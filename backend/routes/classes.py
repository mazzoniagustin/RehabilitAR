from fastapi import APIRouter, Depends
from services import classes_service
from schemes.class_scheme import ClassCreate, AssignProfessor, UpdateCapacity, EvaluateRequest
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


@router.get('/available-for-professor')
def list_classes_for_professor(
    user=Depends(check_permission(['PROFESOR']))
):
    return classes_service.list_active_classes()


@router.get('/requests/pending')
def list_pending_professor_requests(
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.list_pending_professor_requests()


@router.get('/requests/me')
def list_my_professor_requests(
    user=Depends(check_permission(['PROFESOR']))
):
    return classes_service.list_professor_requests(user['id'])


@router.patch('/{class_id}/assign-professor')
def assign_professor(
    class_id: str,
    data: AssignProfessor,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.assign_professor(class_id, data)

@router.patch('/{class_id}/cancel')
def cancel_class(
    class_id: str,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.cancel_class(class_id)

@router.patch('/{class_id}/capacity')
def update_capacity(
    class_id: str,
    data: UpdateCapacity,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.update_capacity(class_id, data.new_capacity)

@router.post('/{class_id}/request')
def create_professor_request(
    class_id: str,
    user=Depends(check_permission(['PROFESOR']))
):
    return classes_service.create_professor_request(class_id, user['id'])

@router.patch('/{class_id}/request/{request_id}')
def evaluate_professor_request(
    class_id: str,
    request_id: str,
    data: EvaluateRequest,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.evaluate_professor_request(class_id, request_id, data)

@router.get('/{class_id}/students')
def list_class_students(
    class_id: str,
    user=Depends(check_permission(['ADMINISTRATIVO', 'PROFESOR']))
):
    return classes_service.list_class_students(class_id)
