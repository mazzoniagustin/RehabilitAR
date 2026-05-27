from database import supabase
from fastapi import HTTPException
from datetime import datetime, timezone
from utils import benefits
#from services.mercadoPago_service import depositar_reserva #pendiente_de_implementar


def cancelar_reserva(reservation_id: str, current_user_id: str):
    try:
        reserva_response = (
            supabase.table('reservations')
            .select('*')
            .eq('id', reservation_id)
            .single()
            .execute()
        )
        if not reserva_response.data:
            raise HTTPException(status_code=404, detail='Reserva no encontrada.')

        reserva = reserva_response.data

        if reserva['user_id'] != current_user_id:
            raise HTTPException(status_code=403, detail='No tenés permiso para cancelar esta reserva.')

        if reserva['status'] != 'CONFIRMADA':
            raise HTTPException(status_code=400, detail='Solo se pueden cancelar reservas confirmadas.')

        clase = (
            supabase.table('classes')
            .select('id, start_time, current_capacity')
            .eq('id', reserva['class_id'])
            .single()
            .execute()
        ).data
        if not clase:
            raise HTTPException(status_code=404, detail='Clase asociada no encontrada.')

        user = (
            supabase.table('users')
            .select('*')
            .eq('id', reserva['user_id'])
            .single()
            .execute()
        ).data
        if not user:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')

        start_time = datetime.fromisoformat(clase['start_time'])
        ahora = datetime.now(timezone.utc)
        diferencia_horas = (start_time - ahora).total_seconds() / 3600

        # Cancelar reserva y decrementar capacidad sin RPC
        supabase.table('reservations').update({'status': 'CANCELADA'}).eq('id', reservation_id).execute()

        nueva_capacidad = max(clase['current_capacity'] - 1, 0)
        supabase.table('classes').update({'current_capacity': nueva_capacidad}).eq('id', clase['id']).execute()

        # Promover al primero de la waitlist si hay alguien esperando
        _promover_waitlist(reserva['class_id'], nueva_capacidad)

        mensaje = 'Reserva cancelada exitosamente.'

        if diferencia_horas >= 48:
            if user['rol'] == 'ABONADO':
                if user['monthly_cancellations'] < 2:
                    benefits.otorgar_credito(user['id'])
                elif user['monthly_cancellations'] == 2:
                    benefits.cancelar_descuentos(user['id'])
                    benefits.retirar_Todoscredito(user['id'])
                    mensaje = 'Has alcanzado el límite de cancelaciones. Se han retirado tus créditos y descuentos.'
                supabase.table('users').update(
                    {'monthly_cancellations': user['monthly_cancellations'] + 1}
                ).eq('id', user['id']).execute()
            else:
                # NO_ABONADO: devolver seña (pendiente integración MercadoPago)
                #depositar_reserva(reserva['amount_paid'], user['email']) #pendiente_de_implementar
                pass

        elif diferencia_horas >= 24:
            if user['rol'] == 'ABONADO':
                if user['monthly_cancellations'] < 2:
                    if user['monthly_cancellations'] == 0:
                        benefits.otorgar_descuento20(user['id'])
                    else:
                        benefits.otorgar_descuento30(user['id'])
                elif user['monthly_cancellations'] == 2:
                    benefits.cancelar_descuentos(user['id'])
                    benefits.retirar_Todoscredito(user['id'])
                    mensaje = 'Has alcanzado el límite de cancelaciones. Se han retirado tus créditos y descuentos.'
                supabase.table('users').update(
                    {'monthly_cancellations': user['monthly_cancellations'] + 1}
                ).eq('id', user['id']).execute()
            else:
                pass

        else:
            mensaje = 'Reserva cancelada. No se otorgan beneficios por cancelaciones con menos de 24hs de anticipación.'

        return {'message': mensaje}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la reserva: {str(e)}')


def _promover_waitlist(class_id: str, capacidad_actual: int):
    """
    Cuando se libera un lugar, asigna al primero de la waitlist.
    Prioridad: ABONADO antes que NO_ABONADO, FIFO dentro de cada grupo.
    """
    try:
        clase = (
            supabase.table('classes')
            .select('max_capacity')
            .eq('id', class_id)
            .single()
            .execute()
        ).data
        if not clase or capacidad_actual >= clase['max_capacity']:
            return

        for prioridad in ['ABONADO', 'NO_ABONADO']:
            siguiente = (
                supabase.table('waitlist')
                .select('*')
                .eq('class_id', class_id)
                .eq('priority', prioridad)
                .order('priority_order', desc=False)
                .limit(1)
                .execute()
            )
            if siguiente.data:
                entrada = siguiente.data[0]

                supabase.table('reservations').insert({
                    'user_id': entrada['user_id'],
                    'class_id': class_id,
                    'status': 'CONFIRMADA'
                }).execute()

                supabase.table('classes').update(
                    {'current_capacity': capacidad_actual + 1}
                ).eq('id', class_id).execute()

                supabase.table('waitlist').delete().eq('id', entrada['id']).execute()
                # TODO: notificar al usuario que fue asignado a la clase
                return
    except Exception:
        # No interrumpir el flujo principal si la promoción falla
        pass
