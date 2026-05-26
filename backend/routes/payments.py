from fastapi import APIRouter
from services.payments_service import pay_subscription

routerPayments = APIRouter(
    prefix="/payments",
    tags=["payments"]
)

@routerPayments.post("/subscription")
def subscription_payment():
    return pay_subscription()