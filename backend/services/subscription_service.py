from database import supabase
from fastapi import HTTPException
#from payment_service import pagar_suscripcion

def dar_alta_suscripcion(user_id: str):
    try:
        user = supabase.table('users').select('rol').eq('id', str(user_id)).single().execute()
        if not user.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if user.data['rol'] == 'ABONADO':
            raise HTTPException(status_code=400, detail='El usuario ya es abonado.')
        #pagar_suscripcion(user_id)
        supabase.table('users').update({'rol': 'ABONADO'}).eq('id', str(user_id)).execute()
        supabase.table('subscriptions').insert({
            'user_id': str(user_id),
            'status': 'ACTIVA',
        }).execute()
        return {'message': 'Alta de suscripción exitosa.'}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al dar de alta la suscripción: {str(e)}')