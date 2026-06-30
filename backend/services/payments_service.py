import qrcode
import base64
from datetime import datetime, timedelta
from database import supabase
from io import BytesIO
from services.mp_service import create_qr_order
from fastapi import HTTPException
from services.reservations.individual_class_reservation_service import reservar_clase_individual
from services.reservations.regular_class_reservation_service import reservar_clase_fija
import requests
import os
from dotenv import load_dotenv
from services.subscriptions_service import get_active_subscription

load_dotenv()

TEST_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN_TEST")

def create_qr(data):
    img = qrcode.make(data)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{qr_base64}"

def get_payment_title(payment_type):
    if payment_type == "SUBSCRIPTION":
        return "Mensualidad de RehabilitAR"
    elif payment_type == "RESERVATION_50":
        return "Reserva 50% RehabilitAR"
    elif payment_type =="RESERVATION_100":
        return "Reserva 100% RehabilitAR"
    elif payment_type == "DEBT":
        return "Deuda de RehabilitAR"
    return "Pago RehabilitAR"

def generate_mp_qr(items, user_id, payment_type, debt_id=None, reservation_id=None):
    amount = sum(float(i["unit_price"]) * int(i["quantity"]) for i in items)
    
    if payment_type == "SUBSCRIPTION":
        payment_res = supabase.table("payments").insert({
            "user_id": user_id,
            "amount": amount,
            "status": "PENDIENTE",
            "payment_method": "MERCADO_PAGO",
            "payment_reason": "SUBSCRIPTION"
        }).execute()
        payment_row_id = payment_res.data[0]["id"]

    elif payment_type == "DEBT":
        payment_row_id = debt_id
        supabase.table("payments").update({
        "payment_method": "MERCADO_PAGO",
        "payment_reason": "DEBT"
        }).eq("id", payment_row_id).execute()
    
    elif payment_type in ["RESERVATION_50", "RESERVATION_100"]:
        payment_row_id = reservation_id
        supabase.table("payments").update({
            "payment_method": "MERCADO_PAGO",
            "payment_reason": payment_type
        }).eq("id", payment_row_id).execute()

    order = create_qr_order(
        items=items,
        user_id=payment_row_id,
        payment_type=get_payment_title(payment_type),
        debt_id=debt_id
    )

    mp_payment_id = order["transactions"]["payments"][0]["id"]
    supabase.table("payments").update({
        "external_id": mp_payment_id
    }).eq("id", payment_row_id).execute()

    qr_data = order["type_response"]["qr_data"]
    qr = create_qr(qr_data)

    return {
        "payment_id": payment_row_id,
        "order_id": order["id"],
        "qr_url": qr
    }



def pay_reservation(user_id, class_id, class_type, payment_percentage):
    if payment_percentage not in (50, 100):
        raise HTTPException(status_code=400, detail="Porcentaje inválido.")

    clase = supabase.table("classes") \
        .select("*") \
        .eq("id", class_id) \
        .single() \
        .execute() \
        .data

    start_time = clase["start_time"]

    conflict_res = supabase.table("reservations") \
        .select("id, classes!inner(start_time)") \
        .eq("user_id", user_id) \
        .neq("status", "CANCELADA") \
        .eq("classes.start_time", start_time) \
        .execute()

    if conflict_res.data:
        raise HTTPException(
            status_code=400,
            detail="Ya estás inscripto en otra clase en el mismo día y horario."
        )

    conflict_waitlist = supabase.table("waitlist") \
        .select("id, classes!inner(start_time)") \
        .eq("user_id", user_id) \
        .eq("classes.start_time", start_time) \
        .execute()

    if conflict_waitlist.data:
        raise HTTPException(
            status_code=400,
            detail="Ya estás anotado en lista de espera para otra clase en el mismo día y horario."
        )
    amount = float(clase["price"]) * (payment_percentage / 100)

    payment_reason = "RESERVATION_50" if payment_percentage == 50 else "RESERVATION_100"

    payment_res = supabase.table("payments").insert({
        "user_id": user_id,
        "class_id": class_id,
        "amount": amount,
        "status": "ESPERANDO_MP",
        "payment_method": "MERCADO_PAGO",
        "payment_reason": payment_reason,
        "payment_type": "RESERVATION",
        "payment_percentage": payment_percentage
    }).execute()

    payment_id = payment_res.data[0]["id"]

    item = [{
        "title": f"Reserva RehabilitAR {payment_percentage}%",
        "quantity": 1,
        "unit_price": amount
    }]

    order = create_qr_order(item, payment_id)

    mp_payment_id = order["transactions"]["payments"][0]["id"]

    supabase.table("payments").update({
        "external_id": str(mp_payment_id)
    }).eq("id", payment_id).execute()

    qr_data = order["type_response"]["qr_data"]

    return {
        "payment_id": payment_id,
        "qr_url": create_qr(qr_data)
    }

