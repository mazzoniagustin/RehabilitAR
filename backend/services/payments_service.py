import qrcode
import base64
from io import BytesIO
from services.mp_service import sdk


def create_payment(items):
    data = {
        "items": items
    }

    response = sdk.preference().create(data)

    if "init_point" not in response["response"]:
        print(response)
        raise Exception("Mercado Pago no devolvió init_point")

    return response["response"]["init_point"]



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


def pay_subscription():
    item = [
        {
            "id": "Mensualidad RehabilitAR",
            "title" : "Mensualidad RehabilitAR",
            "quantity" : 1,
            "unit_price" : 16
        }
    ]
    link = create_payment (item)
    qr = create_qr (link)
    return {
        "payment_url": link,
        "qr_url": qr
    }

def pay_debt(amount):
    item = [
        {
            "title" : "Deuda",
            "quantity" : 1,
            "unit_price" : amount
        }
    ]
    link = create_payment (item)
    return link


def create_qr(link):
    img = qrcode.make(link)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{qr_base64}"

def generate_receipt():
    print()
def pay_with_MP():
    print()


def pay_with_cash():
    print()

