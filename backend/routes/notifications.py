from fastapi import APIRouter, Depends
from services import notifications_service
from utils.permissions import get_current_user
ALL_ROLES = ['ADMINISTRATIVO', 'RECEPCIONISTA', 'PROFESOR', 'ABONADO', 'NO_ABONADO']
router = APIRouter(prefix='/notifications', tags=['notifications'])


@router.get('/')
def get_notifications(user=Depends(get_current_user)):
    return notifications_service.get_notifications(user['id'])


@router.patch('/read-all')
def mark_all_as_read(user=Depends(get_current_user)):
    return notifications_service.mark_all_as_read(user['id'])


@router.patch('/toggle')
def toggle_notifications(user=Depends(get_current_user)):
    return notifications_service.toggle_notifications(user['id'])


@router.patch('/{notification_id}/read')
def mark_as_read(notification_id: str, user=Depends(get_current_user)):
    return notifications_service.mark_as_read(notification_id, user['id'])