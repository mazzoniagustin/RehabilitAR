from fastapi import APIRouter, Depends, HTTPException, Query
from services import admin_service
from schemes.user_scheme import ActionReason, ActionReason, UserRegisterByStaff, AproveCertificate, RejectCertificate, EmployeeRegisterByAdmin
from utils.permissions import check_permission, is_adult

routerStaff = APIRouter(prefix="/staff", tags=["staff"])

@routerStaff.post('/register')
def register_by_staff(data: UserRegisterByStaff, user = Depends(check_permission(['ADMINISTRATIVO', 'RECEPCIONISTA']))):
    if not is_adult(data.birth_date):
        raise HTTPException(status_code=400, detail='El usuario debe ser mayor de edad.')
    return admin_service.register_user_by_staff(data)

@routerStaff.post('/approve_certificate')
def approve_certificate(data: AproveCertificate, user = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.approve_certificate(data)

@routerStaff.post('/reject_certificate')
def reject_certificate(data: RejectCertificate, user = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.reject_certificate(data)

@routerStaff.post('/register_employee')
def register_employee_by_staff(data: EmployeeRegisterByAdmin, user = Depends(check_permission(['ADMINISTRATIVO']))):
    if not is_adult(data.birth_date):
        raise HTTPException(status_code=400, detail='El empleado debe ser mayor de edad.')
    return admin_service.register_employee_by_admin(data)

@routerStaff.post('/approve_unblock_request/{user_id}')
def approve_unblock_request(user_id: str, user = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.approve_unblock_request(user_id, user['id'])

@routerStaff.post('/reject_unblock_request/{user_id}')
def reject_unblock_request(user_id: str, reason: ActionReason, user = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.reject_unblock_request(user_id, reason, user['id'])

@routerStaff.post('/block_user/{user_id}')
def block_user(user_id: str, reason: ActionReason, user = Depends(check_permission(['ADMINISTRATIVO']))):
    print(f"DEBUG: Intentando bloquear al usuario {user_id}")
    return admin_service.block_user(user_id, reason, user['id'])

@routerStaff.post('/unblock_user/{user_id}')
def unblock_user(user_id: str, user = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.unblock_user(user_id, user['id'])

@routerStaff.get('/pending-certificates')
def pending_certificates(user=Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.get_pending_certificates()

@routerStaff.get('/pending_unblocks')
def get_pending_unblocks(admin = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.get_pending_unblock_requests()

@routerStaff.get('/users')
def get_users(
    name: str = Query(None), 
    role: str = Query(None), 
    status: str = Query(None),
    user = Depends(check_permission(['ADMINISTRATIVO']))
):
    return admin_service.get_filtered_users(name, role, status)

@routerStaff.get('/certificates/{user_id}/view')
def view_certificates(user_id: str, user = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.view_certificate(user_id)
