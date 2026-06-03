from database import supabase
from fastapi import HTTPException
from services.cancellations.classes_cancellation_service import asegurar_clase_reservable_con_profesor
from services.reservations.overlap_validator import validate_user_has_no_overlapping_class


def unirse_a_waitlist(user_id: str, class_id: str):
    """
    Permite a cualquier usuario unirse a la lista de espera de una clase llena.
    - Clase INDIVIDUAL: FIFO puro (sin prioridades; priority se guarda como 'NO_ABONADO'
      por el NOT NULL del schema, pero el orden real se determina por joined_at).
    - Clase FIJA: FIFO con prioridad (ABONADO antes que NO_ABONADO).
    """
    try:
        user_id = str(user_id)
        class_id = str(class_id)

        clase_response = supabase.table('classes').select('id, type, status, professor_id, current_capacity, max_capacity, start_time, end_time').eq('id', class_id).single().execute()
        if not clase_response.data:
            raise HTTPException(status_code=404, detail='Clase no encontrada.')
        clase = clase_response.data

        if clase['status'] != 'PROGRAMADA':
            raise HTTPException(status_code=400, detail='No se puede unirse a la lista de espera de una clase que no está programada.')

        asegurar_clase_reservable_con_profesor(class_id, clase)

        if clase['current_capacity'] < clase['max_capacity']:
            raise HTTPException(
                status_code=400,
                detail='La clase tiene lugares disponibles. Podés reservarla directamente.'
            )

        user_response = supabase.table('users').select('id, rol, account_status').eq('id', user_id).single().execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        user = user_response.data

        if user['account_status'] != 'ACTIVA':
            raise HTTPException(status_code=403, detail='No estás habilitado para unirte a la lista de espera.')

        # Verificar que no tenga ya una reserva activa
        existing_reservation = (
            supabase.table('reservations')
            .select('id')
            .eq('user_id', user_id)
            .eq('class_id', class_id)
            .neq('status', 'CANCELADA')
            .execute()
        )
        if existing_reservation.data:
            raise HTTPException(status_code=400, detail='Ya tenés una reserva activa para esta clase.')

        # Verificar que no esté ya en la waitlist
        ya_en_lista = (
            supabase.table('waitlist')
            .select('id')
            .eq('user_id', user_id)
            .eq('class_id', class_id)
            .execute()
        )
        if ya_en_lista.data:
            raise HTTPException(status_code=400, detail='Ya estás en la lista de espera para esta clase.')

        validate_user_has_no_overlapping_class(user_id, class_id, clase)

        class_type = clase['type']

        if class_type == 'INDIVIDUAL':
            return _agregar_waitlist_individual(user_id, class_id)
        if class_type == 'FIJA':
            prioridad = 'ABONADO' if user['rol'] == 'ABONADO' else 'NO_ABONADO'
            return _agregar_waitlist_fija(user_id, class_id, prioridad)

        raise HTTPException(status_code=400, detail='Tipo de clase inválido para lista de espera.')

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al unirse a la lista de espera: {str(e)}')


def salir_de_waitlist(user_id: str, class_id: str):
    try:
        user_id = str(user_id)
        class_id = str(class_id)

        entrada_response = (
            supabase.table('waitlist')
            .select('id')
            .eq('user_id', user_id)
            .eq('class_id', class_id)
            .limit(1)
            .execute()
        )
        if not entrada_response.data:
            raise HTTPException(status_code=404, detail='No estás en la lista de espera para esta clase.')

        supabase.table('waitlist').delete().eq('id', entrada_response.data[0]['id']).execute()
        _reordenar_waitlist(class_id)

        return {'message': 'Saliste de la lista de espera correctamente.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al salir de la lista de espera: {str(e)}')


def _agregar_waitlist_individual(user_id: str, class_id: str):
    waitlist_response = (
        supabase.table('waitlist')
        .select('position, priority_order')
        .eq('class_id', class_id)
        .order('position', desc=True)
        .limit(1)
        .execute()
    )
    entradas = waitlist_response.data or []
    nueva_posicion = (entradas[0]['position'] + 1) if entradas else 1
    nuevo_priority_order = (entradas[0]['priority_order'] + 1) if entradas else 1

    supabase.table('waitlist').insert({
        'user_id': user_id,
        'class_id': class_id,
        'position': nueva_posicion,
        'priority': 'NO_ABONADO',
        'priority_order': nuevo_priority_order,
    }).execute()

    return {
        'message': f'Te uniste a la lista de espera. Posición: {nueva_posicion}.',
        'position': nueva_posicion
    }


def _agregar_waitlist_fija(user_id: str, class_id: str, prioridad: str):
    """
    FIFO con prioridad: ABONADO tiene prioridad sobre NO_ABONADO.
    Dentro del mismo nivel de prioridad, se respeta el orden de llegada.
    """
    waitlist_response = (
        supabase.table('waitlist')
        .select('position')
        .eq('class_id', class_id)
        .order('position', desc=True)
        .limit(1)
        .execute()
    )
    entradas = waitlist_response.data or []
    nueva_posicion = (entradas[0]['position'] + 1) if entradas else 1

    nivel_response = (
        supabase.table('waitlist')
        .select('priority_order')
        .eq('class_id', class_id)
        .eq('priority', prioridad)
        .order('priority_order', desc=True)
        .limit(1)
        .execute()
    )
    nivel_entradas = nivel_response.data or []
    nuevo_priority_order = (nivel_entradas[0]['priority_order'] + 1) if nivel_entradas else 1

    abonados_response = (
        supabase.table('waitlist')
        .select('id', count='exact')
        .eq('class_id', class_id)
        .eq('priority', 'ABONADO')
        .execute()
    )
    total_abonados = abonados_response.count if abonados_response.count is not None else 0
    posicion_visible = nuevo_priority_order if prioridad == 'ABONADO' else total_abonados + nuevo_priority_order

    supabase.table('waitlist').insert({
        'user_id': user_id,
        'class_id': class_id,
        'position': nueva_posicion,
        'priority': prioridad,
        'priority_order': nuevo_priority_order,
    }).execute()

    return {
        'message': f'Te uniste a la lista de espera. Posición: {posicion_visible}.',
        'posicion': posicion_visible
    }


def _reordenar_waitlist(class_id: str):
    restantes = (
        supabase.table('waitlist')
        .select('id, priority')
        .eq('class_id', class_id)
        .order('position', desc=False)
        .execute()
    ).data or []

    for i, fila in enumerate(restantes, start=1):
        supabase.table('waitlist').update({'position': i}).eq('id', fila['id']).execute()

    for prioridad in ['ABONADO', 'NO_ABONADO']:
        grupo = (
            supabase.table('waitlist')
            .select('id')
            .eq('class_id', class_id)
            .eq('priority', prioridad)
            .order('position', desc=False)
            .execute()
        ).data or []
        for i, fila in enumerate(grupo, start=1):
            supabase.table('waitlist').update({'priority_order': i}).eq('id', fila['id']).execute()
