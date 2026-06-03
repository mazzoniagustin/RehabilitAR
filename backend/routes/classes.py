from typing import Optional
from fastapi import APIRouter, Depends, Query
from services import classes_service
from services.cancellations import classes_cancellation_service
from schemes.class_scheme import (
    IndividualClassCreate,
    FijaClassCreate,
    AssignProfessor,
    UpdateCapacity,
    EvaluateRequest
)
from utils.permissions import check_permission

router = APIRouter(
    prefix="/classes",
    tags=["Classes"]
)


# ── Creación ──────────────────────────────────────────────────────────────────

@router.post('/individual')
def create_individual_class(
    data: IndividualClassCreate,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.create_individual_class(data)


@router.post('/fija')
def create_fija_class(
    data: FijaClassCreate,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.create_fija_class(data)


# ── Listados ──────────────────────────────────────────────────────────────────

@router.get('/')
def list_classes(
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.list_active_classes()


@router.get('/rooms')
def list_rooms(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.list_rooms(start_time, end_time)


@router.get('/professors')
def list_professors(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    exclude_class_id: Optional[str] = Query(None),
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.list_professors(start_time, end_time, exclude_class_id)


@router.get('/available')
def list_classes_available(
    user=Depends(check_permission(['NO_ABONADO', 'ABONADO', 'RECEPCIONISTA']))
):
    return classes_service.list_active_classes(user_id=user['id'])


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


@router.get('/{class_id}/available-professors')
def list_available_professors_for_class(
    class_id: str,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.list_available_professors_for_class(class_id)


@router.get('/{class_id}/students')
def list_class_students(
    class_id: str,
    user=Depends(check_permission(['ADMINISTRATIVO', 'PROFESOR']))
):
    return classes_service.list_class_students(class_id)


# ── Acciones ──────────────────────────────────────────────────────────────────

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
    return classes_cancellation_service.cancelar_clase(
        class_id,
        cancel_reason='Cancelación manual desde el panel administrativo.',
        user_id=str(user['id'])
    )


@router.patch('/{class_id}/capacity')
def update_capacity(
    class_id: str,
    data: UpdateCapacity,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return classes_service.update_capacity(class_id, data.new_capacity, admin_user_id=str(user['id']))


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
