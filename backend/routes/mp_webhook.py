from database import supabase
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Request
from services.mp_service import sdk

routerMPWebhook = APIRouter(
    prefix="/mp",
    tags=["Mercado Pago Webhook"]
)



@routerMPWebhook.post("/webhook")
async def mp_webhook(request: Request):
    body = await request.json()

    print("Webhook recibido:", body)

    if body.get("type") == "payment":
        payment_id = body["data"]["id"]

        payment = sdk.payment().get(payment_id)
        payment_data = payment["response"]

        status = payment_data.get("status")
        user_id = payment_data.get("external_reference")

        
        metadata = payment_data.get("metadata", {})
        payment_type = metadata.get("payment_type")
        debt_id = metadata.get("debt_id")
        if status == "approved":
            if payment_type == "SUBSCRIPTION":
                supabase.table("subscriptions").insert({
                    "used_id": user_id,
                    "status": "ACTIVA",
                    "start_date": datetime.now().date().isoformat(),
                    "end_date": (datetime.now() + relativedelta(months=1)).date().isoformat(),
                    "monthly_price": payment_data.get("transaction_amount"),
                    "discount_percentage": 0,
                    "payment_deadline": datetime.now().date().isoformat()
                }).execute()

                supabase.table("users").update({
                    "rol": "ABONADO"
                }).eq("id", user_id).execute()

                print("Suscripción activada correctamente")
            elif payment_type == "DEBT":
                supabase.table("payments").update({
                    "status": "PAGADO",
                    "paid_at": datetime.now().isoformat(),
                    "payment_method": "MERCADO_PAGO"
                }).eq("id", debt_id).execute()
    return {"status": "ok"}
