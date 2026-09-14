from fastapi import APIRouter, HTTPException, Depends
from services.payments_service import *
from pydantic import BaseModel
from utils.permissions import check_permission

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

class ReservationPaymentRequest(BaseModel):
    class_id: str
    class_type: str
    payment_percentage: int

class CashSubscriptionRequest(BaseModel):
    user_id: str

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

@routerPayments.get("/subscription/status/{user_id}")
def subscription_status(user_id: str):
    res = supabase.table("users") \
        .select("rol") \
        .eq("id", user_id) \
        .single() \
        .execute()

    return {
        "is_subscribed": res.data["rol"] == "ABONADO",
        "rol": res.data["rol"]
    }

@routerPayments.get("/debt/status/{debt_id}")
def debt_status(debt_id: str):
    res = supabase.table("payments") \
        .select("status") \
        .eq("id", debt_id) \
        .single() \
        .execute()

    return {
        "is_paid": res.data["status"] == "PAGADO",
        "status": res.data["status"]
    }




@routerPayments.post("/reservation")
def reservation_payment(data: ReservationPaymentRequest, current_user=Depends(check_permission(['NO_ABONADO', 'ABONADO']))):
    return pay_reservation(
        current_user["id"],
        data.class_id,
        data.class_type,
        data.payment_percentage
    )  

@routerPayments.get("/reservation/status/{payment_id}")
def reservation_status(payment_id: str):
    return check_reservation_payment_status(payment_id)

@routerPayments.get("/subscription/cash/validate/{user_id}")
def validate_cash_subscription(
    user_id: str,
    current_user=Depends(check_permission(['RECEPCIONISTA']))
):
    result = validate_subscription_payment(user_id)

    if "Error" in result:
        raise HTTPException(status_code=400, detail=result["Error"])

    return result