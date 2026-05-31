from fastapi import APIRouter, HTTPException
from services.payments_service import *
from pydantic import BaseModel

routerPayments = APIRouter(
    prefix="/payments",
    tags=["payments"]
)
class SubscriptionRequest(BaseModel):
    user_id: str

class DebtRequest(BaseModel):
    user_id: str
    debt_id: str
    amount: float

@routerPayments.post("/subscription")
def subscription_payment(data: SubscriptionRequest):
    result = pay_subscription(data.user_id)
    if "Error" in result:
        raise HTTPException(status_code=400, detail=result["Error"])

    return result

@routerPayments.get("/debts/{user_id}")
def debts(user_id: str):
    return get_user_debts(user_id)


@routerPayments.post("/debt")
def debt_payment(data: DebtRequest):
    return pay_debt(data.user_id, data.debt_id, data.amount)