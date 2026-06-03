from database import supabase
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from services.reservations.individual_class_reservation_service import reservar_clase_individual
from services.reservations.regular_class_reservation_service import reservar_clase_fija


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

    if body.get("type") != "order":
        return {"status": "ignored"}

    data = body.get("data", {})

    order_status = data.get("status")
    status_detail = data.get("status_detail")
    payment_id = data.get("transactions", {}).get("payments", [{}])[0].get("id")

    payment_row_id = data.get("external_reference")

    print("ORDER STATUS:", order_status)
    print("STATUS DETAIL:", status_detail)
    print("PAYMENT ROW ID:", payment_row_id)
    print("MP PAYMENT ID:", payment_id)

    if order_status == "processed" and status_detail == "accredited":
        payment_res = supabase.table("payments") \
            .select("*") \
            .eq("id", payment_row_id) \
            .single() \
            .execute()

        payment = payment_res.data


        print("PAYMENT ROW ID:", payment_row_id)
        print("PAYMENT DB:", payment)
        print("PAYMENT REASON:", payment["payment_reason"])
        update_payment = supabase.table("payments").update({
            "status": "PAGADO",
                "paid_at": datetime.now().isoformat(),
                "payment_method": "MERCADO_PAGO",
                "external_id": payment_id
            }).eq("id", payment_row_id).execute()

        print("UPDATE PAYMENT:", update_payment.data)


        if payment["payment_reason"] == "SUBSCRIPTION":
            supabase.table("users").update({
                "rol": "ABONADO"
            }).eq("id", payment["user_id"]).execute()

        elif payment["payment_reason"] in ["RESERVATION_50", "RESERVATION_100"]:
            print("ENTRÓ A RESERVA")

            class_id = payment["class_id"]
            user_id = payment["user_id"]
            percentage = payment["payment_percentage"]

            clase = supabase.table("classes") \
                .select("type") \
                .eq("id", class_id) \
                .single() \
                .execute() \
                .data

            if clase["type"] == "INDIVIDUAL":
                result = reservar_clase_individual(user_id, class_id, percentage)
            else:
                result = reservar_clase_fija(user_id, class_id, percentage)

            print("RESULT RESERVA:", result)

            reservation_id = result.get("reservation_id")

            supabase.table("payments").update({
                "reservation_id": reservation_id
            }).eq("id", payment_row_id).execute()

            if payment["payment_reason"] == "RESERVATION_50":
                supabase.table("payments").insert({
                    "user_id": user_id,
                    "reservation_id": reservation_id,
                    "class_id": class_id,
                    "amount": float(payment["amount"]),
                    "status": "PENDIENTE",
                    "payment_method": None,
                    "payment_reason": "DEBT",
                    "payment_type": "RESERVATION_REMAINING"
                }).execute()

        elif payment["payment_reason"] == "DEBT":
            return {"status": "debt paid"}

        return {"status": "payment updated"}

    return {"status": "not accredited"}
