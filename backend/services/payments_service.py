import qrcode
import base64
from datetime import datetime
from database import supabase
from io import BytesIO
from services.mp_service import create_qr_order


def create_qr(link):
    img = qrcode.make(link)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{qr_base64}"

def generate_mp_qr(items, user_id, payment_type, debt_id=None):

    order = create_qr_order(items, user_id, payment_type, debt_id)

    qr_data = order["type_response"]["qr_data"]
    qr = create_qr(qr_data)

    return {
        "order_id": order["id"],
        "qr_url": qr
    }



def pay_deposit():
    item = [
        {
            "title" : "Seña del 50%",
            "quantity" : 1,
            "unit_price" : 8
        }
    ]
    order = create_qr_order(item, user_id, "SUBSCRIPTION")

    qr_data = order["type_response"]["qr_data"]
    qr = create_qr(qr_data)

    return {
        "order_id": order["id"],
        "qr_data": qr_data,
        "qr_url": qr
    }
    return link


def pay_subscription(user_id):
    user_response = supabase.table("users") \
        .select("rol") \
        .eq("id", user_id) \
        .single() \
        .execute()

    rol = user_response.data["rol"]

    if rol == "ABONADO":
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
        payment_type="Mensualidad RehabilitAR"
    )

def get_user_debts(user_id):
    response = supabase.table("payments") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    return [
        p for p in response.data
        if p.get("status", "").strip() == "PENDIENTE"
    ]
            




def pay_debt(user_id, debt_id, amount):
    item = [
        {
            "id": f"deuda_{debt_id}",
            "title" : "Pago de deuda",
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

def pay_reservation():
    print()


def generate_receipt():
    print()
def pay_with_MP():
    print()


def pay_with_cash():
    print()

