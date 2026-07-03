from typing import Optional, List
from fastapi import HTTPException
from database import supabase
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo

TZ_AR = ZoneInfo('America/Argentina/Buenos_Aires')
import calendar

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

from schemes.class_scheme import CLASS_DURATION_MINUTES
from services.notifications_service import create_notification
from utils.notifications import send_professor_request_accepted, send_professor_request_rejected


# ── Helpers de fecha ──────────────────────────────────────────────────────────

def _parse_optional_datetime(value: Optional[str], field_name: str):
    if not value:
        return None
    try:
        normalized = value.replace('Z', '+00:00').replace(' ', 'T')
        if normalized.endswith('+00') or normalized.endswith('-00'):
            normalized += ':00'
        return datetime.fromisoformat(normalized)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f'{field_name} debe tener formato de fecha y hora valido.'
        )


def _parse_time_range(start_time: Optional[str], end_time: Optional[str]):
    if bool(start_time) != bool(end_time):
        raise HTTPException(
            status_code=400,
            detail='Debe enviar start_time y end_time para filtrar disponibilidad.'
        )
    start = _parse_optional_datetime(start_time, 'start_time')
    end = _parse_optional_datetime(end_time, 'end_time')
    if start and end:
        if end <= start:
            raise HTTPException(
                status_code=400,
                detail='La hora de finalizacion debe ser mayor a la hora de inicio.'
            )
        validate_center_business_hours(start, end)
    return start, end


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        # Naive datetimes se interpretan como hora argentina (UTC-3)
        return dt.replace(tzinfo=ZoneInfo('America/Argentina/Buenos_Aires')).astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)


# Debe coincidir con la ventana usada en
# services/cancellations/classes_cancellation_service.cancelar_clases_sin_profesor
NO_PROFESSOR_WINDOW_HOURS = 12


def _validate_not_too_close_without_professor(start_time: datetime):
    """
    Si la clase se crea sin profesor asignado, no se permite que su inicio caiga
    dentro de la ventana de cancelación automática por falta de profesor (12hs).
    Si se permitiera, la clase quedaría PROGRAMADA solo hasta el próximo ciclo
    de cancelación automática, dando la falsa impresión de haberse creado bien.
    """
    now_utc = datetime.now(timezone.utc)
    start_utc = _to_utc(start_time)
    hours_until_start = (start_utc - now_utc).total_seconds() / 3600
    if hours_until_start <= NO_PROFESSOR_WINDOW_HOURS:
        raise HTTPException(
            status_code=400,
            detail=(
                'No se puede crear la clase sin profesor asignado: falta menos de 12 horas '
                'para el horario de inicio, por lo que quedaría sujeta a cancelación '
                'automática por falta de profesor. Asigná un profesor o elegí un horario '
                'con más anticipación.'
            )
        )


def _overlaps(existing_start, existing_end, start_time, end_time):
    existing_start = _to_utc(datetime.fromisoformat(existing_start.replace('Z', '+00:00')))
    existing_end = _to_utc(datetime.fromisoformat(existing_end.replace('Z', '+00:00')))
    start_time = _to_utc(start_time)
    end_time = _to_utc(end_time)
    return start_time < existing_end and end_time > existing_start


def _occurrences_in_month(day_of_week: int, year: int, month: int) -> List[date]:
    """Devuelve todas las fechas del mes (year, month) que caen en day_of_week (0=lun)."""
    _, last_day = calendar.monthrange(year, month)
    result = []
    for d in range(1, last_day + 1):
        dt = date(year, month, d)
        if dt.weekday() == day_of_week:
            result.append(dt)
    return result


