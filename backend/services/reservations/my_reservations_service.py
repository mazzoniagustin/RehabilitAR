from database import supabase
from fastapi import HTTPException


def get_my_reservations(user_id: str):
    try:
        res = (
            supabase.table('reservations')
            .select('id, status, payment_status, class_id, classes(activity_type, start_time, type)')
            .eq('user_id', user_id)
            .neq('status', 'CANCELADA')
            .order('created_at', desc=True)
            .execute()
        )

        reservations = res.data or []

        result = []
        for r in reservations:
            clase = r.get('classes') or {}
            result.append({
                'id':             r['id'],
                'status':         r['status'],
                'payment_status': r['payment_status'],
                'class_id':       r['class_id'],
                'activity_type':  clase.get('activity_type'),
                'start_time':     clase.get('start_time'),
                'type':           clase.get('type'),
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener las reservas: {str(e)}')
