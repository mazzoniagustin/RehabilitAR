from fastapi import APIRouter, Depends
from services import class_cancellation, reservation_cancellation, subscription_cancellation
from schemes.cancellation_scheme import CancelClass, CancelReservation, CancelSubscription
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
    return class_cancellation.cancelar_clase(data.class_id, data.cancel_reason)

@router.post('/reservation')
def cancelar_reserva(
    data: CancelReservation,
    user=Depends(check_permission(['ABONADO', 'NO_ABONADO']))
):
    return reservation_cancellation.cancelar_reserva(data.reservation_id)

@router.post('/subscription')
def cancelar_suscripcion(
    data: CancelSubscription,
    user=Depends(check_permission(['ABONADO']))
):
    return subscription_cancellation.cancelar_suscripcion(data.user_id)