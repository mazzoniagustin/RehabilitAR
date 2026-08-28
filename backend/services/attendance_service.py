from fastapi import HTTPException
from database import supabase
import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

import qrcode

attendance_types = ["PRESENTE", "PRESENTE_CON_AVISO", "AUSENTE"]

def get_class_participants (class_id, professor_id):
    class_res = supabase.table("classes") \
        .select("*") \
        .eq ("id", class_id) \
        .eq ("professor_id", professor_id) \
        .execute()
    
    if not class_res.data:
        raise HTTPException (status_code=403, detail="No puede modificar la asistencia de una clase que no tiene asignada")
    
    reservations_res = supabase.table("reservations") \
        .select("id, user_id, users(name, surname, email), attendance(status, comment)") \
        .eq("class_id", class_id) \
        .eq("status", "CONFIRMADA") \
        .execute()

    return reservations_res.data
    

def register_attendance (class_id, user_id, reservation_id, professor_id, status, comment: str | None = None):
    if status not in attendance_types:
        raise HTTPException (status_code= 400, detail= "Estado de asistencia invalido.")
    if status == "PRESENTE_CON_AVISO" and not comment:
        raise HTTPException(status_code=400, detail= "Debe haber un aviso si selecciona presente con aviso.")
    
    class_res = supabase.table("classes")\
                .select("*") \
                .eq ("id", class_id)\
                .eq ("professor_id", professor_id) \
                .execute()
    
    if not class_res.data:
        raise HTTPException (status_code=403, detail="No puede modificar la asistencia de una clase que no tiene asignada")
    
    reservation_res = supabase.table("reservations") \
        .select("*") \
        .eq("id", reservation_id) \
        .eq("class_id", class_id) \
        .eq("user_id", user_id) \
        .eq("status", "CONFIRMADA") \
        .execute()

    if not reservation_res.data:
        raise HTTPException(status_code=404, detail="La reserva no corresponde a esta clase.")
    
    attendance_data = {
        "class_id": class_id,
        "user_id": user_id,
        "reservation_id": reservation_id,
        "status": status,
        "comment": comment,
        "checked_by": professor_id
    }

    response = supabase.table("attendance") \
        .upsert(attendance_data, on_conflict="class_id,user_id") \
        .execute()
    
    return response.data[0]


def _generate_qr_base64(data: str) -> str:
    image = qrcode.make(data)

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{encoded}"


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def generate_attendance_qr(
    professor_id: str,
    class_id: str,
    frontend_public_url: str
):
    try:
        professor_id = str(professor_id)
        class_id = str(class_id)

        class_response = (
            supabase.table("classes")
            .select(
                "id, professor_id, start_time, status, "
                "attendance_token, attendance_token_expires_at, "
                "attendance_qr_active"
            )
            .eq("id", class_id)
            .single()
            .execute()
        )

        clase = class_response.data

        if not clase:
            raise HTTPException(
                status_code=404,
                detail="Clase no encontrada."
            )

        if str(clase.get("professor_id")) != professor_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "No podés generar el QR de esta clase porque no la tenes asignada"
                )
            )

        if clase.get("status") == "CANCELADA":
            raise HTTPException(
                status_code=400,
                detail="No se puede generar asistencia para una clase cancelada."
            )

        # Cada generación reemplaza cualquier QR anterior de la clase.
        token = str(uuid4())

        # El QR funcionará durante 30 minutos.
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        update_response = (
            supabase.table("classes")
            .update({
                "attendance_token": token,
                "attendance_token_expires_at": expires_at.isoformat(),
                "attendance_qr_active": True
            })
            .eq("id", class_id)
            .execute()
        )

        if not update_response.data:
            raise HTTPException(
                status_code=500,
                detail="No se pudo habilitar el QR de asistencia."
            )

        frontend_base = frontend_public_url.rstrip("/")

        attendance_url = (
            f"{frontend_base}/attendance.html"
            f"?token={token}"
        )

        return {
            "message": "QR de asistencia generado correctamente.",
            "token": token,
            "expires_at": expires_at.isoformat(),
            "attendance_url": attendance_url,
            "qr_url": _generate_qr_base64(attendance_url)
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el QR de asistencia: {str(error)}"
        )