def _target_month(day_of_week: int) -> tuple[int, int]:
    """
    Determina el mes objetivo para crear las clases FIJA:
    - Si quedan ocurrencias futuras del día elegido en el mes actual → mes actual.
    - Si ya pasaron todas → mes siguiente.
    """
    today = datetime.now(TZ_AR).date()
    _, last_day = calendar.monthrange(today.year, today.month)
    for d in range(today.day, last_day + 1):
        dt = date(today.year, today.month, d)
        if dt.weekday() == day_of_week:
            return today.year, today.month
    # Avanzar al mes siguiente
    if today.month == 12:
        return today.year + 1, 1
    return today.year, today.month + 1


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _future_occurrences_for_schedule(
    day_of_week: int,
    start_hour: int,
    start_minute: int
) -> tuple[int, int, List[date]]:
    year, month = _target_month(day_of_week)
    now = datetime.now(TZ_AR)

    occurrences = []
    for occ_date in _occurrences_in_month(day_of_week, year, month):
        start_dt = datetime(
            occ_date.year, occ_date.month, occ_date.day,
            start_hour, start_minute,
            tzinfo=TZ_AR
        )
        if start_dt > now:
            occurrences.append(occ_date)

    if occurrences:
        return year, month, occurrences

    year, month = _next_month(year, month)
    return year, month, _occurrences_in_month(day_of_week, year, month)


# ── Crear clase INDIVIDUAL ────────────────────────────────────────────────────

