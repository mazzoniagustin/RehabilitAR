from database import supabase
from fastapi import HTTPException

def reservar_clase_fija(user_id: str, class_id: str):
    try:
<<<<<<< HEAD
        clase_response = supabase.table('classes').select('*').eq('id', class_id).execute()
        if not clase_response.data:
            raise HTTPException(status_code=404, detail='Clase no encontrada.')
        clase = clase_response.data[0]
        user_response = supabase.table('users').select('*').eq('id', user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        user = user_response.data[0]
        if user['account_status'] != 'ACTIVA':
            raise HTTPException(status_code=403, detail='Reserva fallida, no se encuentra habilitado para tomar la clase.')
        if clase['current_capacity'] < clase['max_capacity']:
            supabase.table('reservations').insert({
                'user_id': user_id,
                'class_id': class_id,
                'status': 'CONFIRMADA'
            }).execute()
            supabase.table('classes').update({'current_capacity': clase['current_capacity'] + 1}).eq('id', class_id).execute()
            return {'message': 'Inscripción exitosa.'}
        else:
            reservas = supabase.table('reservations').select('*').eq('class_id', class_id).eq('status', 'CONFIRMADA').order('created_at', desc=True).execute()    
            no_abonado_reserva = None
            for reserva in reservas.data:
                reserva_user = supabase.table('users').select('rol').eq('id', reserva['user_id']).execute().data[0]
                if reserva_user['rol'] == 'NO_ABONADO':
                    no_abonado_reserva = reserva
                    break
            if no_abonado_reserva:
                supabase.table('reservations').update({'status': 'CANCELADA'}).eq('id', no_abonado_reserva['id']).execute()
                supabase.table('reservations').insert({
                    'user_id': user_id,
                    'class_id': class_id,
                    'status': 'CONFIRMADA'
                }).execute()
                return {'message': 'Inscripción exitosa.'}
            else:
                raise HTTPException(status_code=400, detail='Reserva fallida debido a que la clase ya se encuentra llena.')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al realizar la reserva: {str(e)}')
=======
        # Normalizar a str por si llegan como objetos UUID desde Pydantic
        user_id = str(user_id)
        class_id = str(class_id)

        clase_response = supabase.table('classes').select('*').eq('id', class_id).single().execute()
        if not clase_response.data:
            raise HTTPException(status_code=404, detail='Clase no encontrada.')
        clase = clase_response.data

        if not clase['is_scheduled']:
            raise HTTPException(status_code=400, detail='Esta clase no es fija.')

        user_response = supabase.table('users').select('*').eq('id', user_id).single().execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        user = user_response.data

        if user['account_status'] != 'ACTIVA':
            raise HTTPException(status_code=403, detail='Reserva fallida, no se encuentra habilitado para tomar la clase.')

        # Verificar si ya hay una reserva activa (no cancelada) para esta clase
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

        prioridad = 'ABONADO' if user['rol'] == 'ABONADO' else 'NO_ABONADO'

        if clase['current_capacity'] < clase['max_capacity']:
            # Reutilizar reserva CANCELADA previa si existe (evita conflicto unique constraint).
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
                    'payment_status': 'PENDIENTE',
                    'cancellation_reason': None,
                    'cancelled_at': None,
                }).eq('id', existing_cancelled.data[0]['id']).execute()
            else:
                try:
                    supabase.table('reservations').insert({
                        'user_id': user_id,
                        'class_id': class_id,
                        'status': 'CONFIRMADA'
                    }).execute()
                except Exception as insert_err:
                    if '23505' in str(insert_err) or 'unique_user_class' in str(insert_err):
                        raise HTTPException(status_code=400, detail='Ya tenés una reserva para esta clase.')
                    raise

            supabase.table('classes').update({
                'current_capacity': clase['current_capacity'] + 1
            }).eq('id', class_id).execute()

            return {'message': 'Inscripción exitosa.'}

        # Clase llena: agregar a la lista de espera con prioridad FIFO por tipo
        return _agregar_a_waitlist(user_id, class_id, prioridad)

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
        .select('position, priority, priority_order')
        .eq('class_id', class_id)
        .order('position', desc=True)
        .execute()
    )
    entradas = waitlist_response.data or []

    nueva_posicion = (entradas[0]['position'] + 1) if entradas else 1

    mismo_nivel = [e for e in entradas if e['priority'] == prioridad]
    nuevo_priority_order = (
        max(e['priority_order'] for e in mismo_nivel) + 1
    ) if mismo_nivel else 1

    supabase.table('waitlist').insert({
        'user_id': user_id,
        'class_id': class_id,
        'position': nueva_posicion,
        'priority': prioridad,
        'priority_order': nuevo_priority_order,
    }).execute()

    return {'message': 'La clase se encuentra llena. Fuiste agregado a la lista de espera.'}
>>>>>>> origin/feature/classes
