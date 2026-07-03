from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from database import supabase, supabase_admin
from services.classes_service import list_professors
from services.notifications_service import create_notification
from utils.class_desc import build_class_desc
from utils.notifications import send_no_professor_class_email

NO_PROFESSOR_EVENT_TYPE = 'NO_PROFESSOR_CLASS_REMINDER'
NOTIFICATION_HOURS_BEFORE = 24
CANCELLATION_HOURS_BEFORE = 12


def _client():
    return supabase_admin or supabase


def _event_key(class_id: str, professor_id: str) -> str:
    return f'{NO_PROFESSOR_EVENT_TYPE}:{class_id}:{professor_id}'


def _claim_delivery(event_key: str, user_id: str, class_id: str) -> bool:
    """
    Registra el aviso antes de enviarlo para que el job no repita mails
    si vuelve a ejecutarse dentro de la misma ventana de 24 horas.
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
        'event_type': NO_PROFESSOR_EVENT_TYPE,
        'user_id': user_id,
        'class_id': class_id,
    }).execute()
    return True


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


def avisar_profesores_clases_sin_profesor():
    """
    Notifica a profesores disponibles cuando una clase sin profesor asignado
    comienza dentro de las próximas 24 horas, pero aún no entró en la ventana
    de cancelación automática de 12 horas.
    """
    try:
        now = datetime.now(timezone.utc)
        cancellation_limit = now + timedelta(hours=CANCELLATION_HOURS_BEFORE)
        notification_limit = now + timedelta(hours=NOTIFICATION_HOURS_BEFORE)

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
                    event_key = _event_key(class_id, professor_id)
                    professor = professor_details.get(professor_id, {})

                    try:
                        if not _claim_delivery(event_key, professor_id, class_id):
                            skipped_count += 1
                            continue

                        try:
                            create_notification(
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
