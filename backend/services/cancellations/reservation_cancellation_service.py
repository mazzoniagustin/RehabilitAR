from database import supabase
from fastapi import HTTPException
from datetime import datetime, timezone
from utils import benefits
#from services.mercadoPago_service import depositar_reserva  # pendiente de implementar


def _to_aware_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _registrar_cancelacion_reserva(
    reservation_id: str,
    class_id: str,
    user_id: str,
    reason: str,
    hours_before: float,
    generates_credit: bool = False,
    generates_refund: bool = False,
):
    supabase.table('cancellations').insert({
        'reservation_id': str(reservation_id),
        'class_id': str(class_id),
        'user_id': str(user_id),
        'reason': reason,
        'type': 'CLIENTE',
        'hours_before': round(hours_before, 2),
        'generates_credit': generates_credit,
        'generates_refund': generates_refund,
    }).execute()


def _aplicar_descuento_por_cancelacion(user_id: str, monthly_cancellations: int):
    if monthly_cancellations == 1:
        benefits.otorgar_descuento20(user_id)
        return 'Reserva cancelada. Se aplicó un descuento del 20% para la próxima cuota.'

    if monthly_cancellations == 2:
        benefits.otorgar_descuento30(user_id)
        return 'Reserva cancelada. Se aplicó un descuento total del 30% para la próxima cuota.'

    return _retirar_beneficios_por_limite(user_id)


def _retirar_beneficios_por_limite(user_id: str):
    benefits.cancelar_descuentos(user_id)
    benefits.retirar_Todoscredito(
        user_id,
        reason='Beneficios retirados por alcanzar el límite de cancelaciones voluntarias.'
    )
    return 'Reserva cancelada. Alcanzaste el límite de cancelaciones y se retiraron tus beneficios.'


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
            .select('id, type, start_time, current_capacity')
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

        start_time = _to_aware_utc(clase['start_time'])
        ahora = datetime.now(timezone.utc)
        diferencia_horas = (start_time - ahora).total_seconds() / 3600

        reservation_update = {
            'status': 'CANCELADA',
            'cancelled_at': ahora.isoformat(),
            'cancellation_reason': 'Cancelación solicitada por el cliente.',
        }

        nueva_capacidad = max(clase['current_capacity'] - 1, 0)

        new_monthly_cancellations = user['monthly_cancellations'] + 1
        supabase.table('users').update({
            'monthly_cancellations': new_monthly_cancellations,
            'cancellation_count': user['cancellation_count'] + 1,
        }).eq('id', user['id']).execute()

        mensaje = 'Reserva cancelada exitosamente.'
        generates_credit = False
        generates_refund = False

        if user['rol'] == 'NO_ABONADO':
            if diferencia_horas >= 24:
                reservation_update['payment_status'] = 'DEVUELTO'
                generates_refund = True
                mensaje = 'Reserva cancelada. Se reintegró el monto señado.'
            else:
                mensaje = 'Reserva cancelada. No se otorgan beneficios por cancelaciones con menos de 24hs de anticipación.'

        elif user['rol'] == 'ABONADO':
            if new_monthly_cancellations >= 3:
                mensaje = _retirar_beneficios_por_limite(user['id'])
            elif diferencia_horas >= 48:
                credit_result = benefits.otorgar_credito(
                    user['id'],
                    reservation_id=reservation_id,
                    class_id=clase['id'],
                    reason='Crédito otorgado por cancelación de reserva con más de 48 horas de anticipación.'
                )
                generates_credit = bool(credit_result.get('granted'))
                if generates_credit:
                    reservation_update['payment_status'] = 'CREDITO_APLICADO'
                mensaje = credit_result['message']
            elif diferencia_horas >= 24:
                mensaje = _aplicar_descuento_por_cancelacion(user['id'], new_monthly_cancellations)
            else:
                mensaje = 'Reserva cancelada. No se otorgan beneficios por cancelaciones con menos de 24hs de anticipación.'

        supabase.table('reservations').update(reservation_update).eq('id', reservation_id).execute()
        supabase.table('classes').update({'current_capacity': nueva_capacidad}).eq('id', clase['id']).execute()

        _registrar_cancelacion_reserva(
            reservation_id=reservation_id,
            class_id=clase['id'],
            user_id=user['id'],
            reason=reservation_update['cancellation_reason'],
            hours_before=diferencia_horas,
            generates_credit=generates_credit,
            generates_refund=generates_refund,
        )

        # Promover waitlist respetando el tipo de clase
        _promover_waitlist(reserva['class_id'], clase['type'], nueva_capacidad)

        return {'message': mensaje}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la reserva: {str(e)}')


