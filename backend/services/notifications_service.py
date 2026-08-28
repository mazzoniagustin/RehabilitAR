from fastapi import HTTPException
from database import supabase


def get_notifications(user_id: str):
    try:
        user = supabase.table('users') \
            .select('notifications_enabled') \
            .eq('id', user_id) \
            .single() \
            .execute()

        result = supabase.table('notifications') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(20) \
            .execute()

        notifications = result.data or []
        unread_count = sum(1 for n in notifications if not n['is_read'])

        return {
            'notifications': notifications,
            'unread_count': unread_count,
            'notifications_enabled': user.data.get('notifications_enabled', True)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def mark_as_read(notification_id: str, user_id: str):
    try:
        result = supabase.table('notifications') \
            .update({'is_read': True}) \
            .eq('id', notification_id) \
            .eq('user_id', user_id) \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail='Notificación no encontrada.')

        return {'mensaje': 'Notificación marcada como leída.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def mark_all_as_read(user_id: str):
    try:
        supabase.table('notifications') \
            .update({'is_read': True}) \
            .eq('user_id', user_id) \
            .eq('is_read', False) \
            .execute()

        return {'mensaje': 'Todas las notificaciones marcadas como leídas.'}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def create_notification(user_id: str, title: str, message: str):
    try:
        user = supabase.table('users') \
            .select('notifications_enabled') \
            .eq('id', user_id) \
            .single() \
            .execute()

        if not user.data or not user.data.get('notifications_enabled', True):
            return

        supabase.table('notifications').insert({
            'user_id': user_id,
            'title': title,
            'message': message
        }).execute()

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def toggle_notifications(user_id: str):
    try:
        current = supabase.table('users') \
            .select('notifications_enabled') \
            .eq('id', user_id) \
            .single() \
            .execute()

        if not current.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')

        new_value = not current.data['notifications_enabled']

        supabase.table('users') \
            .update({'notifications_enabled': new_value}) \
            .eq('id', user_id) \
            .execute()

        return {'notifications_enabled': new_value}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))