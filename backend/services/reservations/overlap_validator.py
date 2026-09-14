from datetime import datetime, timezone

from database import supabase
from fastapi import HTTPException


def validate_user_has_no_overlapping_class(user_id: str, class_id: str, target_class: dict | None = None):
    """
    Evita que un usuario reserve o se anote en espera para clases que se pisan
    en horario, aunque sean clases distintas.
    """
    user_id = str(user_id)
    class_id = str(class_id)
    target_class = target_class or _get_class(class_id)

    target_start = target_class.get('start_time')
    target_end = target_class.get('end_time')
    if not target_start or not target_end:
        raise HTTPException(status_code=400, detail='La clase no tiene horario completo configurado.')

    _validate_against_reservations(user_id, class_id, target_start, target_end)
    _validate_against_waitlist(user_id, class_id, target_start, target_end)


def _get_class(class_id: str):
    response = (
        supabase.table('classes')
        .select('id, start_time, end_time')
        .eq('id', class_id)
        .single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail='Clase no encontrada.')
    return response.data


def _validate_against_reservations(user_id: str, class_id: str, target_start, target_end):
    reservations = (
        supabase.table('reservations')
        .select('id, class_id, classes(id, start_time, end_time)')
        .eq('user_id', user_id)
        .neq('status', 'CANCELADA')
        .execute()
    ).data or []

    for reservation in reservations:
        if str(reservation.get('class_id')) == class_id:
            continue
        clase = reservation.get('classes') or {}
        if _commitment_overlaps(clase, target_start, target_end):
            raise HTTPException(
                status_code=400,
                detail='Ya tenés una reserva o lista de espera en ese horario.'
            )


def _validate_against_waitlist(user_id: str, class_id: str, target_start, target_end):
    waitlist_entries = (
        supabase.table('waitlist')
        .select('id, class_id, classes(id, start_time, end_time)')
        .eq('user_id', user_id)
        .execute()
    ).data or []

    for entry in waitlist_entries:
        if str(entry.get('class_id')) == class_id:
            continue
        clase = entry.get('classes') or {}
        if _commitment_overlaps(clase, target_start, target_end):
            raise HTTPException(
                status_code=400,
                detail='Ya tenés una reserva o lista de espera en ese horario.'
            )


def _commitment_overlaps(clase: dict, target_start, target_end):
    existing_start = clase.get('start_time')
    existing_end = clase.get('end_time')
    if not existing_start or not existing_end:
        return False
    return _overlaps(existing_start, existing_end, target_start, target_end)


def _overlaps(existing_start, existing_end, target_start, target_end):
    existing_start = _to_utc(existing_start)
    existing_end = _to_utc(existing_end)
    target_start = _to_utc(target_start)
    target_end = _to_utc(target_end)
    return target_start < existing_end and target_end > existing_start


def _to_utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
