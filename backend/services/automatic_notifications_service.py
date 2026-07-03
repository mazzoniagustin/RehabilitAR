from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from database import supabase, supabase_admin
from services.classes_service import list_professors
from utils.class_desc import build_class_desc
from utils.notifications import (
    send_attendance_reminder_email,
    send_no_professor_class_email,
    send_pending_debt_reminder_email,
    send_subscription_due_soon_email,
    send_subscription_payment_deadline_expired_email,
)

ATTENDANCE_REMINDER_EVENT_TYPE = 'ATTENDANCE_REMINDER'
NO_PROFESSOR_EVENT_TYPE = 'NO_PROFESSOR_CLASS_REMINDER'
DEBT_REMINDER_EVENT_TYPE = 'DEBT_REMINDER'
SUBSCRIPTION_DUE_SOON_EVENT_TYPE = 'SUBSCRIPTION_DUE_SOON'
SUBSCRIPTION_PAYMENT_EXPIRED_EVENT_TYPE = 'SUBSCRIPTION_PAYMENT_DEADLINE_EXPIRED'

REMINDER_HOURS_BEFORE = 24
NO_PROFESSOR_CANCELLATION_HOURS_BEFORE = 12
TZ_AR = ZoneInfo('America/Argentina/Buenos_Aires')


def _client():
    return supabase_admin or supabase


def _claim_delivery(
    event_key: str,
    event_type: str,
    user_id: str,
    class_id: str,
    reservation_id: str | None = None,
) -> bool:
    """
    Registra el evento antes de enviar para que los jobs sean idempotentes.
    Si la clave ya existe, ese aviso ya fue procesado.
    """
    existing = (
        _client().table('notification_delivery_log')
        .select('id')
        .eq('event_key', event_key)
        .limit(1)
        .execute()
    )
    if existing.data:
        return False

    row = {
        'event_key': event_key,
        'event_type': event_type,
        'user_id': user_id,
        'class_id': class_id,
    }
    if reservation_id:
        row['reservation_id'] = reservation_id

    _client().table('notification_delivery_log').insert(row).execute()
    return True


def _create_system_notification(user_id: str, title: str, message: str):
    user = (
        _client().table('users')
        .select('notifications_enabled')
        .eq('id', user_id)
        .single()
        .execute()
    )
    if not user.data or not user.data.get('notifications_enabled', True):
        return

    _client().table('notifications').insert({
        'user_id': user_id,
        'title': title,
        'message': message,
    }).execute()


def _user_by_id(user_id: str) -> dict:
    return (
        _client().table('users')
        .select('id, name, email, notifications_enabled')
        .eq('id', user_id)
        .single()
        .execute()
    ).data or {}


def _professor_details_by_id(professor_ids: list[str]) -> dict[str, dict]:
    if not professor_ids:
        return {}

    response = (
        _client().table('users')
        .select('id, name, surname, email')
        .in_('id', professor_ids)
        .execute()
    )
    return {str(professor['id']): professor for professor in (response.data or [])}


def _month_key(today) -> str:
    return today.strftime('%Y-%m')


def _subscription_payment_exists_this_month(user_id: str, today) -> bool:
    month_start = today.replace(day=1).isoformat()
    payment = (
        _client().table('payments')
        .select('id')
        .eq('user_id', user_id)
        .eq('payment_reason', 'SUBSCRIPTION')
        .eq('status', 'PAGADO')
        .gte('paid_at', month_start)
        .lte('paid_at', today.isoformat())
        .limit(1)
        .execute()
    )
    return bool(payment.data)


def _active_subscribers():
    return (
        _client().table('users')
        .select('id, name, email')
        .eq('rol', 'ABONADO')
        .eq('account_status', 'ACTIVA')
        .execute()
    ).data or []


