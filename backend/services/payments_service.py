import qrcode
import base64
from datetime import datetime
from database import supabase
from io import BytesIO
from services.mp_service import sdk
from services.subscriptions_service import get_active_subscription


def create_payment(items, user_id, payment_type = None, debt_id=None):
    data = {
        "items": items,
        "external_reference": str(user_id),
        "metadata": {
            "payment_type": payment_type,
            "debt_id": debt_id
        }
    }

    response = sdk.preference().create(data)

    if "init_point" not in response["response"]:
        print(response)
        raise Exception("Mercado Pago no devolvió init_point")

    return response["response"]["init_point"]

def create_qr(link):
    img = qrcode.make(link)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{qr_base64}"

def pay_deposit():
    item = [
        {
            "title" : "Seña del 50%",
            "quantity" : 1,
            "unit_price" : 8
        }
    ]
    link = create_payment (item)
    return link


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
    link = create_payment (item, user_id, "SUBSCRIPTION")
    qr = create_qr (link)
    return {
        "payment_url": link,
        "qr_url": qr
    }

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
    link = create_payment (item, user_id, "DEBT", debt_id)
    qr = create_qr (link)
    return {
        "payment_url": link,
        "qr_url": qr
    }



def generate_receipt():
    print()
def pay_with_MP():
    print()


def pay_with_cash():
    print()
