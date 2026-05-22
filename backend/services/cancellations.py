from flask import request
from services import subscription_cancellation, reservation_cancellation, class_cancellation

from flask import Blueprint, request

router = Blueprint("cancellations", __name__)

@router.post("/cancellations/suscription_cancellation")
def cancelar_suscripcion():
    datos = request.get_json()
    user_id = datos["user_id"]
    resultado = subscription_cancellation.cancelar_suscripcion(user_id) #pendiente_de_implementar
    return resultado

@router.post("/cancellations/reservation_cancellation")
def cancelar_reserva():
    datos = request.get_json()
    reservation_id = datos["reservation_id"]
    resultado = reservation_cancellation.cancelar_reserva(reservation_id) #pendiente_de_implementar
    return resultado

@router.post("/cancellations/class_cancellation")
def cancelar_clase():
    datos = request.get_json()
    class_id = datos["class_id"]
    cancel_reason = datos["cancel_reason"]
    resultado = class_cancellation.cancelar_clase(class_id, cancel_reason) #pendiente_de_implementar
    return resultado