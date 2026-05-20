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

@routerUser.put('/me')
def update_my_profile(
    data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    update_dict = data.dict(exclude_unset=True)
    return user_service.update_user_info(current_user['id'], update_dict)


@routerUser.get('/public/{user_id}')
def get_public_profile(user_id: str, current_user: dict = Depends(get_current_user)):
    return user_service.show_user_public_info(user_id)

@routerUser.get('/public-search')
def public_search(
    name: str = Query(None),
    role: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    return user_service.search_users_public(name=name, role=role)

@routerUser.post('/request-unblock')
def request_unblock(
    data: ActionReason,
    current_user: dict = Depends(get_current_user)
):
    return user_service.request_unblock(current_user['id'], data)

@routerUser.get('/{user_id}')
def get_user_profile(
    user_id: str,
    current_user: dict = Depends(check_permission(['ADMINISTRATIVO']))
):
    
    return user_service.show_user_admin_info(user_id)