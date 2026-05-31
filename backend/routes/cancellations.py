from fastapi import APIRouter, Depends
from services.cancellations import classes_cancellation_service as class_cancellation
from services.cancellations import reservation_cancellation_service as reservation_cancellation
from services.cancellations import subscription_cancellation_service as subscription_cancellation
from schemes.cancellations_scheme import CancelClass, CancelReservation, CancelSubscription
from utils.permissions import check_permission

router = APIRouter(
    prefix="/cancellations",
    tags=["Cancellations"]
)

@router.post('/class')
def cancelar_clase(
    data: CancelClass,
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return class_cancellation.cancelar_clase(data.class_id, data.cancel_reason, user_id=str(user['id']))


@router.post('/classes/automatic/no-professor')
def cancelar_clases_sin_profesor(
    user=Depends(check_permission(['ADMINISTRATIVO']))
):
    return class_cancellation.cancelar_clases_sin_profesor()


@router.post('/reservation')
def cancelar_reserva(
    data: CancelReservation,
    user=Depends(check_permission(['ABONADO', 'NO_ABONADO']))
):
    return reservation_cancellation.cancelar_reserva(data.reservation_id, user['id'])

@router.post('/subscription')
def cancelar_suscripcion(
    data: CancelSubscription,
    user=Depends(check_permission(['ABONADO']))
):
    return subscription_cancellation.cancelar_suscripcion(data.user_id)
