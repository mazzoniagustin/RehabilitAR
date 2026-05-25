from fastapi import APIRouter, Depends
from services import classes_service
from schemes.class_scheme import ClassCreate, AssignProfessor
from utils.permissions import check_permission

router = APIRouter(
    prefix="/classes",
    tags=["Classes"]
)


@router.post('/')
def create_class(
    data: ClassCreate,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.create_class(data)


@router.get('/')
def list_classes(
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.list_active_classes()


@router.get('/rooms')
def list_rooms(
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.list_rooms()


@router.get('/professors')
def list_professors(
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.list_professors()


@router.patch('/{class_id}/assign-professor')
def assign_professor(
    class_id: str,
    data: AssignProfessor,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.assign_professor(class_id, data)
