from fastapi import HTTPException
from database import supabase


def validate_center_business_hours(start_time, end_time):
    if start_time.weekday() >= 5 or end_time.weekday() >= 5:
        raise HTTPException(
            status_code=400,
            detail='Las clases solo pueden programarse de lunes a viernes.'
        )

    if start_time.date() != end_time.date():
        raise HTTPException(
            status_code=400,
            detail='La clase debe iniciar y finalizar el mismo dia.'
        )

    opening_minutes = 8 * 60
    closing_minutes = 20 * 60
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute

    if start_minutes < opening_minutes or end_minutes > closing_minutes:
        raise HTTPException(
            status_code=400,
            detail='Las clases deben programarse dentro del horario del centro: 08:00 a 20:00.'
        )


def validate_room_exists(room_id):
    response = (
        supabase.table('rooms')
        .select('id, name, capacity, status')
        .eq('id', str(room_id))
        .single()
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail='La sala seleccionada no existe.'
        )

    return response.data


def validate_room_status(room):
    # FIX: era != 'activa'; el CHECK de rooms.status acepta DISPONIBLE/OCUPADA/MANTENIMIENTO
    if room['status'] != 'DISPONIBLE':
        raise HTTPException(
            status_code=400,
            detail='La sala seleccionada no está disponible.'
        )


def validate_room_capacity(room_capacity, requested_capacity):
    if requested_capacity > room_capacity:
        raise HTTPException(
            status_code=400,
            detail='Debe ingresar un cupo menor o igual a la capacidad maxima de la sala'
        )


def validate_room_availability(room_id, start_time, end_time):

    response = (
        supabase.table('classes')
        .select('id, start_time, end_time')
        .eq('room_id', str(room_id))
        .neq('status', 'CANCELADA')  # FIX: era 'cancelada' (minúscula)
        .execute()
    )

    existing_classes = response.data

    for existing_class in existing_classes:

        existing_start = existing_class['start_time']
        existing_end = existing_class['end_time']

        if (
            start_time.isoformat() < existing_end
            and
            end_time.isoformat() > existing_start
        ):
            raise HTTPException(
                status_code=409,
                detail='Sala ocupada para el horario seleccionado'
            )
