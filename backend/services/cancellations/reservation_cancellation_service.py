from database import supabase
from fastapi import HTTPException
from datetime import datetime, timezone
from utils import benefits
#from services.mercadoPago_service import depositar_reserva  # pendiente de implementar


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

        supabase.table('reservations').update({'status': 'CANCELADA'}).eq('id', reservation_id).execute()

        nueva_capacidad = max(clase['current_capacity'] - 1, 0)
        supabase.table('classes').update({'current_capacity': nueva_capacidad}).eq('id', clase['id']).execute()

        # Calcular el nuevo valor ANTES de persistir y usar ese mismo valor
        # en todas las evaluaciones de beneficios siguientes.
        new_monthly_cancellations = user['monthly_cancellations'] + 1
        supabase.table('users').update({
            'monthly_cancellations': new_monthly_cancellations,
            'cancellation_count': user['cancellation_count'] + 1,
        }).eq('id', user['id']).execute()

        _promover_waitlist(reserva['class_id'], nueva_capacidad)

        mensaje = 'Reserva cancelada exitosamente.'

        if diferencia_horas >= 48:
            # Con 48hs o más de anticipación se aplican beneficios por cancelación.
            # Según entrevista:
            #   1ra cancelación del mes → descuento 20% en próxima cuota
            #   2da cancelación del mes → descuento 30% en próxima cuota
            #   3ra cancelación en adelante → se pierden descuentos acumulados
            # El NO_ABONADO recibe devolución de seña (pendiente integración MercadoPago).
            if user['rol'] == 'ABONADO':
                if new_monthly_cancellations == 1:
                    benefits.otorgar_descuento20(user['id'])
                elif new_monthly_cancellations == 2:
                    benefits.otorgar_descuento30(user['id'])
                else:
                    # 3ra cancelación o más: se pierden todos los descuentos acumulados
                    benefits.cancelar_descuentos(user['id'])
                    mensaje = 'Has alcanzado el límite de cancelaciones. Se han retirado tus descuentos.'
            else:
                # NO_ABONADO: devolver seña (pendiente integración MercadoPago)
                # depositar_reserva(reserva['amount_paid'], user['email'])
                pass

        elif diferencia_horas >= 24:
            # Entre 24hs y 48hs: se pierde el beneficio, no se otorga nada.
            # Según entrevista: "con 24hs antes pierde el beneficio".
            # El NO_ABONADO tampoco recupera la seña en este rango.
            mensaje = 'Reserva cancelada. No se otorgan beneficios por cancelaciones con menos de 48hs de anticipación.'

        else:
            # Menos de 24hs: sin beneficio para ningún tipo de usuario.
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
                    'status': 'CONFIRMADA',
                    'payment_status': 'PENDIENTE',
                }).execute()

                supabase.table('classes').update(
                    {'current_capacity': capacidad_actual + 1}
                ).eq('id', class_id).execute()

                supabase.table('waitlist').delete().eq('id', entrada['id']).execute()
                # TODO: notificar al usuario que fue promovido desde la lista de espera
                return
    except Exception:
        # No interrumpir el flujo principal si la promoción falla
        pass