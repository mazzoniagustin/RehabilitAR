from database import supabase
from fastapi import HTTPException
from services.reservations import waitlist_service


def reservar_clase_fija(user_id: str, class_id: str):
    try:
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

        if clase['current_capacity'] >= clase['max_capacity']:
            return waitlist_service.unirse_a_waitlist(user_id, class_id)

        payment_status = 'PAGADO' if user['rol'] == 'ABONADO' else 'PENDIENTE'

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

        return {'message': 'Inscripción exitosa.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al realizar la reserva: {str(e)}')
