from database import supabase
from fastapi import HTTPException

def cancelar_suscripcion(user_id):
    try:
        if user_id is None:
            raise HTTPException(
                status_code=400,
                detail='El ID del usuario es obligatorio para la cancelación de la suscripción.'
            )

        user_response = supabase.table('users').select('rol').eq('id', str(user_id)).single().execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')

        if user_response.data['rol'] != 'ABONADO':
            raise HTTPException(status_code=400, detail='El usuario no tiene una suscripción activa.')

        supabase.table('users').update({'rol': 'NO_ABONADO'}).eq('id', str(user_id)).execute()
        supabase.table('subscriptions').update({'status': 'CANCELADA'}).eq('user_id', str(user_id)).eq('status', 'ACTIVA').execute()

        return {'message': 'Suscripción cancelada exitosamente.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la suscripción: {str(e)}')
