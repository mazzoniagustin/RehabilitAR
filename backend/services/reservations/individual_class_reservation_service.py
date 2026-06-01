from database import supabase
from fastapi import HTTPException
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

        payment_status = 'SENADO_50' if payment_percentage == 50 else 'PENDIENTE'

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

        supabase.table('users').update({
            'total_reservations_count': user['total_reservations_count'] + 1
        }).eq('id', user_id).execute()

        if payment_percentage == 50:
            return {'message': 'Inscripción exitosa. Debe pagar el 50% restante antes de la clase.'}
        return {'message': 'Inscripción exitosa.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al realizar la reserva: {str(e)}')
