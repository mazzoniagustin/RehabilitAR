from database import supabase
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from services.classes_service import cancel_class
from utils import benefits

AUTO_NO_PROFESSOR_REASON = 'Cancelación automática por falta de profesor.'


def _to_aware_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _registrar_cancelacion(
    class_id: str,
    cancel_reason: str,
    tipo: str,
    user_id: str = None,
    reservation_id: str = None,
    generates_credit: bool = False,
    generates_refund: bool = False,
):
    """
    Registra el motivo de cancelación en la tabla 'cancellations',
    que es el lugar correcto en el schema (la tabla classes no tiene
    columna cancellation_reason).
    """
    row = {
        'class_id': str(class_id),
        'reason': cancel_reason,
        'type': tipo,
        'generates_credit': generates_credit,
        'generates_refund': generates_refund,
    }
    if user_id:
        row['user_id'] = str(user_id)
    if reservation_id:
        row['reservation_id'] = str(reservation_id)
    supabase.table('cancellations').insert(row).execute()


def _limpiar_waitlist_de_clase(class_id: str):
    supabase.table('waitlist').delete().eq('class_id', class_id).execute()


def _cancelar_reservas_de_clase(class_id: str, cancel_reason: str, tipo: str):
    """
    Cancela todas las reservas confirmadas de la clase y aplica
    los beneficios correspondientes (crédito a abonados, reembolso
    pendiente de implementar para no abonados).
    Al finalizar, resetea current_capacity a 0 para que la clase
    quede consistente aunque su status sea CANCELADA.
    """
    reservas = (
        supabase.table('reservations')
        .select('*')
        .eq('class_id', class_id)
        .eq('status', 'CONFIRMADA')
        .execute()
    )
    for reserva in (reservas.data or []):
        reservation_update = {
            'status': 'CANCELADA',
            'cancelled_at': datetime.now(timezone.utc).isoformat(),
            'cancellation_reason': cancel_reason,
        }
        user = supabase.table('users').select('rol').eq('id', reserva['user_id']).single().execute().data
        if user and user['rol'] == 'ABONADO':
            credit_result = benefits.otorgar_credito(
                reserva['user_id'],
                reservation_id=reserva['id'],
                class_id=class_id,
                reason=f'Crédito otorgado por cancelación de clase: {cancel_reason}'
            )
            generates_credit = bool(credit_result.get('granted'))
            if generates_credit:
                reservation_update['payment_status'] = 'CREDITO_APLICADO'
            generates_refund = False
        else:
            # depositar_reserva(reserva['amount_paid'], user['email']) #pendiente_de_implementar
            reservation_update['payment_status'] = 'DEVUELTO'
            generates_credit = False
            generates_refund = True

        supabase.table('reservations').update(reservation_update).eq('id', reserva['id']).execute()
        _registrar_cancelacion(
            class_id=class_id,
            cancel_reason=cancel_reason,
            tipo=tipo,
            user_id=reserva['user_id'],
            reservation_id=reserva['id'],
            generates_credit=generates_credit,
            generates_refund=generates_refund,
        )

    # Resetear el cupo ocupado a 0: todas las reservas fueron canceladas,
    # no quedan inscriptos independientemente del status de la clase.
    supabase.table('classes').update({'current_capacity': 0}).eq('id', class_id).execute()
    _limpiar_waitlist_de_clase(class_id)


def _cancelar_clase_confirmada(class_id: str, reason: str, tipo: str, user_id: str = None):
    cancel_class(class_id)
    _registrar_cancelacion(class_id, reason, tipo=tipo, user_id=user_id)
    _cancelar_reservas_de_clase(class_id, reason, tipo=tipo)


def cancelar_clase(class_id: str, cancel_reason: str, user_id: str = None):
    try:
        if not cancel_reason or not cancel_reason.strip():
            raise HTTPException(status_code=400, detail='La razón de cancelación es obligatoria.')

        reason = cancel_reason.strip()
        _cancelar_clase_confirmada(class_id, reason, tipo='MANUAL', user_id=user_id)

        return {'message': 'Clase cancelada exitosamente.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la clase: {str(e)}')


def cancelacion_automatica(class_id: str):
    try:
        if class_id is None:
            raise HTTPException(status_code=400, detail='El ID de la clase es obligatorio para la cancelación automática.')

        if cancelar_si_corresponde_sin_profesor(class_id):
            return {'message': 'Clase cancelada automáticamente por falta de profesor.'}

        return {'message': 'No se cumplen las condiciones para cancelar la clase automáticamente.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la clase: {str(e)}')


def _esta_en_ventana_sin_profesor(clase: dict):
    if not clase:
        return False
    if clase.get('status') and clase['status'] != 'PROGRAMADA':
        return False
    if clase.get('professor_id') is not None:
        return False

    start_time = _to_aware_utc(clase['start_time'])
    ahora = datetime.now(timezone.utc)
    diferencia_horas = (start_time - ahora).total_seconds() / 3600
    return 0 < diferencia_horas <= 12


def cancelar_si_corresponde_sin_profesor(class_id: str, clase: dict = None):
    class_id = str(class_id)
    if clase is None:
        clase = (
            supabase.table('classes')
            .select('id, status, professor_id, start_time')
            .eq('id', class_id)
            .single()
            .execute()
        ).data
        if not clase:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')

    if _esta_en_ventana_sin_profesor(clase):
        _cancelar_clase_confirmada(class_id, AUTO_NO_PROFESSOR_REASON, tipo='AUTOMATICA')
        return True

    return False


def asegurar_clase_reservable_con_profesor(class_id: str, clase: dict = None):
    if cancelar_si_corresponde_sin_profesor(class_id, clase):
        raise HTTPException(
            status_code=400,
            detail='La clase fue cancelada automáticamente por falta de profesor.'
        )


def cancelar_clases_sin_profesor():
    """
    Cancela todas las clases programadas sin profesor que comienzan dentro
    de las próximas 12 horas, reutilizando la lógica del servicio.
    """
    try:
        ahora = datetime.now(timezone.utc)
        limite = ahora + timedelta(hours=12)

        clases = (
            supabase.table('classes')
            .select('id')
            .eq('status', 'PROGRAMADA')
            .is_('professor_id', None)
            .gt('start_time', ahora.isoformat())
            .lte('start_time', limite.isoformat())
            .execute()
        )

        canceladas = []
        errores = []

        for clase in (clases.data or []):
            try:
                _cancelar_clase_confirmada(clase['id'], AUTO_NO_PROFESSOR_REASON, tipo='AUTOMATICA')
                canceladas.append(str(clase['id']))
            except Exception as e:
                errores.append({'class_id': str(clase['id']), 'error': str(e)})

        return {
            'message': 'Proceso de cancelación automática finalizado.',
            'cancelled_count': len(canceladas),
            'cancelled_classes': canceladas,
            'errors': errores,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar clases sin profesor: {str(e)}')
