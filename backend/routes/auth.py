from fastapi import APIRouter, Depends
from services import auth_service, user_service
from schemes.user_scheme import RecoverPassword, UserRegister, UserLogin, ChangePassword
from utils.permissions import get_current_user


#Toma las requests y retorna las responses / respuestas

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
def register(data: UserRegister):
    return auth_service.register_user(data)

@router.post("/login")
def login(data: UserLogin):
    return auth_service.login_user(data.email, data.password)


@router.post('/change_password')
def change_password(
    data: ChangePassword,
    current_user: dict = Depends(get_current_user)
):
    return user_service.change_password(current_user['id'], data)

@router.post('/recover-password')
def recover_password(data: RecoverPassword):
    return auth_service.recover_password(data.email)

@router.post('/logout')
def log_out():
    return auth_service.log_out()
