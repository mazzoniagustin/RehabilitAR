from fastapi import HTTPException
from database import supabase
from datetime import datetime

from utils.class_validators import (
    validate_room_exists,
    validate_room_status,
    validate_room_capacity,
    validate_room_availability
)

from utils.professor_validators import (
    validate_professor_exists,
    validate_professor_weekly_hours,
    validate_professor_schedule_availability
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

        if data.professor_id:
            validate_professor_exists(data.professor_id)
            validate_professor_weekly_hours(
                data.professor_id,
                data.start_time,
                data.end_time
            )
            validate_professor_schedule_availability(
                data.professor_id,
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

                'status': 'PROGRAMADA',  # FIX: era 'activa', no existe en el CHECK

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
            .eq('status', 'PROGRAMADA')  # FIX: era 'activa', no existe en el CHECK
            .order('start_time', desc=False)
            .execute()
        )

        return response.data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error al obtener las clases: {str(e)}'
        )


def list_rooms():

    try:

        response = (
            supabase.table('rooms')
            .select('id, name, capacity, status')
            .order('name', desc=False)
            .execute()
        )

        return response.data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error al obtener las salas: {str(e)}'
        )


def list_professors():

    try:

        response = (
            supabase.table('users')
            .select('id, name, surname, specialty, account_status')
            .eq('rol', 'PROFESOR')
            .eq('account_status', 'ACTIVA')
            .order('surname', desc=False)
            .execute()
        )

        return response.data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error al obtener los profesores: {str(e)}'
        )


def assign_professor(class_id: str, data):

    try:

        # Verificar que la clase existe y está programada
        class_response = (
            supabase.table('classes')
            .select('id, professor_id, start_time, end_time, status')
            .eq('id', class_id)
            .single()
            .execute()
        )

        if not class_response.data:
            raise HTTPException(
                status_code=404,
                detail='La clase seleccionada no existe.'
            )

        clase = class_response.data

        # FIX: era != 'activa'; los estados válidos son PROGRAMADA / EN CURSO
        if clase['status'] not in ('PROGRAMADA', 'EN CURSO'):
            raise HTTPException(
                status_code=400,
                detail='No se puede asignar un profesor a una clase que no está activa.'
            )

        # Validar que no se intente asignar el mismo profesor que ya tiene la clase
        if clase['professor_id'] and clase['professor_id'] == str(data.professor_id):
            raise HTTPException(
                status_code=400,
                detail='El profesor seleccionado ya está asignado a esta clase.'
            )

        # Parsear horarios de la clase (Supabase devuelve timestamptz)
        class_start = datetime.fromisoformat(clase['start_time'])
        class_end = datetime.fromisoformat(clase['end_time'])

        # Validar que el profesor existe y tiene el rol correcto
        validate_professor_exists(data.professor_id)

        # Validar que no supere las 40 horas semanales.
        # Se excluye la clase actual para evitar doble conteo en caso de reasignación.
        validate_professor_weekly_hours(
            data.professor_id,
            class_start,
            class_end,
            exclude_class_id=class_id
        )

        # Validar disponibilidad horaria del profesor.
        # Se excluye la clase actual para evitar falso conflicto en reasignación.
        validate_professor_schedule_availability(
            data.professor_id,
            class_start,
            class_end,
            exclude_class_id=class_id
        )

        # Asignar el profesor a la clase
        updated_class = (
            supabase.table('classes')
            .update({'professor_id': str(data.professor_id)})
            .eq('id', class_id)
            .execute()
        )

        return {
            'message': 'Se asignó el profesor correctamente.',
            'data': updated_class.data[0]
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error al asignar el profesor: {str(e)}'
        )
