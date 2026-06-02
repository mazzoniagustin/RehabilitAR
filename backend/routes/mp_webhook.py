from database import supabase
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from fastapi import APIRouter, Request

load_dotenv()


routerMPWebhook = APIRouter(
    prefix="/mp",
    tags=["Mercado Pago Webhook"]
)

TEST_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN_TEST")

@routerMPWebhook.post("/webhook")
async def mp_webhook(request: Request):
    body = await request.json()
    print("Webhook recibido:", body)

    payment_id = None

    if body.get("type") == "payment":
        payment_id = body.get("data", {}).get("id")

    if not payment_id:
        return {"status": "ignored"}

    response = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={
            "Authorization": f"Bearer {TEST_TOKEN}"
        }
    )

    payment_data = response.json()

    print("PAYMENT DATA:", payment_data)

    status = payment_data.get("status")
    user_id = payment_data.get("external_reference")
    metadata = payment_data.get("metadata", {})

    payment_type = metadata.get("payment_type")
    debt_id = metadata.get("debt_id")

    if status == "approved":
        if payment_type == "SUBSCRIPTION":
            supabase.table("users").update({
                "rol": "ABONADO"
            }).eq("id", user_id).execute()

        elif payment_type == "DEBT":
            supabase.table("payments").update({
                "status": "PAGADO",
                "paid_at": datetime.now().isoformat(),
                "payment_method": "MERCADO_PAGO"
            }).eq("id", debt_id).execute()

    return {"status": "ok"}
