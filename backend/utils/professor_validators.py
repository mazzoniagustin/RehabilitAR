from fastapi import HTTPException
from database import supabase
from datetime import datetime, timedelta, timezone


def _to_utc(dt: datetime) -> datetime:
    """
    Normaliza un datetime a UTC aware.
    - Si ya tiene timezone: convierte a UTC.
    - Si es naive: asume UTC y lo marca como tal.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_professor_exists(professor_id):
    response = (
        supabase.table('users')
        .select('id, name, surname, rol, account_status')
        .eq('id', str(professor_id))
        .single()
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail='El profesor seleccionado no existe.'
        )

    if response.data['rol'] != 'PROFESOR':
        raise HTTPException(
            status_code=400,
            detail='El usuario seleccionado no tiene el rol de profesor.'
        )

    if response.data['account_status'] != 'ACTIVA':
        raise HTTPException(
            status_code=400,
            detail='El profesor seleccionado no tiene una cuenta activa.'
        )

    return response.data


def validate_professor_weekly_hours(
    professor_id,
    new_start: datetime,
    new_end: datetime,
    exclude_class_id: str = None
):
    """
    Valida que el profesor no supere las 40 horas semanales.
    Calcula las horas ya asignadas en la semana de la clase nueva
    y verifica que sumando la nueva clase no se exceda el límite.

    exclude_class_id: excluye una clase del conteo (evita doble conteo
    al reasignar un profesor a una clase que ya le pertenecía).
    """
    new_start_utc = _to_utc(new_start)
    new_end_utc = _to_utc(new_end)

    # Calcular inicio y fin de la semana (lunes a domingo) en UTC
    week_start = (new_start_utc - timedelta(days=new_start_utc.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7)

    query = (
        supabase.table('classes')
        .select('id, start_time, end_time')
        .eq('professor_id', str(professor_id))
        .neq('status', 'CANCELADA')  # FIX: era 'cancelada' (minúscula)
        .gte('start_time', week_start.isoformat())
        .lt('start_time', week_end.isoformat())
    )

    if exclude_class_id:
        query = query.neq('id', exclude_class_id)

    response = query.execute()
    existing_classes = response.data or []

    total_seconds = sum(
        (
            _to_utc(datetime.fromisoformat(c['end_time'])) -
            _to_utc(datetime.fromisoformat(c['start_time']))
        ).total_seconds()
        for c in existing_classes
    )

    new_class_seconds = (new_end_utc - new_start_utc).total_seconds()
    total_hours = (total_seconds + new_class_seconds) / 3600

    if total_hours > 40:
        raise HTTPException(
            status_code=400,
            detail='El profesor seleccionado supera las 40 horas semanales.'
        )


def validate_professor_schedule_availability(
    professor_id,
    new_start: datetime,
    new_end: datetime,
    exclude_class_id: str = None
):
    """
    Valida que el profesor no tenga otra clase en el mismo horario.

    exclude_class_id: excluye una clase del chequeo (evita falso conflicto
    al reasignar un profesor a una clase que ya le pertenecía).
    """
    new_start_utc = _to_utc(new_start)
    new_end_utc = _to_utc(new_end)

    query = (
        supabase.table('classes')
        .select('id, start_time, end_time')
        .eq('professor_id', str(professor_id))
        .neq('status', 'CANCELADA')  # FIX: era 'cancelada' (minúscula)
    )

    if exclude_class_id:
        query = query.neq('id', exclude_class_id)

    response = query.execute()
    existing_classes = response.data or []

    for existing_class in existing_classes:
        existing_start = _to_utc(datetime.fromisoformat(existing_class['start_time']))
        existing_end = _to_utc(datetime.fromisoformat(existing_class['end_time']))

        if new_start_utc < existing_end and new_end_utc > existing_start:
            raise HTTPException(
                status_code=409,
                detail='El profesor seleccionado no está disponible en este horario.'
            )