def register_attendance_by_email(token: str, email: str):
    try:
        token = str(token).strip()
        normalized_email = str(email).strip().lower()

        if not token:
            raise HTTPException(
                status_code=400,
                detail="El código de asistencia no es válido."
            )

        if not normalized_email:
            raise HTTPException(
                status_code=400,
                detail="Ingresá tu correo electrónico."
            )

        # Buscar la clase asociada al token generado por el profesor.
        class_response = (
            supabase.table("classes")
            .select(
                "id, status, attendance_token, "
                "attendance_token_expires_at"
            )
            .eq("attendance_token", token)
            .single()
            .execute()
        )

        clase = class_response.data

        if not clase:
            raise HTTPException(
                status_code=404,
                detail="El código QR no es válido."
            )

        if clase.get("status") == "CANCELADA":
            raise HTTPException(
                status_code=400,
                detail="La clase fue cancelada."
            )

        expires_at_raw = clase.get("attendance_token_expires_at")

        if not expires_at_raw:
            raise HTTPException(
                status_code=400,
                detail="El código QR de asistencia ya no está activo."
            )

        expires_at = _parse_datetime(expires_at_raw)

        if datetime.now(timezone.utc) > expires_at:
            (
                supabase.table("classes")
                .update({
                    "attendance_token": None,
                    "attendance_token_expires_at": None
                })
                .eq("id", clase["id"])
                .execute()
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    "El código QR venció. "
                    "Solicitá al profesor que genere uno nuevo."
                )
            )

        # Buscar al usuario por email.
        user_response = (
            supabase.table("users")
            .select(
                "id, name, surname, email, "
                "account_status, rol"
            )
            .ilike("email", normalized_email)
            .execute()
        )

        users_found = user_response.data or []

        if not users_found:
            raise HTTPException(
                status_code=404,
                detail="No se encontró un usuario con el correo ingresado."
            )

        user = users_found[0]

        if user.get("account_status") != "ACTIVA":
            raise HTTPException(
                status_code=403,
                detail="La cuenta asociada al correo se encuentra suspendida."
            )

        if user.get("rol") not in ["ABONADO", "NO_ABONADO"]:
            raise HTTPException(
                status_code=403,
                detail="El correo ingresado no pertenece a un cliente."
            )

        # Verificar que el cliente esté inscripto en la clase.
        reservation_response = (
            supabase.table("reservations")
            .select("id, user_id, class_id, status")
            .eq("class_id", clase["id"])
            .eq("user_id", user["id"])
            .eq("status", "CONFIRMADA")
            .execute()
        )

        reservations = reservation_response.data or []

        if not reservations:
            raise HTTPException(
                status_code=403,
                detail="El cliente no está inscripto en esta clase."
            )

        reservation = reservations[0]

        # Verificar si ya tiene una asistencia registrada.
        attendance_response = (
            supabase.table("attendance")
            .select("id, status, comment")
            .eq("class_id", clase["id"])
            .eq("user_id", user["id"])
            .execute()
        )

        existing_attendance = (
            attendance_response.data[0]
            if attendance_response.data
            else None
        )

        if existing_attendance:
            status_labels = {
                "PRESENTE": "presente",
                "PRESENTE_CON_AVISO": "presente con aviso",
                "AUSENTE": "ausente"
            }

            stored_status = existing_attendance.get("status")

            current_status = status_labels.get(
                stored_status,
                str(stored_status or "registrada")
                .replace("_", " ")
                .lower()
            )

            raise HTTPException(
                status_code=409,
                detail=(
                    "La asistencia de este cliente "
                    f"ya fue registrada como {current_status}."
                )
            )

        insert_response = (
            supabase.table("attendance")
            .insert({
                "class_id": clase["id"],
                "user_id": user["id"],
                "reservation_id": reservation["id"],
                "status": "PRESENTE",
                "comment": "Asistencia registrada mediante QR."
            })
            .execute()
        )

        if not insert_response.data:
            raise HTTPException(
                status_code=500,
                detail="No se pudo registrar la asistencia."
            )

        return {
            "message": (
                "Asistencia registrada correctamente para "
                f"{user['name']} {user['surname']}."
            ),
            "status": "PRESENTE"
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al registrar la asistencia: {str(error)}"
        )


def disable_attendance_qr(
    professor_id: str,
    class_id: str
):
    try:
        class_response = (
            supabase.table("classes")
            .select("id, professor_id")
            .eq("id", str(class_id))
            .single()
            .execute()
        )

        clase = class_response.data

        if not clase:
            raise HTTPException(
                status_code=404,
                detail="Clase no encontrada."
            )

        if str(clase.get("professor_id")) != str(professor_id):
            raise HTTPException(
                status_code=403,
                detail="No podés cerrar la asistencia de esta clase."
            )

        (
            supabase.table("classes")
            .update({
                "attendance_qr_active": False
            })
            .eq("id", str(class_id))
            .execute()
        )

        return {
            "message": "El QR de asistencia fue desactivado."
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al cerrar el QR de asistencia: {str(error)}"
        )