def get_payment_title(payment_type):
    if payment_type == "SUBSCRIPTION":
        return "Mensualidad de RehabilitAR"
    elif payment_type == "RESERVATION_50":
        return "Reserva 50% RehabilitAR"
    elif payment_type =="RESERVATION_100":
        return "Reserva 100% RehabilitAR"
    elif payment_type == "DEBT":
        return "Deuda de RehabilitAR"
    return "Pago RehabilitAR"


def pay_subscription(user_id):
    user_response = supabase.table("users") \
        .select("id") \
        .eq("id", user_id) \
        .single() \
        .execute()
    if not user_response.data:
        return {
            "Error": "Usuario no encontrado."
        }

    if get_active_subscription(user_id):
        return {
            "Error": "Ya sos cliente abonado. No podés volver a pagar la mensualidad."
        }
    today = datetime.now()
    if today.day > 10:
        return {
            "Error": "No puede pagar su mensualidad debido a que ya pasaron los 10 días limites de iniciado el mes"
        }
    item = [
        {
            "id": "Mensualidad RehabilitAR",
            "title" : "Mensualidad RehabilitAR",
            "quantity" : 1,
            "unit_price" : 16
        }
    ]
    return generate_mp_qr(
        items=item,
        user_id=user_id,
        payment_type="SUBSCRIPTION"
    )

def get_user_debts(user_id):
    response = supabase.table("payments") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    return [
        p for p in response.data
        if p.get("status", "").strip() == "PENDIENTE"
        and p.get("payment_reason") == "DEBT"
    ]

def check_reservation_payment_status(payment_id: str):
    payment_res = supabase.table("payments") \
        .select("status") \
        .eq("id", payment_id) \
        .single() \
        .execute()

    status = payment_res.data["status"]

    return {
        "is_paid": status == "PAGADO",
        "status": status
    }
            




def pay_debt(user_id, debt_id, amount):
    item = [
        {
            "title" : "Deuda de RehabilitAR",
            "quantity" : 1,
            "unit_price" : float(amount)
        }
    ]
    return generate_mp_qr(
        items=item,
        user_id=user_id,
        payment_type="DEBT",
        debt_id=debt_id
    )

def generate_receipt():
    print()

def validate_subscription_payment(user_id):
    user_response = supabase.table("users") \
        .select("id") \
        .eq("id", user_id) \
        .single() \
        .execute()

    if not user_response.data:
        return {
            "Error": "Usuario no encontrado."
        }

    if get_active_subscription(user_id):
        return {
            "Error": "Ya sos cliente abonado. No podés volver a pagar la mensualidad."
        }

    today = datetime.now()

    if today.day > 10:
        return {
            "Error": "No puede pagar su mensualidad debido a que ya pasaron los 10 días limites de iniciado el mes"
        }

    return {
        "message": "El cliente puede registrar la mensualidad."
    }

def pay_with_cash(user_id: str):
    validation = validate_subscription_payment(user_id)
    if "Error" in validation:
        return validation

    today = datetime.now()

    supabase.table("payments").insert({
        "user_id": user_id,
        "amount": 16,
        "status": "PAGADO",
        "payment_method": "EFECTIVO",
        "payment_reason": "SUBSCRIPTION",
        "payment_type": "SUBSCRIPTION",
        "paid_at": today.isoformat()
    }).execute()

    supabase.table("users").update({
        "rol": "ABONADO"
    }).eq("id", user_id).execute()

    return {
        "message": "Mensualidad registrada correctamente. El cliente ahora es abonado."
    }

    

