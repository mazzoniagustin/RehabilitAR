from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from database import supabase, supabase_admin
from services.notifications_service import create_notification
from utils.class_desc import build_class_desc
from utils.notifications import send_attendance_reminder_email

REMINDER_EVENT_TYPE = 'ATTENDANCE_REMINDER'
REMINDER_HOURS_BEFORE = 24


def _client():
    return supabase_admin or supabase


def _event_key(reservation_id: str) -> str:
    return f'{REMINDER_EVENT_TYPE}:{reservation_id}'


def _claim_delivery(event_key: str, user_id: str, class_id: str, reservation_id: str) -> bool:
    """
    Registra el evento antes de enviar para que el job sea idempotente.
    Si la clave ya existe, el recordatorio ya fue procesado.
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

    _client().table('notification_delivery_log').insert({
        'event_key': event_key,
        'event_type': REMINDER_EVENT_TYPE,
        'user_id': user_id,
        'class_id': class_id,
        'reservation_id': reservation_id,
    }).execute()
    return True


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
                event_key = _event_key(reservation_id)

                try:
                    if not _claim_delivery(event_key, user_id, class_id, reservation_id):
                        skipped_count += 1
                        continue

                    try:
                        create_notification(
                            user_id,
                            'Recordatorio de asistencia',
                            f'Te recordamos que tenés una clase reservada de {class_desc}.'
                        )
                    except Exception:
                        # El mail sigue saliendo aunque la notificacion in-app falle
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
