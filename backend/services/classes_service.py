from fastapi import HTTPException
from database import supabase

from utils.class_validators import (
    validate_room_exists,
    validate_room_status,
    validate_room_capacity,
    validate_room_availability
)


def create_class(data):

    try:

        # Validar sala existente
        room = validate_room_exists(data.room_id)

        # Validar estado sala
        validate_room_status(room)

        # Validar capacidad
        validate_room_capacity(
            room['capacity'],
            data.max_capacity
        )

        # Validar disponibilidad horaria
        validate_room_availability(
            data.room_id,
            data.start_time,
            data.end_time
        )

        # Crear clase
        new_class = (
            supabase.table('classes')
            .insert({
                'room_id': str(data.room_id),
                'professor_id': (
                    str(data.professor_id)
                    if data.professor_id
                    else None
                ),

                'type': data.type,
                'activity_type': data.activity_type,

                'is_scheduled': data.is_scheduled,

                'status': 'activa',

                'max_capacity': data.max_capacity,
                'current_capacity': 0,

                'start_time': data.start_time.isoformat(),
                'end_time': data.end_time.isoformat(),
            })
            .execute()
        )

        return {
            'message': 'La clase se creo exitosamente',
            'data': new_class.data[0]
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error al crear la clase: {str(e)}'
        )


def list_active_classes():

    try:

        response = (
            supabase.table('classes')
            .select(
                '''
                *,
                rooms(
                    id,
                    name,
                    capacity
                )
                '''
            )
            .eq('status', 'activa')
            .order('start_time', desc=False)
            .execute()
        )

        return response.data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error al obtener las clases: {str(e)}'
        )
