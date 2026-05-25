from database import supabase
from datetime import datetime, timezone
from fastapi import HTTPException
from services.classes_service import cancel_class
#from services.credits_service import otorgar_credito #pendiente_de_implementar

def cancelar_clase(class_id, cancel_reason):
    try:
        if (cancel_reason is None) or (cancel_reason == ""):
            raise HTTPException(status_code=400, detail="La razón de cancelación es obligatoria.")
        cancel_class(class_id)
        supabase.table("classes").update({"cancellation_reason": cancel_reason}).eq("id", class_id).execute()
        reservas = supabase.table("reservations").select("*").eq("class_id", class_id).eq("status", "CONFIRMADA").execute()
        for reserva in reservas.data:
            supabase.table("reservations").update({"status": "CANCELADA"}).eq("id", reserva["id"]).execute()
            #otorgar_credito(reserva["user_id"], reserva["class_id"]) #pendiente_de_implementar
        return {"message": "Clase cancelada exitosamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cancelar la clase: {str(e)}")

def cancelacion_automatica(class_id):
    try:
        if class_id is None:
            raise HTTPException(status_code=400, detail="El ID de la clase es obligatorio para la cancelación automática.")
        clase = supabase.table("classes").select("professor_id, start_time").eq("id", class_id).execute().data[0]
        start_time = datetime.fromisoformat(clase["start_time"])
        ahora = datetime.now(timezone.utc)
        diferencia_horas = (start_time - ahora).total_seconds() / 3600
        if (clase["professor_id"] is None) and (diferencia_horas <= 12):
            cancel_class(class_id)
            supabase.table("classes").update({"cancellation_reason": "Cancelación automática por falta de profesor"}).eq("id", class_id).execute()
            reservas = supabase.table("reservations").select("*").eq("class_id", class_id).eq("status", "CONFIRMADA").execute()
            for reserva in reservas.data:
                supabase.table("reservations").update({"status": "CANCELADA"}).eq("id", reserva["id"]).execute()
                #otorgar_credito(reserva["user_id"], reserva["class_id"]) #pendiente_de_implementar
            return {"message": "Clase cancelada automáticamente por falta de profesor."}
        return {"message": "No se cumplen las condiciones para cancelar la clase automáticamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cancelar la clase: {str(e)}")