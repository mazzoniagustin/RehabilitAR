from database import supabase, supabase_admin
from fastapi import HTTPException
from services.cancellations.classes_cancellation_service import asegurar_clase_reservable_con_profesor
from services.reservations.overlap_validator import validate_user_has_no_overlapping_class
from services.notifications_service import create_notification
from utils.notifications import (
    send_waitlist_joined_email,
    send_waitlist_advanced_email,
    send_waitlist_threshold_admin_email,
)
from utils.class_desc import build_class_desc

WAITLIST_THRESHOLD_EVENT_TYPE = 'WAITLIST_OVER_10'
WAITLIST_THRESHOLD = 10


def _client():
    return supabase_admin or supabase


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

        clase_response = supabase.table('classes').select('id, type, status, professor_id, current_capacity, max_capacity, start_time, end_time, activity_type, rooms(name)').eq('id', class_id).single().execute()
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

        user_response = supabase.table('users').select('id, rol, account_status, email, name').eq('id', user_id).single().execute()
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
            return _agregar_waitlist_individual(user_id, class_id, clase, user)
        if class_type == 'FIJA':
            prioridad = 'ABONADO' if user['rol'] == 'ABONADO' else 'NO_ABONADO'
            return _agregar_waitlist_fija(user_id, class_id, prioridad, clase, user)

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

        clase = (
            supabase.table('classes')
            .select('type')
            .eq('id', class_id)
            .single()
            .execute()
        ).data
        class_type = clase['type'] if clase else 'FIJA'

        posiciones_previas = _visible_positions_map(class_id, class_type)

        supabase.table('waitlist').delete().eq('id', entrada_response.data[0]['id']).execute()
        _reordenar_waitlist(class_id)
        _notificar_avance_waitlist(class_id, class_type, posiciones_previas)

        return {'message': 'Saliste de la lista de espera correctamente.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al salir de la lista de espera: {str(e)}')


def _agregar_waitlist_individual(user_id: str, class_id: str, clase: dict = None, user: dict = None):
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

    _notificar_union_waitlist(user_id, clase, nueva_posicion, user)
    _notificar_admin_waitlist_si_supera_limite(class_id, clase)

    return {
        'message': f'Te uniste a la lista de espera. Posición: {nueva_posicion}.',
        'position': nueva_posicion
    }


def _agregar_waitlist_fija(user_id: str, class_id: str, prioridad: str, clase: dict = None, user: dict = None):
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

    _notificar_union_waitlist(user_id, clase, posicion_visible, user)
    _notificar_admin_waitlist_si_supera_limite(class_id, clase)

    return {
        'message': f'Te uniste a la lista de espera. Posición: {posicion_visible}.',
        'posicion': posicion_visible
    }


def _waitlist_threshold_event_key(class_id: str, admin_id: str) -> str:
    return f'{WAITLIST_THRESHOLD_EVENT_TYPE}:{class_id}:{admin_id}'


def _claim_waitlist_threshold_delivery(class_id: str, admin_id: str) -> bool:
    event_key = _waitlist_threshold_event_key(class_id, admin_id)
    existing = (
        _client().table('notification_delivery_log')
        .select('id')
        .eq('event_key', event_key)
        .limit(1)
        .execute()
    )
    if existing.data:
        return False

    _client().table('notification_delivery_log').insert({
        'event_key': event_key,
        'event_type': WAITLIST_THRESHOLD_EVENT_TYPE,
        'user_id': admin_id,
        'class_id': class_id,
    }).execute()
    return True


def _crear_notificacion_admin(admin_id: str, title: str, message: str):
    admin = (
        _client().table('users')
        .select('notifications_enabled')
        .eq('id', admin_id)
        .single()
        .execute()
    )
    if not admin.data or not admin.data.get('notifications_enabled', True):
        return

    _client().table('notifications').insert({
        'user_id': admin_id,
        'title': title,
        'message': message,
    }).execute()


