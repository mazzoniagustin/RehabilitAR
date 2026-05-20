from fastapi import APIRouter, Depends, UploadFile, File, Query
from services import user_service, admin_service
from schemes.user_scheme import ActionReason, ChangePassword, UserUpdate
from utils.permissions import get_current_user, check_permission

routerUser = APIRouter(prefix='/users', tags=['Usuarios'])


@routerUser.get('/me')
def get_my_profile(current_user: dict = Depends(get_current_user)):
    return user_service.show_user_info(current_user['id'])


@routerUser.post('/me/change-password')
def change_password(
    data: ChangePassword,
    current_user: dict = Depends(get_current_user)
):
    return user_service.change_password(data)

@routerUser.post("/upload-certificate")
def upload_certificate(
    file: UploadFile = File(...),
    user = Depends(get_current_user)
):
    return user_service.upload_certificate(user["id"], file)

