from datetime import date

from database import supabase_admin
from fastapi import HTTPException

MAX_MONTHLY_CREDITS = 3


def _current_month() -> str:
    today = date.today()
    return date(today.year, today.month, 1).isoformat()


def _history_payload(user_id: str, type_: str, reason: str, reservation_id=None, class_id=None):
    payload = {
        "user_id": str(user_id),
        "type": type_,
        "reason": reason,
    }
    if reservation_id:
        payload["reservation_id"] = str(reservation_id)
    if class_id:
        payload["class_id"] = str(class_id)
    return payload


def _client():
    if not supabase_admin:
        raise HTTPException(
            status_code=500,
            detail="Falta configurar SUPABASE_SERVICE_ROLE_KEY para gestionar beneficios."
        )
    return supabase_admin


def _get_or_create_credit_row(user_id: str):
    user_id = str(user_id)
    current_month = _current_month()
    client = _client()

    response = (
        client.table("credits")
        .select("id, available_credits, used_credits, month")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        created = (
            client.table("credits")
            .insert({
                "user_id": user_id,
                "available_credits": 0,
                "used_credits": 0,
                "month": current_month,
            })
            .execute()
        )
        return created.data[0]

    credit = response.data[0]
    if credit.get("month") != current_month:
        updated = (
            client.table("credits")
            .update({
                "available_credits": 0,
                "used_credits": 0,
                "month": current_month,
            })
            .eq("user_id", user_id)
            .execute()
        )
        return updated.data[0] if updated.data else {
            **credit,
            "available_credits": 0,
            "used_credits": 0,
            "month": current_month,
        }

    return credit


def _get_credit_row(user_id: str):
    response = (
        _client().table("credits")
        .select("id, available_credits, used_credits, month")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def otorgar_credito(
    user_id: str,
    reservation_id: str = None,
    class_id: str = None,
    reason: str = "Crédito otorgado por cancelación.",
):
    try:
        user_id = str(user_id)
        credit = _get_or_create_credit_row(user_id)
        available = credit.get("available_credits") or 0

        if available >= MAX_MONTHLY_CREDITS:
            return {"message": "El usuario ya alcanzó el máximo de créditos mensuales.", "granted": False}

        new_available = available + 1
        (
            _client().table("credits")
            .update({"available_credits": new_available, "month": _current_month()})
            .eq("user_id", user_id)
            .execute()
        )

        _client().table("credits_history").insert(
            _history_payload(user_id, "CREDITO_OTORGADO", reason, reservation_id, class_id)
        ).execute()

        return {"message": "Crédito otorgado exitosamente.", "granted": True, "available_credits": new_available}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al otorgar crédito: {str(e)}")


def retirar_credito(
    user_id: str,
    reservation_id: str = None,
    class_id: str = None,
    reason: str = "Crédito utilizado por el usuario.",
):
    try:
        user_id = str(user_id)
        credit = _get_credit_row(user_id)
        if not credit:
            raise HTTPException(status_code=400, detail="No hay créditos disponibles para retirar.")

        available = credit.get("available_credits") or 0
        used = credit.get("used_credits") or 0

        if available <= 0:
            raise HTTPException(status_code=400, detail="No hay créditos disponibles para retirar.")

        (
            _client().table("credits")
            .update({
                "available_credits": available - 1,
                "used_credits": used + 1,
                "month": _current_month(),
            })
            .eq("user_id", user_id)
            .execute()
        )

        _client().table("credits_history").insert(
            _history_payload(user_id, "CREDITO_RETIRADO", reason, reservation_id, class_id)
        ).execute()

        return {"message": "Crédito retirado exitosamente.", "available_credits": available - 1}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al retirar crédito: {str(e)}")


def retirar_Todoscredito(
    user_id: str,
    reservation_id: str = None,
    class_id: str = None,
    reason: str = "Todos los créditos retirados por alcanzar el límite de cancelaciones.",
):
    try:
        user_id = str(user_id)
        credit = _get_credit_row(user_id)
        if not credit:
            return {"message": "Sin créditos que retirar.", "removed": False}

        available = credit.get("available_credits") or 0

        if available <= 0:
            return {"message": "Sin créditos que retirar.", "removed": False}

        (
            _client().table("credits")
            .update({"available_credits": 0, "month": _current_month()})
            .eq("user_id", user_id)
            .execute()
        )

        _client().table("credits_history").insert(
            _history_payload(user_id, "CREDITOS_RETIRADOS_TODOS", reason, reservation_id, class_id)
        ).execute()

        return {"message": "Créditos retirados exitosamente.", "removed": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al retirar créditos: {str(e)}")


def _update_active_subscription_discount(user_id: str, discount_percentage: int):
    user_id = str(user_id)
    response = (
        _client().table("subscriptions")
        .select("id")
        .eq("user_id", user_id)
        .eq("status", "ACTIVA")
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="El usuario no tiene una suscripción activa.")

    subscription_id = response.data[0]["id"]
    (
        _client().table("subscriptions")
        .update({"discount_percentage": discount_percentage})
        .eq("id", subscription_id)
        .execute()
    )


def otorgar_descuento20(user_id: str):
    try:
        _update_active_subscription_discount(user_id, 20)
        return {"message": "Descuento del 20% otorgado exitosamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al otorgar descuento: {str(e)}")


def otorgar_descuento30(user_id: str):
    try:
        _update_active_subscription_discount(user_id, 30)
        return {"message": "Descuento del 30% otorgado exitosamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al otorgar descuento: {str(e)}")


def cancelar_descuentos(user_id: str):
    try:
        _update_active_subscription_discount(user_id, 0)
        return {"message": "Descuentos cancelados exitosamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cancelar descuentos: {str(e)}")
