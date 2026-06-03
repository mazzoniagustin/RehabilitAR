from database import supabase
from fastapi import HTTPException
from services.cancellations.classes_cancellation_service import asegurar_clase_reservable_con_profesor
from services.reservations.overlap_validator import validate_user_has_no_overlapping_class
from services.reservations import waitlist_service


def reservar_clase_fija(user_id: str, class_id: str, payment_percentage: int = 100):
    try:
        # Normalizar a str por si llegan como objetos UUID desde Pydantic
        user_id = str(user_id)
        class_id = str(class_id)

        clase_response = (
            supabase.table('classes')
            .select('*')
            .eq('id', class_id)
            .single()
            .execute()
        )
        if not clase_response.data:
            raise HTTPException(status_code=404, detail='Clase no encontrada.')
        clase = clase_response.data

        if clase['type'] != 'FIJA':
            raise HTTPException(status_code=400, detail='Esta clase no es fija.')

        asegurar_clase_reservable_con_profesor(class_id, clase)

        user_response = (
            supabase.table('users')
            .select('*')
            .eq('id', user_id)
            .single()
            .execute()
        )
        if not user_response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        user = user_response.data

        if user['account_status'] != 'ACTIVA':
            raise HTTPException(
                status_code=403,
                detail='Reserva fallida, no se encuentra habilitado para tomar la clase.'
            )
        if user['rol'] != 'ABONADO' and payment_percentage not in (50, 100):
            raise HTTPException(status_code=400, detail='El porcentaje de pago debe ser 50 o 100.')
        existing_active = (
            supabase.table('reservations')
            .select('id, status')
            .eq('user_id', user_id)
            .eq('class_id', class_id)
            .neq('status', 'CANCELADA')
            .execute()
        )
        if existing_active.data:
            raise HTTPException(status_code=400, detail='Ya tenés una reserva para esta clase.')

        validate_user_has_no_overlapping_class(user_id, class_id, clase)

        if clase['current_capacity'] >= clase['max_capacity']:
            return waitlist_service.unirse_a_waitlist(user_id, class_id)

        payment_status = 'PAGADO' if user['rol'] == 'ABONADO' else ('SENADO_50' if payment_percentage == 50 else 'PAGADO')

        existing_cancelled = (
            supabase.table('reservations')
            .select('id')
            .eq('user_id', user_id)
            .eq('class_id', class_id)
            .eq('status', 'CANCELADA')
            .limit(1)
            .execute()
        )

        if existing_cancelled.data:
            supabase.table('reservations').update({
                'status': 'CONFIRMADA',
                'payment_status': payment_status,
                'cancellation_reason': None,
                'cancelled_at': None,
            }).eq('id', existing_cancelled.data[0]['id']).execute()
        else:
            try:
                supabase.table('reservations').insert({
                    'user_id': user_id,
                    'class_id': class_id,
                    'status': 'CONFIRMADA',
                    'payment_status': payment_status,
                }).execute()
            except Exception as insert_err:
                if '23505' in str(insert_err) or 'unique_user_class' in str(insert_err):
                    raise HTTPException(status_code=400, detail='Ya tenés una reserva para esta clase.')
                raise

        supabase.table('classes').update({
            'current_capacity': clase['current_capacity'] + 1
        }).eq('id', class_id).execute()

        reservation_response = (
            supabase.table('reservations')
            .select('id')
            .eq('user_id', user_id)
            .eq('class_id', class_id)
            .eq('status', 'CONFIRMADA')
            .single()
            .execute()
        )

        reservation_id = reservation_response.data['id']

        return {
            'message': 'Reserva generada. Escaneá el QR para completar el pago.',
            'reservation_id': reservation_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al realizar la reserva: {str(e)}')


def _agregar_a_waitlist(user_id: str, class_id: str, prioridad: str):
    """
    Agrega al usuario a la lista de espera respetando prioridad FIFO:
    - ABONADO tiene prioridad sobre NO_ABONADO.
    - Dentro del mismo nivel de prioridad, se respeta el orden de llegada.
    """
    ya_en_lista = (
        supabase.table('waitlist')
        .select('id')
        .eq('user_id', user_id)
        .eq('class_id', class_id)
        .execute()
    )
    if ya_en_lista.data:
        raise HTTPException(status_code=400, detail='Ya estás en la lista de espera para esta clase.')

    waitlist_response = (
        supabase.table('waitlist')
        .select('position')
        .eq('class_id', class_id)
        .order('position', desc=True)
        .limit(1)
        .execute()
    )
    entradas = waitlist_response.data or []
    nueva_posicion = (entradas[0]['position'] + 1) if entradas else 1

    nivel_response = (
        supabase.table('waitlist')
        .select('priority_order')
        .eq('class_id', class_id)
        .eq('priority', prioridad)
        .order('priority_order', desc=True)
        .limit(1)
        .execute()
    )
    nivel_entradas = nivel_response.data or []
    nuevo_priority_order = (nivel_entradas[0]['priority_order'] + 1) if nivel_entradas else 1

    supabase.table('waitlist').insert({
        'user_id': user_id,
        'class_id': class_id,
        'position': nueva_posicion,
        'priority': prioridad,
        'priority_order': nuevo_priority_order,
    }).execute()

    return {'message': 'La clase se encuentra llena. Fuiste agregado a la lista de espera.'}