def _promover_waitlist(class_id: str, class_type: str, capacidad_actual: int):
    """
    Cuando se libera un lugar, asigna al primero de la waitlist según el tipo de clase:
    - FIJA:       FIFO con prioridad (ABONADO antes que NO_ABONADO).
    - INDIVIDUAL: FIFO puro (sin distinción de prioridad, orden de llegada).
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

        if class_type == 'FIJA':
            # Prioridad: ABONADO primero, luego NO_ABONADO, FIFO dentro de cada grupo
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
                    _confirmar_desde_waitlist(siguiente.data[0], class_id, capacidad_actual)
                    return
        elif class_type == 'INDIVIDUAL':
            # INDIVIDUAL: FIFO puro por orden de llegada, sin distinción de prioridad
            siguiente = (
                supabase.table('waitlist')
                .select('*')
                .eq('class_id', class_id)
                .order('joined_at', desc=False)
                .limit(1)
                .execute()
            )
            if siguiente.data:
                _confirmar_desde_waitlist(siguiente.data[0], class_id, capacidad_actual)

    except Exception:
        # No interrumpir el flujo principal si la promoción falla
        pass


def _confirmar_desde_waitlist(entrada: dict, class_id: str, capacidad_actual: int):
    """Crea/reactiva la reserva del primer usuario en waitlist y lo elimina de la lista."""
    user_response = (
        supabase.table('users')
        .select('rol')
        .eq('id', entrada['user_id'])
        .single()
        .execute()
    )
    class_response = (
        supabase.table('classes')
        .select('type')
        .eq('id', class_id)
        .single()
        .execute()
    )
    payment_status = (
        'PAGADO'
        if (user_response.data or {}).get('rol') == 'ABONADO'
        and (class_response.data or {}).get('type') == 'FIJA'
        else 'PENDIENTE'
    )

    # Reutilizar reserva cancelada si existe (evita violación del unique constraint)
    existing_cancelled = (
        supabase.table('reservations')
        .select('id')
        .eq('user_id', entrada['user_id'])
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
        supabase.table('reservations').insert({
            'user_id': entrada['user_id'],
            'class_id': class_id,
            'status': 'CONFIRMADA',
            'payment_status': payment_status,
        }).execute()

    supabase.table('classes').update(
        {'current_capacity': capacidad_actual + 1}
    ).eq('id', class_id).execute()

    supabase.table('waitlist').delete().eq('id', entrada['id']).execute()

    # Reordenar posiciones globales de los restantes en la waitlist
    restantes = (
        supabase.table('waitlist')
        .select('id, priority')
        .eq('class_id', class_id)
        .order('position', desc=False)
        .execute()
    ).data or []
    for i, fila in enumerate(restantes, start=1):
        supabase.table('waitlist').update({'position': i}).eq('id', fila['id']).execute()

    # Reordenar priority_order dentro de cada grupo de prioridad
    for prioridad in ['ABONADO', 'NO_ABONADO']:
        grupo = (
            supabase.table('waitlist')
            .select('id')
            .eq('class_id', class_id)
            .eq('priority', prioridad)
            .order('position', desc=False)
            .execute()
        ).data or []
        for i, fila in enumerate(grupo, start=1):
            supabase.table('waitlist').update({'priority_order': i}).eq('id', fila['id']).execute()

    # TODO: notificar al usuario que fue promovido desde la lista de espera
