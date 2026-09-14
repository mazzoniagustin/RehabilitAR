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
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
from services.notifications_service import create_notification
from utils.notifications import send_email


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

    payment_insert  = supabase.table("payments").insert({
        "user_id": user_id,
        "amount": 16,
        "status": "PAGADO",
        "payment_method": "EFECTIVO",
        "payment_reason": "SUBSCRIPTION",
        "payment_type": "SUBSCRIPTION",
        "paid_at": today.isoformat()
    }).execute()

    payment_id = payment_insert.data[0]["id"]

    supabase.table("users").update({
        "rol": "ABONADO"
    }).eq("id", user_id).execute()

    notify_payment_registered(payment_id)
    return {
        "message": "Mensualidad registrada correctamente. El cliente ahora es abonado."
    }

    
# Notificaciones y comprobantes

def get_mp_payment_data(mp_payment_id):
    if not mp_payment_id:
        return None

    try:
        response = requests.get(
            f"https://api.mercadopago.com/v1/payments/{mp_payment_id}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )

        print("MP PAYMENT DETAIL STATUS:", response.status_code)
        print("MP PAYMENT DETAIL RESPONSE:", response.text)

        if response.status_code != 200:
            return None

        return response.json()
    except Exception as e:
        print("Error consultando pago en Mercado Pago:", e)
        return None
    
def download_mp_receipt_if_available(mp_data, payment_id):
    if not mp_data:
        return None

    possible_urls = [
        mp_data.get("transaction_details", {}).get("external_resource_url"),
        mp_data.get("point_of_interaction", {}).get("transaction_data", {}).get("ticket_url"),
    ]

    receipt_url = next((url for url in possible_urls if url), None)

    if not receipt_url:
        print("Mercado Pago no devolvió URL descargable de comprobante.")
        return None

    try:
        response = requests.get(receipt_url, timeout=15)

        if response.status_code != 200:
            return None

        content_type = response.headers.get("Content-Type", "")

        if "pdf" in content_type:
            extension = "pdf"
        elif "png" in content_type:
            extension = "png"
        elif "jpeg" in content_type or "jpg" in content_type:
            extension = "jpg"
        else:
            extension = "bin"

        receipts_dir = "receipts"
        os.makedirs(receipts_dir, exist_ok=True)

        file_path = os.path.join(receipts_dir, f"comprobante_mp_{payment_id}.{extension}")

        with open(file_path, "wb") as f:
            f.write(response.content)

        return file_path

    except Exception as e:
        print("Error descargando comprobante de Mercado Pago:", e)
        return None
    


def payment_reason_to_spanish(payment):
    reason = payment.get("payment_reason")

    if reason == "SUBSCRIPTION":
        return "Mensualidad de RehabilitAR. El cliente es ahora abonado."

    if reason == "RESERVATION_100":
        return "Reserva de clase abonada al 100%."

    if reason == "RESERVATION_50":
        return "Reserva de clase abonada al 50%. Se generó una deuda por el 50% restante."

    if reason == "DEBT":
        return "Deuda saldada correctamente."

    return "Pago registrado en RehabilitAR."

def get_class_payment_detail(payment):
    if not payment.get("class_id"):
        return ""

    clase = supabase.table("classes") \
        .select("activity_type, start_time, type") \
        .eq("id", payment["class_id"]) \
        .single() \
        .execute() \
        .data

    if not clase:
        return ""

    start_time = clase.get("start_time")
    formatted_date = start_time

    try:
        formatted_date = datetime.fromisoformat(start_time.replace("Z", "+00:00")) \
            .strftime("%d/%m/%Y a las %H:%M")
    except Exception:
        pass

    return f"""
                Clase asociada:
                Actividad: {(clase.get("activity_type") or "").replace("_", " ")}
                Tipo: {clase.get("type") or "-"}
                Fecha y horario: {formatted_date}
            """


def build_payment_message(payment, user, mp_data=None):
    motivo = payment_reason_to_spanish(payment)
    class_detail = get_class_payment_detail(payment)

    mp_detail = ""

    if mp_data:
        mp_detail = f"""
                        Datos del comprobante de Mercado Pago:
                        ID de pago Mercado Pago: {mp_data.get("id", "-")}
                        Estado Mercado Pago: {mp_data.get("status", "-")}
                        Fecha de aprobación: {mp_data.get("date_approved", "-")}
                        Medio de pago: {mp_data.get("payment_method_id", "-")}
                        Tipo de pago: {mp_data.get("payment_type_id", "-")}
                    """

    return f"""Hola {user.get("name")},

                Se registró correctamente un pago en RehabilitAR.

                Cliente afectado:
                Nombre: {user.get("name")} {user.get("surname")}
                Email: {user.get("email")}

                Detalle del pago:
                    ID interno del pago: {payment.get("id")}
                    Monto: ${payment.get("amount")}
                    Estado: {payment.get("status")}
                    Método registrado: {payment.get("payment_method")}
                    Motivo: {motivo}
                    Fecha registrada: {payment.get("paid_at") or "-"}

                {class_detail}
                {mp_detail}

            Saludos,
            Equipo RehabilitAR
        """

def notify_payment_registered(payment_id: str):
    payment = supabase.table("payments") \
        .select("*") \
        .eq("id", payment_id) \
        .single() \
        .execute() \
        .data

    if not payment:
        print("No se encontró el pago para notificar:", payment_id)
        return

    user = supabase.table("users") \
        .select("id, name, surname, email") \
        .eq("id", payment["user_id"]) \
        .single() \
        .execute() \
        .data

    if not user:
        print("No se encontró el usuario para notificar:", payment["user_id"])
        return

    mp_data = None
    attachment_path = None

    if payment.get("payment_method") == "MERCADO_PAGO":
        mp_data = get_mp_payment_data(payment.get("external_id"))
        attachment_path = download_mp_receipt_if_available(mp_data, payment_id)

    message = build_payment_message(payment, user, mp_data)

    create_notification(
        payment["user_id"],
        "Pago registrado correctamente",
        message
    )

    email_body = message

    if attachment_path:
        email_body += "\n\nAdjuntamos el comprobante de Mercado Pago."
    else:
        email_body += "\n\nNo se encontró un comprobante descargable desde Mercado Pago. Se incluyen los datos del pago en este mensaje."

    send_email(
        to_email=user["email"],
        subject="Pago registrado correctamente - RehabilitAR",
        body=email_body,
        attachment_path=attachment_path
    )