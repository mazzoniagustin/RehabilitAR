from fastapi import APIRouter, Depends, HTTPException
from services import auth_service, user_service
from schemes.user_scheme import RecoverPassword, ResetPassword, UserRegister, UserLogin, ChangePassword
from utils.permissions import get_current_user, is_adult


#Toma las requests y retorna las responses / respuestas

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
def register(data: UserRegister):
    if not is_adult(data.birth_date):
        raise HTTPException(status_code=400, detail='El usuario debe ser mayor de edad.')
    return auth_service.register_user(data)

@router.post("/login")
def login(data: UserLogin):
    return auth_service.login_user(data.email, data.password)


@router.post('/recover-password')
def recover_password(data: RecoverPassword):
    return auth_service.recover_password(data.email)

@router.post('/reset-password')
def reset_password(data: ResetPassword):
    return auth_service.reset_password(data.token, data.password)

@router.post('/logout')
def log_out():
    return auth_service.log_out()
