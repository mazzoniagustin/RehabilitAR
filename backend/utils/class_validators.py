from fastapi import HTTPException
from database import supabase


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
    if room['status'] != 'activa':
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
        .neq('status', 'cancelada')
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