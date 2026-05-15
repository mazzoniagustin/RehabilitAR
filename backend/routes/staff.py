from fastapi import APIRouter, Depends
from services import admin_service
from schemes.user_scheme import ActionReason, ActionReason, UserRegisterByStaff, AproveCertificate, RejectCertificate, EmployeeRegisterByAdmin
from utils.permissions import check_permission

routerStaff = APIRouter(prefix="/staff", tags=["staff"])

@routerStaff.post('/register')
def register_by_staff(data: UserRegisterByStaff, user = Depends(check_permission(['ADMINISTRATIVO', 'RECEPCIONISTA']))):
    return admin_service.register_user_by_staff(data)

@routerStaff.post('/approve_certificate')
def approve_certificate(data: AproveCertificate, user = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.approve_certificate(data)

@routerStaff.post('/reject_certificate')
def reject_certificate(data: RejectCertificate, reason: ActionReason, user = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.reject_certificate(data, reason)

@routerStaff.post('/register_employee')
def register_employee_by_staff(data: EmployeeRegisterByAdmin, user = Depends(check_permission(['ADMINISTRATIVO']))):
    return admin_service.register_employee_by_admin(data)

