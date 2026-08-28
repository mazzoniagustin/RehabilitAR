from fastapi import APIRouter, Depends
from pydantic import BaseModel
from services.attendance_service import get_class_participants
from services.attendance_service import register_attendance
from utils.permissions import get_current_user, check_permission
from services import attendance_service
import os
from schemes.attendance_scheme import AttendanceByEmail
from fastapi import APIRouter, Depends, HTTPException


routerAttendance = APIRouter(
    prefix="/attendance",
    tags=["attendance"]
)


class AttendanceRequest(BaseModel):
    class_id: str
    user_id: str
    reservation_id: str
    status: str
    notice_reason: str | None = None


@routerAttendance.get("/class/{class_id}/participants")
def get_participants(class_id, current_user=Depends(get_current_user)):
    if current_user["rol"] != "PROFESOR":
        raise Exception("Solo los profesores pueden pasar asistencia.")

    return get_class_participants(
        class_id,
        current_user["id"]
    )


@routerAttendance.post("/mark")
def mark(data: AttendanceRequest, current_user=Depends(get_current_user)):
    if current_user["rol"] != "PROFESOR":
        raise Exception("Solo los profesores pueden pasar asistencia.")

    return register_attendance(
        data.class_id,
        data.user_id,
        data.reservation_id,
        current_user["id"],
        data.status,
        data.notice_reason
    )


@routerAttendance.post("/class/{class_id}/qr")
def generate_class_attendance_qr(
    class_id: str,
    current_user=Depends(check_permission(["PROFESOR"]))
):
    frontend_public_url = os.getenv("FRONTEND_PUBLIC_URL")

    if not frontend_public_url:
        raise HTTPException(
            status_code=500,
            detail="Falta configurar FRONTEND_PUBLIC_URL."
        )

    return attendance_service.generate_attendance_qr(
        professor_id=current_user["id"],
        class_id=class_id,
        frontend_public_url=frontend_public_url
    )


@routerAttendance.post("/qr/register")
def register_attendance_from_qr(
    data: AttendanceByEmail
):
    return attendance_service.register_attendance_by_email(
        token=data.token,
        email=data.email
    )


@routerAttendance.patch("/class/{class_id}/qr/disable")
def disable_class_attendance_qr(
    class_id: str,
    current_user=Depends(check_permission(["PROFESOR"]))
):
    return attendance_service.disable_attendance_qr(
        professor_id=current_user["id"],
        class_id=class_id
    )