def create_individual_class(data):
    try:
        end_time = data.start_time + timedelta(minutes=CLASS_DURATION_MINUTES)

        room = validate_room_exists(data.room_id)
        validate_center_business_hours(data.start_time, end_time)
        validate_room_status(room)
        validate_room_capacity(room['capacity'], data.max_capacity)
        validate_room_availability(data.room_id, data.start_time, end_time)

        if data.professor_id:
            validate_professor_exists(data.professor_id)
            validate_professor_weekly_hours(data.professor_id, data.start_time, end_time)
            validate_professor_schedule_availability(data.professor_id, data.start_time, end_time)
        else:
            _validate_not_too_close_without_professor(data.start_time)

        new_class = (
            supabase.table('classes')
            .insert({
                'room_id': str(data.room_id),
                'professor_id': str(data.professor_id) if data.professor_id else None,
                'type': 'INDIVIDUAL',
                'activity_type': data.activity_type,
                'status': 'PROGRAMADA',
                'max_capacity': data.max_capacity,
                'current_capacity': 0,
                'start_time': data.start_time.isoformat(),
                'end_time': end_time.isoformat(),
            })
            .execute()
        )

        return {
            'message': 'La clase individual se creó exitosamente.',
            'data': new_class.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al crear la clase individual: {str(e)}')


# ── Crear clases FIJA ─────────────────────────────────────────────────────────

def create_fija_class(data):
    """
    Genera una clase FIJA por cada ocurrencia del día elegido en el mes objetivo.
    Valida sala, horario y disponibilidad para cada instancia antes de insertar.
    """
    try:
        room = validate_room_exists(data.room_id)
        validate_room_status(room)
        validate_room_capacity(room['capacity'], data.max_capacity)

        if data.professor_id:
            validate_professor_exists(data.professor_id)

        year, month, occurrences = _future_occurrences_for_schedule(
            data.day_of_week,
            data.start_hour,
            data.start_minute
        )

        if not occurrences:
            raise HTTPException(
                status_code=400,
                detail='No hay ocurrencias disponibles para el día seleccionado en el mes objetivo.'
            )

        day_names = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes']

        conflicts = []
        rows_to_insert = []
        professor_assigned_count = 0

        for occ_date in occurrences:
            start_dt = datetime(
                occ_date.year, occ_date.month, occ_date.day,
                data.start_hour, data.start_minute,
                tzinfo=TZ_AR
            )
            end_dt = start_dt + timedelta(minutes=CLASS_DURATION_MINUTES)

            # Validar horario del centro para esta ocurrencia
            try:
                validate_center_business_hours(start_dt, end_dt)
            except HTTPException as e:
                conflicts.append({'date': occ_date.isoformat(), 'reason': e.detail})
                continue

            # Validar disponibilidad de sala
            try:
                validate_room_availability(data.room_id, start_dt, end_dt)
            except HTTPException as e:
                conflicts.append({
                    'date': occ_date.isoformat(),
                    'reason': e.detail or 'Sala ocupada en ese horario.'
                })
                continue

            professor_id = None
            if data.professor_id:
                try:
                    validate_professor_weekly_hours(data.professor_id, start_dt, end_dt)
                    validate_professor_schedule_availability(data.professor_id, start_dt, end_dt)
                    professor_id = str(data.professor_id)
                    professor_assigned_count += 1
                except HTTPException:
                    professor_id = None

            if professor_id is None:
                try:
                    _validate_not_too_close_without_professor(start_dt)
                except HTTPException as e:
                    conflicts.append({'date': occ_date.isoformat(), 'reason': e.detail})
                    continue

            rows_to_insert.append({
                'room_id': str(data.room_id),
                'professor_id': professor_id,
                'type': 'FIJA',
                'activity_type': data.activity_type,
                'status': 'PROGRAMADA',
                'max_capacity': data.max_capacity,
                'current_capacity': 0,
                'start_time': start_dt.isoformat(),
                'end_time': end_dt.isoformat(),
            })

        if conflicts:
            conflict_details = '; '.join(
                f"{item['date']}: {item['reason']}" for item in conflicts
            )
            raise HTTPException(
                status_code=409,
                detail=(
                    'No se puede crear la clase fija porque todas las fechas deben tener '
                    f'disponibilidad para la sala elegida. '
                    f'Conflictos: {conflict_details}'
                )
            )

        if data.professor_id and professor_assigned_count == 0:
            raise HTTPException(
                status_code=409,
                detail='El profesor seleccionado no está disponible para ninguna de las fechas a crear.'
            )

        row = supabase.table('classes').insert(rows_to_insert).execute()
        created = row.data or []

        month_name = [
            'enero','febrero','marzo','abril','mayo','junio',
            'julio','agosto','septiembre','octubre','noviembre','diciembre'
        ][month - 1]

        return {
            'message': (
                f'Se crearon {len(created)} clase(s) fija(s) para todos los {day_names[data.day_of_week]} '
                f'de {month_name} {year}.'
                + (
                    f' El profesor inicial fue asignado a {professor_assigned_count} de {len(created)} clase(s).'
                    if data.professor_id else ''
                )
            ),
            'created': created,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al crear la clase fija: {str(e)}')


# ── Listar clases ─────────────────────────────────────────────────────────────

def list_active_classes(user_id: str = None):
    try:
        from services.cancellations.classes_cancellation_service import cancelar_clases_sin_profesor
        cancelar_clases_sin_profesor()

        response = (
            supabase.table('classes')
            .select('*, rooms(id, name, capacity)')
            .eq('status', 'PROGRAMADA')
            .order('start_time', desc=False)
            .execute()
        )
        classes = response.data or []

        if user_id:
            # Reservas activas del usuario (para excluir clases ya reservadas)
            reservations_res = (
                supabase.table('reservations')
                .select('class_id')
                .eq('user_id', str(user_id))
                .neq('status', 'CANCELADA')
                .execute()
            )
            reserved_class_ids = {r['class_id'] for r in (reservations_res.data or [])}

            # Entradas del usuario en la waitlist (para saber si ya está anotado)
            waitlist_res = (
                supabase.table('waitlist')
                .select('class_id')
                .eq('user_id', str(user_id))
                .execute()
            )
            waitlisted_class_ids = {w['class_id'] for w in (waitlist_res.data or [])}

            # Excluir clases donde el usuario ya tiene reserva activa o ya está en waitlist
            classes = [c for c in classes if c['id'] not in reserved_class_ids and c['id'] not in waitlisted_class_ids]

            # Marcar cada clase con is_full para que el front decida qué botón mostrar
            for c in classes:
                c['is_full'] = c['current_capacity'] >= c['max_capacity']

        professor_ids = list({c['professor_id'] for c in classes if c.get('professor_id')})
        professors_by_id = {}
        if professor_ids:
            prof_res = (
                supabase.table('users')
                .select('id, name, surname')
                .in_('id', professor_ids)
                .execute()
            )
            professors_by_id = {p['id']: p for p in (prof_res.data or [])}

        for c in classes:
            prof = professors_by_id.get(c.get('professor_id'))
            c['professor_name'] = f"{prof['name']} {prof['surname']}" if prof else None

        return classes

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener las clases: {str(e)}')


# ── Listar salas ──────────────────────────────────────────────────────────────

def list_rooms(start_time: Optional[str] = None, end_time: Optional[str] = None):
    try:
        start, end = _parse_time_range(start_time, end_time)
        response = (
            supabase.table('rooms')
            .select('id, name, capacity, status')
            .eq('status', 'DISPONIBLE')
            .order('name', desc=False)
            .execute()
        )
        rooms = response.data or []
        if not start:
            return rooms

        classes_response = (
            supabase.table('classes')
            .select('room_id, start_time, end_time')
            .neq('status', 'CANCELADA')
            .execute()
        )
        occupied_room_ids = {
            c['room_id']
            for c in (classes_response.data or [])
            if c.get('room_id') and _overlaps(c['start_time'], c['end_time'], start, end)
        }
        return [room for room in rooms if room['id'] not in occupied_room_ids]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener las salas: {str(e)}')


# ── Listar profesores ─────────────────────────────────────────────────────────

def list_professors(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    exclude_class_id: Optional[str] = None
):
    try:
        start, end = _parse_time_range(start_time, end_time)
        response = (
            supabase.table('users')
            .select('id, name, surname, specialty, account_status')
            .eq('rol', 'PROFESOR')
            .eq('account_status', 'ACTIVA')
            .order('surname', desc=False)
            .execute()
        )
        professors = response.data or []
        if not start:
            return professors

        available = []
        for professor in professors:
            try:
                validate_professor_weekly_hours(professor['id'], start, end, exclude_class_id=exclude_class_id)
                validate_professor_schedule_availability(professor['id'], start, end, exclude_class_id=exclude_class_id)
                available.append(professor)
            except HTTPException:
                continue
        return available

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener los profesores: {str(e)}')


def list_available_professors_for_class(class_id: str):
    try:
        class_response = (
            supabase.table('classes')
            .select('id, start_time, end_time')
            .eq('id', class_id)
            .single()
            .execute()
        )
        if not class_response.data:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')

        clase = class_response.data
        return list_professors(clase['start_time'], clase['end_time'], exclude_class_id=class_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener profesores disponibles: {str(e)}')


# ── Asignar profesor ──────────────────────────────────────────────────────────

def assign_professor(class_id: str, data):
    try:
        class_response = (
            supabase.table('classes')
            .select('id, professor_id, activity_type, start_time, end_time, status, rooms(name)')
            .eq('id', class_id)
            .single()
            .execute()
        )
        if not class_response.data:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')

        clase = class_response.data
        if clase['status'] not in ('PROGRAMADA', 'EN CURSO'):
            raise HTTPException(status_code=400, detail='No se puede asignar un profesor a una clase que no está activa.')

        if clase['professor_id']:
            raise HTTPException(status_code=400, detail='La clase ya tiene un profesor asignado. Para cambiar el profesor, primero desasignalo.')

        class_start = datetime.fromisoformat(clase['start_time'])
        class_end = datetime.fromisoformat(clase['end_time'])
        validate_professor_exists(data.professor_id)
        validate_professor_weekly_hours(data.professor_id, class_start, class_end, exclude_class_id=class_id)
        validate_professor_schedule_availability(data.professor_id, class_start, class_end, exclude_class_id=class_id)

        updated_class = (
            supabase.table('classes')
            .update({'professor_id': str(data.professor_id)})
            .eq('id', class_id)
            .select()
            .execute()
        )

        affected_requests = (
            supabase.table('professor_requests')
            .select('id, professor_id, status, users(name, email)')
            .eq('class_id', class_id)
            .in_('status', ['PENDIENTE', 'ACEPTADA'])
            .neq('professor_id', str(data.professor_id))
            .execute()
        ).data or []

        reject_reason = 'El administrador asignó directamente a otro profesor.'

        supabase.table('professor_requests').update({
            'status': 'RECHAZADA',
            'reject_reason': reject_reason
        }).eq('class_id', class_id).eq('status', 'PENDIENTE').execute()

        supabase.table('professor_requests').update({
            'status': 'RECHAZADA',
            'reject_reason': 'El administrador reasignó la clase a otro profesor.'
        }).eq('class_id', class_id).eq('status', 'ACEPTADA').neq('professor_id', str(data.professor_id)).execute()

        class_desc = _build_class_desc(clase)
        for req in affected_requests:
            professor = req.get('users') or {}
            req_reason = (
                reject_reason if req['status'] == 'PENDIENTE'
                else 'El administrador reasignó la clase a otro profesor.'
            )
            try:
                create_notification(
                    req['professor_id'],
                    'Solicitud de clase rechazada',
                    f'Tu solicitud para dictar la clase {class_desc} fue rechazada. Motivo: {req_reason}'
                )
                if professor.get('email'):
                    send_professor_request_rejected(
                        professor['email'], professor.get('name', 'profesor/a'), class_desc, req_reason
                    )
            except Exception:
                # No interrumpir la asignación si falla el envío de una notificación
                pass

        return {'message': 'Se asignó el profesor correctamente.', 'data': updated_class.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al asignar el profesor: {str(e)}')


# ── Cancelar clase ────────────────────────────────────────────────────────────

def cancel_class(class_id: str):
    try:
        class_response = (
            supabase.table('classes')
            .select('id, status')
            .eq('id', class_id)
            .single()
            .execute()
        )
        if not class_response.data:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')

        clase = class_response.data
        if clase['status'] == 'CANCELADA':
            raise HTTPException(status_code=400, detail='La clase ya se encuentra cancelada.')

        updated_class = (
            supabase.table('classes')
            .update({'status': 'CANCELADA'})
            .eq('id', class_id)
            .select('id, status')
            .execute()
        )
        if not (updated_class.data or []):
            raise HTTPException(status_code=500, detail='No se pudo cancelar la clase. Intente nuevamente.')

        # Limpiar waitlist de la clase cancelada
        supabase.table('waitlist').delete().eq('class_id', class_id).execute()

        return {'message': 'Clase cancelada exitosamente', 'data': updated_class.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la clase: {str(e)}')


# ── Actualizar cupo ───────────────────────────────────────────────────────────

def update_capacity(class_id: str, new_capacity: int, admin_user_id: str = None):
    try:
        class_response = (
            supabase.table('classes')
            .select('id, max_capacity, current_capacity, room_id, status, rooms(capacity)')
            .eq('id', class_id)
            .single()
            .execute()
        )
        if not class_response.data:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')

        clase = class_response.data
        if clase['status'] not in ('PROGRAMADA', 'EN CURSO'):
            raise HTTPException(status_code=400, detail='Solo se puede modificar el cupo de clases activas.')

        room_capacity = clase['rooms']['capacity']
        if new_capacity > room_capacity:
            raise HTTPException(status_code=400, detail='El cupo ingresado supera la capacidad máxima de la sala.')

        reservations_response = (
            supabase.table('reservations')
            .select('id', count='exact')
            .eq('class_id', class_id)
            .eq('status', 'CONFIRMADA')
            .execute()
        )
        current_inscribed = reservations_response.count if reservations_response.count is not None else 0

        if new_capacity < current_inscribed:
            from services.cancellations.classes_cancellation_service import cancelar_clase
            cancelar_clase(
                class_id,
                cancel_reason='Cancelación automática: el nuevo cupo es menor a los inscriptos.',
                user_id=admin_user_id
            )
            return {'message': 'El nuevo cupo es menor a los inscriptos. La clase ha sido cancelada y se procesaron los reembolsos.'}

        updated_class = (
            supabase.table('classes')
            .update({'max_capacity': new_capacity})
            .eq('id', class_id)
            .select()
            .execute()
        )
        return {'message': 'Cupo de clase actualizado exitosamente.', 'data': updated_class.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al modificar el cupo de la clase: {str(e)}')


# ── Solicitudes de profesores ─────────────────────────────────────────────────

def create_professor_request(class_id: str, professor_id: str):
    try:
        class_response = supabase.table('classes').select('id, professor_id, start_time, end_time, status').eq('id', class_id).single().execute()
        if not class_response.data:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')
        if class_response.data['status'] not in ('PROGRAMADA', 'EN CURSO'):
            raise HTTPException(status_code=400, detail='No se puede solicitar una clase que no esta activa.')
        if class_response.data['professor_id'] is not None:
            raise HTTPException(status_code=400, detail='La clase ya tiene un profesor asignado.')

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

        professors_response = supabase.table('users').select('id, name, surname, specialty').in_('id', professor_ids).execute()
        professors_by_id = {p['id']: p for p in (professors_response.data or [])}

        classes_response = supabase.table('classes').select('id, type, activity_type, start_time, end_time, professor_id, room_id').in_('id', class_ids).execute()
        classes = classes_response.data or []
        room_ids = list({c['room_id'] for c in classes if c.get('room_id')})
        rooms_by_id = {}
        if room_ids:
            rooms_response = supabase.table('rooms').select('id, name').in_('id', room_ids).execute()
            rooms_by_id = {room['id']: room for room in (rooms_response.data or [])}

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


def _format_class_datetime_ar(start_time_iso: str) -> str:
    dt = datetime.fromisoformat(start_time_iso)
    dt_ar = _to_utc(dt).astimezone(TZ_AR)
    dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    return f"{dias[dt_ar.weekday()]} {dt_ar.strftime('%d/%m/%Y')} a las {dt_ar.strftime('%H:%M')}"


def _build_class_desc(clase: dict) -> str:
    activity = clase.get('activity_type', '') or ''
    room = (clase.get('rooms') or {}).get('name', '') if clase.get('rooms') else ''
    when = _format_class_datetime_ar(clase['start_time']) if clase.get('start_time') else ''
    return ' '.join(filter(None, [activity, f'en {room}' if room else '', f'el {when}' if when else ''])).strip()


def evaluate_professor_request(class_id: str, request_id: str, data):
    try:
        req_response = (
            supabase.table('professor_requests')
            .select('*, classes(start_time, end_time, status, professor_id, activity_type, rooms(name)), users(name, email)')
            .eq('id', request_id)
            .single()
            .execute()
        )
        if not req_response.data:
            raise HTTPException(status_code=404, detail='Solicitud no encontrada.')

        request_obj = req_response.data
        if request_obj['class_id'] != class_id:
            raise HTTPException(status_code=400, detail='La solicitud no corresponde a esta clase.')
        if request_obj['status'] != 'PENDIENTE':
            raise HTTPException(status_code=400, detail='La solicitud ya fue evaluada.')

        professor = request_obj.get('users') or {}
        clase = request_obj.get('classes') or {}
        class_desc = _build_class_desc(clase)

        if data.status == 'RECHAZADA':
            if not data.reason or not data.reason.strip():
                raise HTTPException(status_code=400, detail='El rechazo debe incluir un motivo obligatorio')
            updated = supabase.table('professor_requests').update({'status': 'RECHAZADA', 'reject_reason': data.reason}).eq('id', request_id).select().execute()

            if professor.get('email'):
                send_professor_request_rejected(professor['email'], professor.get('name', 'profesor/a'), class_desc, data.reason)
            create_notification(
                request_obj['professor_id'],
                'Solicitud de clase rechazada',
                f'Tu solicitud para dictar la clase {class_desc} fue rechazada. Motivo: {data.reason}'
            )

            return {'message': 'Solicitud rechazada correctamente con motivo', 'data': updated.data[0]}

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

        supabase.table('classes').update({'professor_id': request_obj['professor_id']}).eq('id', class_id).execute()
        updated = supabase.table('professor_requests').update({'status': 'ACEPTADA'}).eq('id', request_id).execute()

        other_pending = (
            supabase.table('professor_requests')
            .select('*, classes(start_time, end_time, status, professor_id, activity_type, rooms(name)), users(name, email)')
            .eq('class_id', class_id)
            .eq('status', 'PENDIENTE')
            .neq('id', request_id)
            .execute()
        )

        supabase.table('professor_requests').update({
            'status': 'RECHAZADA',
            'reject_reason': 'Otra solicitud fue aceptada para esta clase.'
        }).eq('class_id', class_id).eq('status', 'PENDIENTE').neq('id', request_id).execute()

        if professor.get('email'):
            send_professor_request_accepted(professor['email'], professor.get('name', 'profesor/a'), class_desc)
        create_notification(
            request_obj['professor_id'],
            'Solicitud de clase aceptada',
            f'Tu solicitud para dictar la clase {class_desc} fue aceptada.'
        )

        auto_reject_reason = 'Otra solicitud fue aceptada para esta clase.'
        for other_request in (other_pending.data or []):
            other_professor = other_request.get('users') or {}
            other_class_desc = _build_class_desc(other_request.get('classes') or {})
            if other_professor.get('email'):
                send_professor_request_rejected(other_professor['email'], other_professor.get('name', 'profesor/a'), other_class_desc, auto_reject_reason)
            create_notification(
                other_request['professor_id'],
                'Solicitud de clase rechazada',
                f'Tu solicitud para dictar la clase {other_class_desc} fue rechazada. Motivo: {auto_reject_reason}'
            )

        return {'message': 'Se aceptó la solicitud correctamente.', 'data': updated.data[0]}

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
