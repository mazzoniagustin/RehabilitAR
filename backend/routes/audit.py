from fastapi import APIRouter, Depends
from services import audit_service
from utils.permissions import check_permission

routerAudit = APIRouter(prefix='/audit', tags=['Audit'])

@routerAudit.get('/global-stats')
def get_stats(
    year:  int = None,
    month: int = None,
    admin = Depends(check_permission(['ADMINISTRATIVO']))
):
    return audit_service.get_stats(year=year, month=month)
 
@routerAudit.get('/user-stats/{user_id}')
def get_user_audit_stats(
    user_id: str, 
    admin = Depends(check_permission(['ADMINISTRATIVO']))
):
    return audit_service.get_user_stats(user_id)