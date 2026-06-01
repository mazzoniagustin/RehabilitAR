from database import supabase
from fastapi import HTTPException

def cancelar_suscripcion(user_id: str):
    try:
        supabase.table('users').update({'rol': 'NO_ABONADO'}).eq('id', user_id).execute()
        supabase.table('subscriptions').update({'status': 'CANCELADA'}).eq('user_id', user_id).eq('status', 'ACTIVA').execute()

        return {'message': 'Suscripción cancelada exitosamente.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la suscripción: {str(e)}')
