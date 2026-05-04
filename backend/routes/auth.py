from fastapi import APIRouter
from schemes.user_scheme import UserRegister, UserLogin, UserRegisterByAdmin, UserUpdatePhysicalCertificate
from services.auth_service import AuthService
from services.admin_service import Admin

router = APIRouter(prefix="/auth", tags=["Authentication"])
routerAdmin = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/register")
async def register(data: UserRegister):
    return AuthService.register_user(data)

@router.post("/login")
async def login(data: UserLogin):
    return AuthService.login_user(data.email, data.password)

@routerAdmin.post('/register')
async def register_by_admin(data: UserRegisterByAdmin):
    return Admin.register_user_by_admin(data)

@routerAdmin.post('/enable_physical_certificate')
async def enable_physical_certificate(data: UserUpdatePhysicalCertificate):
    return Admin.enable_physical_certificate(data)