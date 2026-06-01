from fastapi import HTTPException
from database import supabase

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
        .execute()

    if not reservation_res.data:
        raise HTTPException(status_code=404, detail="La reserva no corresponde a esta clase.")
    
    attendance_data = {
        "class_id": class_id,
        "user_id": user_id,
        "reservation_id": reservation_id,
        "status": status,
        "comment": comment,
        "marked_by": professor_id
    }

    response = supabase.table("attendance") \
        .upsert(attendance_data, on_conflict="class_id,user_id") \
        .execute()
    
    return response.data[0]











