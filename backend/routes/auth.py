from fastapi import APIRouter, HTTPException
from schemes.user_scheme import UserRegister, UserLogin, UserRegisterByStaff, ApproveCertificate, RejectCertificate, EmployeeRegisterByAdmin, ChangePassword
from services import auth_service, admin_service
from utils.permissions import check_permission


#Toma las requests y retorna las responses / respuestas

router = APIRouter(prefix="/auth", tags=["Authentication"])
routerStaff = APIRouter(prefix="/staff", tags=["staff"])

@router.post("/register")
def register(data: UserRegister):
    return auth_service.register_user(data)

@router.post("/login")
def login(data: UserLogin):
    return auth_service.login_user(data.email, data.password)

@routerStaff.post('/register')
def register_by_staff(data: UserRegisterByStaff):
    if not check_permission(data.staff_id, ['ADMINISTRATIVO', 'RECEPCIONISTA']):
        raise HTTPException(status_code=403, detail=f'Acceso denegado. Permisos insuficientes.')
    return admin_service.register_user_by_staff(data)

@routerStaff.post('/approve_certificate')
def approve_certificate(data: ApproveCertificate):
    if not check_permission(data.admin_id, ['ADMINISTRATIVO']):
        raise HTTPException(status_code=403, detail=f'Acceso denegado. Permisos insuficientes.')
    return admin_service.approve_certificate(data)

@routerStaff.post('/reject_certificate')
def reject_certificate(data: RejectCertificate):
    if not check_permission(data.admin_id, ['ADMINISTRATIVO']):
        raise HTTPException(status_code=403, detail=f'Acceso denegado. Permisos insuficientes.')
    return admin_service.reject_certificate(data)

@routerStaff.post('/register_employee')
def register_employee_by_staff(data: EmployeeRegisterByAdmin):
    if not check_permission(data.admin_id, ['ADMINISTRATIVO']):
        raise HTTPException(status_code=403, detail=f'Acceso denegado. Permisos insuficientes.')
    return admin_service.register_employee_by_admin(data)

@router.post('/change_password')
def change_password(data: ChangePassword):
    return auth_service.change_password(data)

@router.post('/logout')
def log_out():
    return auth_service.log_out()