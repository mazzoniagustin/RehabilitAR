from fastapi import APIRouter
from schemes.user_scheme import UserRegister, UserLogin, UserRegisterByAdmin, UserUpdatePhysicalCertificate
from services import auth_service, admin_service

router = APIRouter(prefix="/auth", tags=["Authentication"])
routerAdmin = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/register")
def register(data: UserRegister):
    return auth_service.register_user(data)

@router.post("/login")
def login(data: UserLogin):
    return auth_service.login_user(data.email, data.password)

@routerAdmin.post('/register')
def register_by_admin(data: UserRegisterByAdmin):
    return admin_service.register_user_by_admin(data)

@routerAdmin.post('/approve_certificate')
def approve_certificate(data: UserUpdatePhysicalCertificate):
    return admin_service.approve_certificate(data)

@routerAdmin.post('/reject_certificate')
def reject_certificate(data: UserUpdatePhysicalCertificate):
    return admin_service.reject_certificate(data)