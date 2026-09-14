from datetime import datetime

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException

from database import supabase_admin


def _client():
    if not supabase_admin:
        raise HTTPException(
            status_code=500,
            detail="Falta configurar SUPABASE_SERVICE_ROLE_KEY para gestionar suscripciones."
        )
    return supabase_admin


def get_active_subscription(user_id: str):
    response = (
        _client().table("subscriptions")
        .select("id, user_id, status, start_date, end_date, monthly_price, discount_percentage, payment_deadline")
        .eq("user_id", str(user_id))
        .eq("status", "ACTIVA")
        .order("end_date", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def _validate_abonado(user_id: str):
    response = (
        _client().table("users")
        .select("rol")
        .eq("id", str(user_id))
        .single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if response.data.get("rol") != "ABONADO":
        raise HTTPException(status_code=400, detail="El usuario no es abonado.")


def ensure_active_subscription(user_id: str, monthly_price=0, activate_user: bool = False):
    user_id = str(user_id)
    current = get_active_subscription(user_id)
    if current:
        if activate_user:
            _client().table("users").update({"rol": "ABONADO"}).eq("id", user_id).execute()
        return current

    if not activate_user:
        _validate_abonado(user_id)

    today = datetime.now().date()
    created = (
        _client().table("subscriptions")
        .insert({
            "user_id": user_id,
            "status": "ACTIVA",
            "start_date": today.isoformat(),
            "end_date": (datetime.now() + relativedelta(months=1)).date().isoformat(),
            "monthly_price": monthly_price,
            "discount_percentage": 0,
            "payment_deadline": today.isoformat(),
        })
        .execute()
    )

    if activate_user:
        _client().table("users").update({"rol": "ABONADO"}).eq("id", user_id).execute()

    return created.data[0]