def _notificar_admin_waitlist_si_supera_limite(class_id: str, clase: dict = None):
    try:
        count_response = (
            supabase.table('waitlist')
            .select('id', count='exact')
            .eq('class_id', class_id)
            .execute()
        )
        total_waitlist = count_response.count if count_response.count is not None else 0
        if total_waitlist <= WAITLIST_THRESHOLD:
            return

        admins = (
            _client().table('users')
            .select('id, email, name')
            .eq('rol', 'ADMINISTRATIVO')
            .eq('account_status', 'ACTIVA')
            .execute()
        ).data or []
        if not admins:
            return

        desc = build_class_desc(clase) if clase else 'la clase'

        for admin in admins:
            admin_id = str(admin['id'])
            if not _claim_waitlist_threshold_delivery(str(class_id), admin_id):
                continue

            try:
                _crear_notificacion_admin(
                    admin_id,
                    'Lista de espera con alta demanda',
                    f'La lista de espera de la clase de {desc} superó los 10 miembros. '
                    f'Cantidad actual: {total_waitlist}.'
                )
            except Exception:
                pass

            if admin.get('email'):
                send_waitlist_threshold_admin_email(
                    admin['email'],
                    admin.get('name', 'administrativo/a'),
                    desc,
                    total_waitlist,
                )
    except Exception:
        # No interrumpir la reserva/lista de espera por un fallo de notificación.
        pass


def _notificar_union_waitlist(user_id: str, clase: dict, posicion: int, user: dict = None):
    try:
        desc = build_class_desc(clase) if clase else 'la clase'
        create_notification(
            user_id,
            'Te uniste a la lista de espera',
            f'Te uniste a la lista de espera de la clase de {desc}. '
            f'Tu posición actual es {posicion}. '
            'Te avisaremos si entrás a la clase por una vacante o si avanzás de posición.'
        )

        if user is None:
            user = (
                supabase.table('users')
                .select('email, name')
                .eq('id', user_id)
                .single()
                .execute()
            ).data

        if user and user.get('email'):
            send_waitlist_joined_email(user['email'], user.get('name', 'usuario/a'), desc, posicion)
    except Exception:
        # No interrumpir el flujo principal si la notificación falla
        pass


def _visible_positions_map(class_id: str, class_type: str) -> dict:
    """
    Calcula {waitlist_id: (user_id, posicion_visible)} para todos los que
    siguen en la lista de espera de la clase, respetando el mismo criterio
    usado al unirse: FIFO puro para INDIVIDUAL, prioridad ABONADO > NO_ABONADO
    (FIFO dentro de cada grupo) para FIJA.
    """
    if class_type == 'INDIVIDUAL':
        entradas = (
            supabase.table('waitlist')
            .select('id, user_id')
            .eq('class_id', class_id)
            .order('joined_at', desc=False)
            .execute()
        ).data or []
        return {fila['id']: (fila['user_id'], i) for i, fila in enumerate(entradas, start=1)}

    posiciones = {}
    contador = 0
    for prioridad in ['ABONADO', 'NO_ABONADO']:
        grupo = (
            supabase.table('waitlist')
            .select('id, user_id')
            .eq('class_id', class_id)
            .eq('priority', prioridad)
            .order('priority_order', desc=False)
            .execute()
        ).data or []
        for fila in grupo:
            contador += 1
            posiciones[fila['id']] = (fila['user_id'], contador)
    return posiciones


def _notificar_avance_waitlist(class_id: str, class_type: str, posiciones_previas: dict):
    """
    Compara las posiciones previas de la lista de espera con las actuales
    (luego de una salida o una promoción) y notifica a quienes hayan
    mejorado su lugar en la cola.
    """
    try:
        clase = (
            supabase.table('classes')
            .select('activity_type, start_time, rooms(name)')
            .eq('id', class_id)
            .single()
            .execute()
        ).data
        desc = build_class_desc(clase) if clase else 'la clase'

        posiciones_actuales = _visible_positions_map(class_id, class_type)
        for waitlist_id, (user_id, nueva_posicion) in posiciones_actuales.items():
            anterior = posiciones_previas.get(waitlist_id)
            if anterior and anterior[1] > nueva_posicion:
                create_notification(
                    user_id,
                    'Avanzaste en la lista de espera',
                    f'Avanzaste de posición en la lista de espera de la clase de {desc}. '
                    f'Tu posición actual es {nueva_posicion}.'
                )
                try:
                    user = (
                        supabase.table('users')
                        .select('email, name')
                        .eq('id', user_id)
                        .single()
                        .execute()
                    ).data
                    if user and user.get('email'):
                        send_waitlist_advanced_email(user['email'], user.get('name', 'usuario/a'), desc, nueva_posicion)
                except Exception:
                    # No interrumpir el flujo principal si el email falla
                    pass
    except Exception:
        # No interrumpir el flujo principal si la notificación falla
        pass


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
