from fastapi import HTTPException
from database import supabase
from datetime import datetime, timedelta, timezone


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


def validate_professor_weekly_hours(professor_id, new_start: datetime, new_end: datetime):
    """
    Valida que el profesor no supere las 40 horas semanales.
    Calcula las horas ya asignadas en la semana de la clase nueva
    y verifica que sumando la nueva clase no se exceda el límite.
    """
    # Calcular inicio y fin de la semana (lunes a domingo) de la clase a asignar
    week_start = (new_start - timedelta(days=new_start.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7)

    response = (
        supabase.table('classes')
        .select('start_time, end_time')
        .eq('professor_id', str(professor_id))
        .neq('status', 'cancelada')
        .gte('start_time', week_start.isoformat())
        .lt('start_time', week_end.isoformat())
        .execute()
    )

    existing_classes = response.data or []

    total_seconds = sum(
        (
            datetime.fromisoformat(c['end_time']) -
            datetime.fromisoformat(c['start_time'])
        ).total_seconds()
        for c in existing_classes
    )

    new_class_seconds = (new_end - new_start).total_seconds()
    total_hours = (total_seconds + new_class_seconds) / 3600

    if total_hours > 40:
        raise HTTPException(
            status_code=400,
            detail='El profesor seleccionado supera las 40 horas semanales.'
        )


def validate_professor_schedule_availability(professor_id, new_start: datetime, new_end: datetime):
    """
    Valida que el profesor no tenga otra clase en el mismo horario.
    """
    response = (
        supabase.table('classes')
        .select('id, start_time, end_time')
        .eq('professor_id', str(professor_id))
        .neq('status', 'cancelada')
        .execute()
    )

    existing_classes = response.data or []

    for existing_class in existing_classes:
        existing_start = existing_class['start_time']
        existing_end = existing_class['end_time']

        if (
            new_start.isoformat() < existing_end
            and
            new_end.isoformat() > existing_start
        ):
            raise HTTPException(
                status_code=409,
                detail='El profesor seleccionado no está disponible en este horario.'
            )
