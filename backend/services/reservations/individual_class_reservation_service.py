from database import supabase
from fastapi import HTTPException
#from services.mercadoPago_service import pagar_Reserva  # pendiente de implementar

def reservar_clase_individual(user_id: str, class_id: str, payment_percentage: int):
    try:
        # Normalizar a str por si llegan como objetos UUID desde Pydantic
        user_id = str(user_id)
        class_id = str(class_id)

        if payment_percentage not in (50, 100):
            raise HTTPException(status_code=400, detail='El porcentaje de pago debe ser 50 o 100.')

        clase = supabase.table('classes').select('*').eq('id', class_id).single().execute()
        if not clase.data:
            raise HTTPException(status_code=404, detail='Clase no encontrada.')
        clase = clase.data

        if clase['is_scheduled']:
            raise HTTPException(status_code=400, detail='Esta clase es fija y no puede reservarse de esta manera.')

        user = supabase.table('users').select('*').eq('id', user_id).single().execute()
        if not user.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        user = user.data

        if user['account_status'] != 'ACTIVA':
            raise HTTPException(status_code=403, detail='Reserva fallida, no se encuentra habilitado para tomar la clase.')

        existing = (
            supabase.table('reservations')
            .select('id')
            .eq('user_id', user_id)
            .eq('class_id', class_id)
            .eq('status', 'CONFIRMADA')
            .execute()
        )
        if existing.data:
            raise HTTPException(status_code=400, detail='Ya tenés una reserva confirmada para esta clase.')

        if clase['current_capacity'] >= clase['max_capacity']:
            raise HTTPException(status_code=400, detail='Reserva fallida debido a que la clase ya se encuentra llena.')

        update_response = (
            supabase.table('classes')
            .update({'current_capacity': clase['current_capacity'] + 1})
            .eq('id', class_id)
            .eq('current_capacity', clase['current_capacity'])
            .lt('current_capacity', clase['max_capacity'])
            .select()  # necesario para que Supabase devuelva las filas afectadas
            .execute()
        )
        if not update_response.data:
            # El UPDATE no afectó ninguna fila: la clase se llenó entre el SELECT y el UPDATE.
            raise HTTPException(status_code=400, detail='Reserva fallida debido a que la clase ya se encuentra llena.')

        # FIX: asignar payment_status según porcentaje abonado
        # Con integración MercadoPago: 100% → 'PAGADO', 50% → 'SENADO_50'
        # Sin integración activa, ambos quedan en pendiente pero diferenciados
        payment_status = 'SENADO_50' if payment_percentage == 50 else 'PENDIENTE'

        supabase.table('reservations').insert({
            'user_id': user_id,
            'class_id': class_id,
            'status': 'CONFIRMADA',
            'payment_status': payment_status,
        }).execute()

        # FIX: actualizar contador histórico de reservas
        supabase.table('users').update({
            'total_reservations_count': user['total_reservations_count'] + 1
        }).eq('id', user_id).execute()

        if payment_percentage == 50:
            return {'message': 'Inscripción exitosa. Debe pagar el 50% restante antes de la clase.'}
        else:
            return {'message': 'Inscripción exitosa.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al realizar la reserva: {str(e)}')
