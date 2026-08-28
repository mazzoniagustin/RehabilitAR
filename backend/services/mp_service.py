import os
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

TEST_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN_TEST")

MP_EXTERNAL_POS_ID = os.getenv("MP_EXTERNAL_POS_ID")

def create_qr_order(items, user_id, payment_type=None, debt_id=None):
    total_amount = sum(
        float(item["unit_price"]) * int(item["quantity"])
        for item in items
    )

    data = {
        "type": "qr",
        "total_amount": str(total_amount),
        "external_reference": str(user_id),
        "description": payment_type or "Pago RehabilitAR",
        "config": {
            "qr": {
                "mode": "dynamic",
                "external_pos_id": MP_EXTERNAL_POS_ID
            }
        },
        "transactions": {
            "payments": [
                {
                    "amount": str(total_amount)
                }
            ]
        },
        "items": [ {
                "title": payment_type or item["title"],
                "quantity": int(item["quantity"]),
                "unit_price": str(item["unit_price"]),
                "unit_measure": "unit"
            }
            for item in items
        ]
        
    }

    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
    }

    response = requests.post(
        "https://api.mercadopago.com/v1/orders",
        json=data,
        headers=headers
    )

    print("MP STATUS:", response.status_code)
    print("MP RESPONSE:", response.text)

    if response.status_code not in [200, 201]:
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)
        raise Exception(
            f"Mercado Pago devolvió {response.status_code}: {response.text}"
        )

    return response.json()   