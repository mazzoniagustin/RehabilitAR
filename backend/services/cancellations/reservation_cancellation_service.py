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

        start_time = datetime.fromisoformat(clase['start_time'])
        ahora = datetime.now(timezone.utc)
        diferencia_horas = (start_time - ahora).total_seconds() / 3600

        supabase.table('reservations').update({'status': 'CANCELADA'}).eq('id', reservation_id).execute()

        nueva_capacidad = max(clase['current_capacity'] - 1, 0)
        supabase.table('classes').update({'current_capacity': nueva_capacidad}).eq('id', clase['id']).execute()

        new_monthly_cancellations = user['monthly_cancellations'] + 1
        supabase.table('users').update({
            'monthly_cancellations': new_monthly_cancellations,
            'cancellation_count': user['cancellation_count'] + 1,
        }).eq('id', user['id']).execute()

        # Promover waitlist respetando el tipo de clase
        _promover_waitlist(reserva['class_id'], clase['type'], nueva_capacidad)

        mensaje = 'Reserva cancelada exitosamente.'

        if diferencia_horas >= 48:
            if user['rol'] == 'ABONADO':
                if new_monthly_cancellations == 1:
                    benefits.otorgar_descuento20(user['id'])
                elif new_monthly_cancellations == 2:
                    benefits.otorgar_descuento30(user['id'])
                else:
                    benefits.cancelar_descuentos(user['id'])
                    mensaje = 'Has alcanzado el límite de cancelaciones. Se han retirado tus descuentos.'
            else:
                # NO_ABONADO: devolver seña (pendiente integración MercadoPago)
                pass

        elif diferencia_horas >= 24:
            mensaje = 'Reserva cancelada. No se otorgan beneficios por cancelaciones con menos de 48hs de anticipación.'

        else:
            mensaje = 'Reserva cancelada. No se otorgan beneficios por cancelaciones con menos de 24hs de anticipación.'

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
        else:
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
            'payment_status': 'PENDIENTE',
            'cancellation_reason': None,
            'cancelled_at': None,
        }).eq('id', existing_cancelled.data[0]['id']).execute()
    else:
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
