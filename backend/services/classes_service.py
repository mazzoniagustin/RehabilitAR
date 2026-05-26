from typing import Optional
from fastapi import HTTPException
from database import supabase
from datetime import datetime

from utils.class_validators import (
    validate_center_business_hours,
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

        validate_center_business_hours(
            data.start_time,
            data.end_time
        )

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


def cancel_class(class_id: str):
    try:
        class_response = supabase.table('classes').select('id, status').eq('id', class_id).single().execute()
        if not class_response.data:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')
        
        clase = class_response.data
        if clase['status'] == 'CANCELADA':
            raise HTTPException(status_code=400, detail='La clase ya se encuentra cancelada.')
            
        updated_class = supabase.table('classes').update({'status': 'CANCELADA'}).eq('id', class_id).execute()
        
        return {
            'message': 'Clase cancelada exitosamente',
            'data': updated_class.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la clase: {str(e)}')

def update_capacity(class_id: str, new_capacity: int):
    try:
        class_response = supabase.table('classes').select('id, max_capacity, room_id, status, rooms(capacity)').eq('id', class_id).single().execute()
        
        if not class_response.data:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')
            
        clase = class_response.data
        
        if clase['status'] != 'PROGRAMADA' and clase['status'] != 'EN CURSO':
            raise HTTPException(status_code=400, detail='Solo se puede modificar el cupo de clases activas.')
            
        room_capacity = clase['rooms']['capacity']
        
        if new_capacity > room_capacity:
            raise HTTPException(status_code=400, detail='El cupo ingresado supera la capacidad máxima de la sala')
            
        # Get current inscribed students count
        reservations_response = supabase.table('reservations').select('id', count='exact').eq('class_id', class_id).in_('status', ['CONFIRMADA']).execute()
        current_inscribed = reservations_response.count if reservations_response.count is not None else 0
        
        if new_capacity < current_inscribed:
            # Cancel class automatically
            updated_class = supabase.table('classes').update({'status': 'CANCELADA'}).eq('id', class_id).execute()
            return {
                'message': 'El nuevo cupo es menor a los inscriptos. La clase ha sido cancelada.',
                'data': updated_class.data[0]
            }
            
        updated_class = supabase.table('classes').update({'max_capacity': new_capacity}).eq('id', class_id).execute()
        
        return {
            'message': 'Cupo de clase actualizado exitosamente',
            'data': updated_class.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al modificar el cupo de la clase: {str(e)}')


def create_professor_request(class_id: str, professor_id: str):
    try:
        class_response = supabase.table('classes').select('id, professor_id, start_time, end_time, status').eq('id', class_id).single().execute()
        if not class_response.data:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')

        if class_response.data['status'] not in ('PROGRAMADA', 'EN CURSO'):
            raise HTTPException(status_code=400, detail='No se puede solicitar una clase que no esta activa.')

        if class_response.data['professor_id'] is not None:
            raise HTTPException(status_code=400, detail='La clase ya tiene un profesor asignado.')
            
        # check existing request
        req_check = supabase.table('professor_requests').select('id, status').eq('class_id', class_id).eq('professor_id', professor_id).execute()
        if req_check.data and any(r['status'] == 'PENDIENTE' for r in req_check.data):
            raise HTTPException(status_code=400, detail='Ya existe una solicitud pendiente para esta clase.')
            
        new_request = supabase.table('professor_requests').insert({
            'class_id': class_id,
            'professor_id': professor_id,
            'status': 'PENDIENTE'
        }).execute()
        
        return {'message': 'Solicitud enviada correctamente', 'data': new_request.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al crear la solicitud: {str(e)}')


def list_pending_professor_requests():
    try:
        response = (
            supabase.table('professor_requests')
            .select('id, class_id, professor_id, status, created_at')
            .eq('status', 'PENDIENTE')
            .order('created_at', desc=False)
            .execute()
        )

        requests = response.data or []
        if not requests:
            return []

        professor_ids = list({r['professor_id'] for r in requests})
        class_ids = list({r['class_id'] for r in requests})

        professors_response = (
            supabase.table('users')
            .select('id, name, surname, specialty')
            .in_('id', professor_ids)
            .execute()
        )
        professors_by_id = {
            professor['id']: professor
            for professor in (professors_response.data or [])
        }

        classes_response = (
            supabase.table('classes')
            .select('id, type, activity_type, start_time, end_time, professor_id, room_id')
            .in_('id', class_ids)
            .execute()
        )

        classes = classes_response.data or []
        room_ids = list({c['room_id'] for c in classes if c.get('room_id')})
        rooms_by_id = {}

        if room_ids:
            rooms_response = (
                supabase.table('rooms')
                .select('id, name')
                .in_('id', room_ids)
                .execute()
            )
            rooms_by_id = {
                room['id']: room
                for room in (rooms_response.data or [])
            }

        classes_by_id = {}
        for clase in classes:
            clase['rooms'] = rooms_by_id.get(clase.get('room_id'))
            classes_by_id[clase['id']] = clase

        for request in requests:
            request['users'] = professors_by_id.get(request['professor_id'])
            request['classes'] = classes_by_id.get(request['class_id'])

        return requests
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener solicitudes pendientes: {str(e)}')


def list_professor_requests(professor_id: str):
    try:
        response = (
            supabase.table('professor_requests')
            .select('id, class_id, status, reject_reason, created_at')
            .eq('professor_id', professor_id)
            .order('created_at', desc=True)
            .execute()
        )

        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener tus solicitudes: {str(e)}')


def evaluate_professor_request(class_id: str, request_id: str, data):
    try:
        req_response = supabase.table('professor_requests').select('*, classes(start_time, end_time, status, professor_id)').eq('id', request_id).single().execute()
        if not req_response.data:
            raise HTTPException(status_code=404, detail='Solicitud no encontrada.')
            
        request_obj = req_response.data
        if request_obj['class_id'] != class_id:
            raise HTTPException(status_code=400, detail='La solicitud no corresponde a esta clase.')
            
        if request_obj['status'] != 'PENDIENTE':
            raise HTTPException(status_code=400, detail='La solicitud ya fue evaluada.')
            
        if data.status == 'RECHAZADA':
            if not data.reason or not data.reason.strip():
                raise HTTPException(status_code=400, detail='El rechazo debe incluir un motivo obligatorio')
                
            updated = supabase.table('professor_requests').update({'status': 'RECHAZADA', 'reject_reason': data.reason}).eq('id', request_id).execute()
            return {'message': 'Solicitud rechazada correctamente con motivo', 'data': updated.data[0]}
            
        # ACEPTADA
        clase = request_obj['classes']

        if clase['status'] not in ('PROGRAMADA', 'EN CURSO'):
            raise HTTPException(status_code=400, detail='La clase ya no está activa.')

        if clase['professor_id'] is not None:
            raise HTTPException(status_code=400, detail='La clase ya tiene un profesor asignado.')
            
        class_start = datetime.fromisoformat(clase['start_time'])
        class_end = datetime.fromisoformat(clase['end_time'])
        
        try:
            validate_professor_weekly_hours(request_obj['professor_id'], class_start, class_end)
        except HTTPException:
            raise HTTPException(status_code=400, detail='No se puede asignar el profesor porque supera el límite de 40 horas semanales')
            
        try:
            validate_professor_schedule_availability(request_obj['professor_id'], class_start, class_end)
        except HTTPException:
            raise HTTPException(status_code=400, detail='No se puede asignar el profesor por conflicto de horario')
            
        # All ok, update class and request
        supabase.table('classes').update({'professor_id': request_obj['professor_id']}).eq('id', class_id).execute()
        updated = supabase.table('professor_requests').update({'status': 'ACEPTADA'}).eq('id', request_id).execute()
        
        return {'message': 'Se aceptó la solicitud correctamente', 'data': updated.data[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al evaluar la solicitud: {str(e)}')

def list_class_students(class_id: str):
    try:
        class_check = supabase.table('classes').select('id').eq('id', class_id).single().execute()
        if not class_check.data:
            raise HTTPException(status_code=404, detail='Clase no encontrada.')
            
        res = supabase.table('reservations').select('user_id, users(name, surname, email, phone)').eq('class_id', class_id).in_('status', ['CONFIRMADA']).execute()
        
        return res.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener inscriptos: {str(e)}')
