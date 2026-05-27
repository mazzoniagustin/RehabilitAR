from fastapi import APIRouter, Depends
from services.reservations import individual_class_reservation_service, regular_class_reservation_service
from schemes.reservations_scheme import IndividualReservation, RegularReservation
from utils.permissions import check_permission

router = APIRouter(
    prefix="/reservations",
    tags=["Reservations"]
)

@router.post('/regular')
def reservar_clase_fija(
    data: RegularReservation,
    current_user=Depends(check_permission(['ABONADO']))
):
    return regular_class_reservation_service.reservar_clase_fija(current_user['id'], data.class_id)

@router.post('/individual')
def reservar_clase_individual(
    data: IndividualReservation,
    current_user=Depends(check_permission(['NO_ABONADO', 'ABONADO']))
):
    return individual_class_reservation_service.reservar_clase_individual(current_user['id'], data.class_id, data.payment_percentage)
