from fastapi import APIRouter, Depends
from services import notifications_service
from services import attendance_reminder_service
from services import no_professor_notification_service
from utils.permissions import check_permission, get_current_user
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


@router.post('/reminders/attendance')
def send_attendance_reminders(user=Depends(check_permission(['ADMINISTRATIVO']))):
    return attendance_reminder_service.enviar_recordatorios_asistencia()


@router.post('/reminders/no-professor')
def send_no_professor_reminders(user=Depends(check_permission(['ADMINISTRATIVO']))):
    return no_professor_notification_service.avisar_profesores_clases_sin_profesor()
