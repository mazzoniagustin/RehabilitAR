from database import supabase
from fastapi import HTTPException

def reservar_clase_fija(user_id: str, class_id: str):
    try:
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