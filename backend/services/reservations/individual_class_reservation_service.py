from database import supabase
from fastapi import HTTPException

#from services.mp_service import pagar_Reserva #pendiente_de_implementar
from services.cancellations.classes_cancellation_service import asegurar_clase_reservable_con_profesor
from services.reservations.overlap_validator import validate_user_has_no_overlapping_class
from services.reservations import waitlist_service


def reservar_clase_individual(user_id: str, class_id: str, payment_percentage: int):
    try:
        user_id = str(user_id)
        class_id = str(class_id)

        if payment_percentage not in (50, 100):
            raise HTTPException(status_code=400, detail='El porcentaje de pago debe ser 50 o 100.')

        clase = (
            supabase.table('classes')
            .select('*')
            .eq('id', class_id)
            .single()
            .execute()
        )
        if not clase.data:
            raise HTTPException(status_code=404, detail='Clase no encontrada.')
        clase = clase.data

        if clase['type'] != 'INDIVIDUAL':
            raise HTTPException(
                status_code=400,
                detail='Esta clase no es individual. Para clases fijas utilizá la opción correspondiente.'
            )

        asegurar_clase_reservable_con_profesor(class_id, clase)

        user = (
            supabase.table('users')
            .select('*')
            .eq('id', user_id)
            .single()
            .execute()
        )
        if not user.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        user = user.data

        if user['account_status'] != 'ACTIVA':
            raise HTTPException(
                status_code=403,
                detail='Reserva fallida, no se encuentra habilitado para tomar la clase.'
            )

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

        payment_status = 'SENADO_50' if payment_percentage == 50 else 'PAGADO'

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

        supabase.table('payments').insert({
            'user_id': user_id,
            'reservation_id': reservation_id,
            'amount': float(clase['price']) * 0.5,
            'status': 'PENDIENTE',
            'payment_reason': 'DEBT',
            'payment_type': 'RESERVATION_REMAINING'
        }).execute()
            
        supabase.table('users').update({
            'total_reservations_count': user['total_reservations_count'] + 1
        }).eq('id', user_id).execute()
            
        return {
            'message': 'Reserva generada. Escaneá el QR para completar el pago.',
            'reservation_id': reservation_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al realizar la reserva: {str(e)}')


def _agregar_a_waitlist_individual(user_id: str, class_id: str):
    """
    Waitlist FIFO puro para clases INDIVIDUAL: sin prioridades por rol.
    El campo priority se almacena como NO_ABONADO por defecto para cumplir el NOT NULL,
    pero no se usa como criterio de orden — se ordena por joined_at.
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
        .select('position, priority_order')
        .eq('class_id', class_id)
        .order('position', desc=True)
        .limit(1)
        .execute()
    )
    entradas = waitlist_response.data or []
    nueva_posicion = (entradas[0]['position'] + 1) if entradas else 1
    nuevo_priority_order = (entradas[0]['priority_order'] + 1) if entradas else 1

    supabase.table('waitlist').insert({
        'user_id': user_id,
        'class_id': class_id,
        'position': nueva_posicion,
        'priority': 'NO_ABONADO',   # valor requerido por NOT NULL; no se usa para ordenar
        'priority_order': nuevo_priority_order,
    }).execute()

    return {'message': 'La clase se encuentra llena. Fuiste agregado a la lista de espera.'}
