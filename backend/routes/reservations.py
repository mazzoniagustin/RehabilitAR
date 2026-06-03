from fastapi import APIRouter, Depends
from services.reservations import (
    individual_class_reservation_service,
    regular_class_reservation_service,
    my_reservations_service,
    waitlist_service,
)
from schemes.reservations_scheme import IndividualReservation, RegularReservation, WaitlistJoin
from utils.permissions import check_permission
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(
    prefix="/reservations",
    tags=["Reservations"]
)

@router.get('/me')
def get_my_reservations(
    current_user=Depends(check_permission(['ABONADO', 'NO_ABONADO']))
):
    return my_reservations_service.get_my_reservations(current_user['id'])

@router.post('/regular')
def reservar_clase_fija(
    data: RegularReservation,
    current_user=Depends(check_permission(['ABONADO', 'NO_ABONADO']))
):
    return regular_class_reservation_service.reservar_clase_fija(current_user['id'], data.class_id,data.payment_percentage)

@router.post('/individual')
def reservar_clase_individual(
    data: IndividualReservation,
    current_user=Depends(check_permission(['NO_ABONADO', 'ABONADO']))
):
    raise HTTPException(
        status_code=400,
        detail="Las reservas deben pagarse desde Mercado Pago."
    )

@router.post('/waitlist')
def unirse_a_waitlist(
    data: WaitlistJoin,
    current_user=Depends(check_permission(['ABONADO', 'NO_ABONADO']))
):
    return waitlist_service.unirse_a_waitlist(current_user['id'], data.class_id)


@router.delete('/waitlist/{class_id}')
def salir_de_waitlist(
    class_id: str,
    current_user=Depends(check_permission(['ABONADO', 'NO_ABONADO']))
):
    return waitlist_service.salir_de_waitlist(current_user['id'], class_id)
