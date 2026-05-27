from database import supabase
from fastapi import HTTPException
#from services.mercadoPago_service import pagar_Reserva #pendiente_de_implementar

def reservar_clase_individual(user_id: str, class_id: str, payment_percentage: int):
    try:
        clase = supabase.table('classes').select('*').eq('id', class_id).execute()
        if not clase.data:
            raise HTTPException(status_code=404, detail='Clase no encontrada.')
        clase = clase.data[0]
        user = supabase.table('users').select('*').eq('id', user_id).execute()
        if not user.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        user = user.data[0]
        if user['account_status'] != 'ACTIVA':
            raise HTTPException(status_code=403, detail='Reserva fallida, no se encuentra habilitado para tomar la clase.')
        if clase['current_capacity'] < clase['max_capacity']:
            total = clase['price']
            amount_paid = total * (payment_percentage / 100)
            #pagar_Reserva = supabase.table('payments').insert({
                #'user_id': user_id,
                #'amount': amount_paid,
                #'status': 'PENDIENTE'
            #}).execute()
            supabase.table('reservations').insert({
                'user_id': user_id,
                'class_id': class_id,
                'status': 'CONFIRMADA'
            }).execute()
            supabase.table('classes').update({'current_capacity': clase['current_capacity'] + 1}).eq('id', class_id).execute()
            if payment_percentage == 50:
                return {'message': 'Inscripción exitosa. Debe pagar el 50% restante antes de la clase.'}
            else:
                return {'message': 'Inscripción exitosa.'}
        else:
            raise HTTPException(status_code=400, detail='Reserva fallida debido a que la clase ya se encuentra llena.')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al realizar la reserva: {str(e)}')