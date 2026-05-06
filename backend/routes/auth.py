from fastapi import APIRouter
from schemes.user_scheme import UserRegister, UserLogin, UserRegisterByStaff, UserUpdatePhysicalCertificate, EmployeeRegisterByAdmin
from services import auth_service, admin_service


#Toma las requests y retorna las responses / respuestas

router = APIRouter(prefix="/auth", tags=["Authentication"])
routerAdmin = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/register")
def register(data: UserRegister):
    return auth_service.register_user(data)

@router.post("/login")
def login(data: UserLogin):
    return auth_service.login_user(data.email, data.password)

@routerAdmin.post('/register')
def register_by_admin(data: UserRegisterByStaff):
    if not check_permission(data.staff_id, ['ADMINISTRATIVO', 'RECEPCIONISTA']):
        raise HTTPException(status_code=403, detail=f'Acceso denegado. Permisos insuficientes.')
    return admin_service.register_user_by_staff(data)

@routerAdmin.post('/approve_certificate')
def approve_certificate(data: UserUpdatePhysicalCertificate):
    if not check_permission(data.admin_id, ['ADMINISTRATIVO']):
        raise HTTPException(status_code=403, detail=f'Acceso denegado. Permisos insuficientes.')
    return admin_service.approve_certificate(data)

@routerAdmin.post('/reject_certificate')
def reject_certificate(data: UserUpdatePhysicalCertificate):
    if not check_permission(data.admin_id, ['ADMINISTRATIVO']):
        raise HTTPException(status_code=403, detail=f'Acceso denegado. Permisos insuficientes.')
    return admin_service.reject_certificate(data)

@routerAdmin.post('/register_employee')
def register_employee_by_admin(data: EmployeeRegisterByAdmin):
    if not check_permission(data.admin_id, ['ADMINISTRATIVO']):
        raise HTTPException(status_code=403, detail=f'Acceso denegado. Permisos insuficientes.')
    return admin_service.register_employee_by_admin(data)