def enviar_recordatorios_asistencia():
    """
    Envia recordatorios a clientes con reservas confirmadas en clases que
    comienzan dentro de las proximas 24 horas.
    """
    try:
        now = datetime.now(timezone.utc)
        limit = now + timedelta(hours=REMINDER_HOURS_BEFORE)

        classes = (
            _client().table('classes')
            .select('id, activity_type, start_time, status, rooms(name)')
            .eq('status', 'PROGRAMADA')
            .gt('start_time', now.isoformat())
            .lte('start_time', limit.isoformat())
            .order('start_time', desc=False)
            .execute()
        ).data or []

        sent_count = 0
        skipped_count = 0
        errors = []

        for clase in classes:
            class_id = str(clase['id'])
            class_desc = build_class_desc(clase)

            reservations = (
                _client().table('reservations')
                .select('id, user_id, users(email, name)')
                .eq('class_id', class_id)
                .eq('status', 'CONFIRMADA')
                .execute()
            ).data or []

            for reservation in reservations:
                reservation_id = str(reservation['id'])
                user_id = str(reservation['user_id'])
                event_key = f'{ATTENDANCE_REMINDER_EVENT_TYPE}:{reservation_id}'

                try:
                    if not _claim_delivery(
                        event_key,
                        ATTENDANCE_REMINDER_EVENT_TYPE,
                        user_id,
                        class_id,
                        reservation_id,
                    ):
                        skipped_count += 1
                        continue

                    try:
                        _create_system_notification(
                            user_id,
                            'Recordatorio de asistencia',
                            f'Te recordamos que tenés una clase reservada de {class_desc}.'
                        )
                    except Exception:
                        # El mail sigue saliendo aunque la notificación in-app falle
                        # o el usuario la tenga desactivada.
                        pass

                    user = reservation.get('users') or {}
                    if user.get('email'):
                        send_attendance_reminder_email(
                            user['email'],
                            user.get('name', 'usuario/a'),
                            class_desc
                        )

                    sent_count += 1
                except Exception as e:
                    errors.append({
                        'reservation_id': reservation_id,
                        'error': str(e),
                    })

        return {
            'message': 'Proceso de recordatorios de asistencia finalizado.',
            'sent_count': sent_count,
            'skipped_count': skipped_count,
            'errors': errors,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al enviar recordatorios de asistencia: {str(e)}')


def avisar_profesores_clases_sin_profesor():
    """
    Notifica a profesores disponibles cuando una clase sin profesor asignado
    comienza dentro de las próximas 24 horas, pero aún no entró en la ventana
    de cancelación automática de 12 horas.
    """
    try:
        now = datetime.now(timezone.utc)
        cancellation_limit = now + timedelta(hours=NO_PROFESSOR_CANCELLATION_HOURS_BEFORE)
        notification_limit = now + timedelta(hours=REMINDER_HOURS_BEFORE)

        classes = (
            _client().table('classes')
            .select('id, activity_type, start_time, end_time, status, rooms(name)')
            .eq('status', 'PROGRAMADA')
            .is_('professor_id', None)
            .gt('start_time', cancellation_limit.isoformat())
            .lte('start_time', notification_limit.isoformat())
            .order('start_time', desc=False)
            .execute()
        ).data or []

        sent_count = 0
        skipped_count = 0
        classes_without_available_professors = []
        errors = []

        for clase in classes:
            class_id = str(clase['id'])
            class_desc = build_class_desc(clase)

            try:
                available_professors = list_professors(
                    clase['start_time'],
                    clase['end_time'],
                    exclude_class_id=class_id
                )
                professor_ids = [str(professor['id']) for professor in available_professors]
                professor_details = _professor_details_by_id(professor_ids)

                if not professor_ids:
                    classes_without_available_professors.append(class_id)
                    continue

                for professor_id in professor_ids:
                    event_key = f'{NO_PROFESSOR_EVENT_TYPE}:{class_id}:{professor_id}'
                    professor = professor_details.get(professor_id, {})

                    try:
                        if not _claim_delivery(
                            event_key,
                            NO_PROFESSOR_EVENT_TYPE,
                            professor_id,
                            class_id,
                        ):
                            skipped_count += 1
                            continue

                        try:
                            _create_system_notification(
                                professor_id,
                                'Clase sin profesor asignado',
                                f'Hay una clase de {class_desc} sin profesor asignado. '
                                'Si estás disponible, podés solicitar tomarla.'
                            )
                        except Exception:
                            # El mail sigue saliendo aunque la notificación in-app falle
                            # o el profesor la tenga desactivada.
                            pass

                        if professor.get('email'):
                            send_no_professor_class_email(
                                professor['email'],
                                professor.get('name', 'profesor/a'),
                                class_desc
                            )

                        sent_count += 1
                    except Exception as e:
                        errors.append({
                            'class_id': class_id,
                            'professor_id': professor_id,
                            'error': str(e),
                        })

            except Exception as e:
                errors.append({
                    'class_id': class_id,
                    'error': str(e),
                })

        return {
            'message': 'Proceso de avisos por clases sin profesor finalizado.',
            'sent_count': sent_count,
            'skipped_count': skipped_count,
            'classes_without_available_professors': classes_without_available_professors,
            'errors': errors,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al avisar clases sin profesor: {str(e)}')


def enviar_recordatorios_deuda_pendiente():
    """
    Envia recordatorios a clientes no abonados con deudas pendientes por
    reservas pagadas al 50% cuando faltan 24 horas o menos para la clase.
    """
    try:
        now = datetime.now(timezone.utc)
        limit = now + timedelta(hours=REMINDER_HOURS_BEFORE)

        classes = (
            _client().table('classes')
            .select('id, activity_type, start_time, status, rooms(name)')
            .eq('status', 'PROGRAMADA')
            .gt('start_time', now.isoformat())
            .lte('start_time', limit.isoformat())
            .order('start_time', desc=False)
            .execute()
        ).data or []

        sent_count = 0
        skipped_count = 0
        errors = []

        for clase in classes:
            class_id = str(clase['id'])
            class_desc = build_class_desc(clase)

            debts = (
                _client().table('payments')
                .select('id, user_id, reservation_id, class_id, amount')
                .eq('class_id', class_id)
                .eq('status', 'PENDIENTE')
                .eq('payment_reason', 'DEBT')
                .execute()
            ).data or []

            for debt in debts:
                payment_id = str(debt['id'])
                user_id = str(debt['user_id'])
                reservation_id = str(debt['reservation_id']) if debt.get('reservation_id') else None
                event_key = f'{DEBT_REMINDER_EVENT_TYPE}:{payment_id}'

                try:
                    if not _claim_delivery(
                        event_key,
                        DEBT_REMINDER_EVENT_TYPE,
                        user_id,
                        class_id,
                        reservation_id,
                    ):
                        skipped_count += 1
                        continue

                    amount = debt.get('amount')
                    message = (
                        f'Tenés una deuda pendiente de ${amount} correspondiente a la clase de {class_desc}. '
                        'El saldo restante debe abonarse antes del inicio de la clase.'
                    )

                    try:
                        _create_system_notification(
                            user_id,
                            'Recordatorio de deuda pendiente',
                            message
                        )
                    except Exception:
                        # El mail sigue saliendo aunque la notificación in-app falle
                        # o el usuario la tenga desactivada.
                        pass

                    user = _user_by_id(user_id)
                    if user.get('email'):
                        send_pending_debt_reminder_email(
                            user['email'],
                            user.get('name', 'usuario/a'),
                            class_desc,
                            amount
                        )

                    sent_count += 1
                except Exception as e:
                    errors.append({
                        'payment_id': payment_id,
                        'reservation_id': reservation_id,
                        'error': str(e),
                    })

        return {
            'message': 'Proceso de recordatorios de deuda pendiente finalizado.',
            'sent_count': sent_count,
            'skipped_count': skipped_count,
            'errors': errors,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al enviar recordatorios de deuda pendiente: {str(e)}')


def notificar_cercania_vencimiento_suscripcion():
    """
    Notifica a clientes abonados el dia 9 del mes si todavia no registraron
    el pago de la mensualidad. Es el aviso preventivo: resta aproximadamente
    un dia para que termine el plazo de pago del dia 10.
    """
    try:
        today = datetime.now(TZ_AR).date()
        if today.day != 9:
            return {
                'message': 'No corresponde enviar recordatorios de cercanía de vencimiento hoy.',
                'sent_count': 0,
                'skipped_count': 0,
                'errors': [],
            }

        month_key = _month_key(today)
        sent_count = 0
        skipped_count = 0
        errors = []

        for user in _active_subscribers():
            user_id = str(user['id'])
            if _subscription_payment_exists_this_month(user_id, today):
                continue

            event_key = f'{SUBSCRIPTION_DUE_SOON_EVENT_TYPE}:{user_id}:{month_key}'
            try:
                if not _claim_delivery(
                    event_key,
                    SUBSCRIPTION_DUE_SOON_EVENT_TYPE,
                    user_id,
                    class_id=None,
                ):
                    skipped_count += 1
                    continue

                message = (
                    'Estás cerca del vencimiento del plazo para abonar tu mensualidad. '
                    'Tenés tiempo hasta el día 10 del mes para registrar el pago.'
                )

                try:
                    _create_system_notification(
                        user_id,
                        'Vencimiento de mensualidad cercano',
                        message
                    )
                except Exception:
                    pass

                if user.get('email'):
                    send_subscription_due_soon_email(
                        user['email'],
                        user.get('name', 'usuario/a')
                    )

                sent_count += 1
            except Exception as e:
                errors.append({
                    'user_id': user_id,
                    'error': str(e),
                })

        return {
            'message': 'Proceso de avisos de cercanía de vencimiento de suscripción finalizado.',
            'sent_count': sent_count,
            'skipped_count': skipped_count,
            'errors': errors,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al avisar cercanía de vencimiento de suscripción: {str(e)}')


def notificar_vencimiento_plazo_pago_deuda():
    """
    Notifica a clientes abonados desde el dia 11 del mes si no registraron el
    pago de la mensualidad dentro de los primeros 10 dias.
    """
    try:
        today = datetime.now(TZ_AR).date()
        if today.day <= 10:
            return {
                'message': 'El plazo de pago de mensualidad todavía no venció.',
                'sent_count': 0,
                'skipped_count': 0,
                'errors': [],
            }

        month_key = _month_key(today)
        sent_count = 0
        skipped_count = 0
        errors = []

        for user in _active_subscribers():
            user_id = str(user['id'])
            if _subscription_payment_exists_this_month(user_id, today):
                continue

            event_key = f'{SUBSCRIPTION_PAYMENT_EXPIRED_EVENT_TYPE}:{user_id}:{month_key}'
            try:
                if not _claim_delivery(
                    event_key,
                    SUBSCRIPTION_PAYMENT_EXPIRED_EVENT_TYPE,
                    user_id,
                    class_id=None,
                ):
                    skipped_count += 1
                    continue

                message = (
                    'Venció el plazo de 10 días para abonar tu mensualidad. '
                    'Regularizá tu situación para evitar restricciones sobre tu cuenta.'
                )

                try:
                    _create_system_notification(
                        user_id,
                        'Venció el plazo de pago de la mensualidad',
                        message
                    )
                except Exception:
                    pass

                if user.get('email'):
                    send_subscription_payment_deadline_expired_email(
                        user['email'],
                        user.get('name', 'usuario/a')
                    )

                sent_count += 1
            except Exception as e:
                errors.append({
                    'user_id': user_id,
                    'error': str(e),
                })

        return {
            'message': 'Proceso de avisos de vencimiento de plazo de pago finalizado.',
            'sent_count': sent_count,
            'skipped_count': skipped_count,
            'errors': errors,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al avisar vencimiento de plazo de pago: {str(e)}')
