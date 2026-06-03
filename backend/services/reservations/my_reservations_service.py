from database import supabase
from fastapi import HTTPException


def get_my_reservations(user_id: str):
    try:
        from services.cancellations.classes_cancellation_service import (
            cancelar_clases_sin_profesor,
            sincronizar_reservas_de_clases_canceladas,
        )

        cancelar_clases_sin_profesor()
        sincronizar_reservas_de_clases_canceladas(user_id)

        res = (
            supabase.table('reservations')
            .select('id, status, payment_status, class_id, classes(activity_type, start_time, type, status)')
            .eq('user_id', user_id)
            .neq('status', 'CANCELADA')
            .order('created_at', desc=True)
            .execute()
        )

        reservations = res.data or []

        result = []
        for r in reservations:
            clase = r.get('classes') or {}
            if clase.get('status') == 'CANCELADA':
                continue
            result.append({
                'kind':           'RESERVATION',
                'id':             r['id'],
                'status':         r['status'],
                'payment_status': r['payment_status'],
                'class_id':       r['class_id'],
                'activity_type':  clase.get('activity_type'),
                'start_time':     clase.get('start_time'),
                'type':           clase.get('type'),
            })

        waitlist_res = (
            supabase.table('waitlist')
            .select('id, class_id, position, priority, priority_order, joined_at, classes(activity_type, start_time, type, status)')
            .eq('user_id', user_id)
            .order('joined_at', desc=True)
            .execute()
        )

        for w in (waitlist_res.data or []):
            clase = w.get('classes') or {}
            if clase.get('status') == 'CANCELADA':
                continue
            result.append({
                'kind':              'WAITLIST',
                'id':                w['id'],
                'status':            'EN_ESPERA',
                'payment_status':    None,
                'class_id':          w['class_id'],
                'activity_type':     clase.get('activity_type'),
                'start_time':        clase.get('start_time'),
                'type':              clase.get('type'),
                'waitlist_position': _visible_waitlist_position(w, clase.get('type')),
                'priority':          w.get('priority'),
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener las reservas: {str(e)}')


def _visible_waitlist_position(entry: dict, class_type: str):
    if class_type != 'FIJA':
        return entry.get('position')

    if entry.get('priority') == 'ABONADO':
        return entry.get('priority_order')

    abonados_response = (
        supabase.table('waitlist')
        .select('id', count='exact')
        .eq('class_id', entry['class_id'])
        .eq('priority', 'ABONADO')
        .execute()
    )
    total_abonados = abonados_response.count if abonados_response.count is not None else 0
    return total_abonados + (entry.get('priority_order') or 0)
