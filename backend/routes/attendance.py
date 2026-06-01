from fastapi import APIRouter, Depends
from pydantic import BaseModel
from services.attendance_service import get_class_participants
from services.attendance_service import register_attendance
from utils.permissions import get_current_user


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







