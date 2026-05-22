from database import supabase
from services.credits_service import otorgar_credito #pendiente_de_implementar

def cancelar_clase(class_id, cancel_reason):
    try:
        if (cancel_reason == None) or (cancel_reason == ""):
            return {"error": "La razón de cancelación es obligatoria."}
        else:
            supabase.table("classes").update({"status": "cancelled", "cancellation_reason": cancel_reason}).eq("id", class_id).execute()
            reservas = supabase.table("reservations").select("*").eq("class_id", class_id).eq("status", "active").execute()
            for reserva in reservas.data:
                supabase.table("reservations").update({"status": "cancelled"}).eq("id", reserva["id"]).execute()
                otorgar_credito(reserva["user_id"], reserva["class_id"]) #pendiente_de_implementar
            return {"message": "Clase cancelada exitosamente."}
    except Exception as e:
        return {"error de motivo de cancelación": str(e)}

def cancelación_automática(class_id):
    try:
        if (class_id != None):
            clase = supabase.table("classes").select("professor_id, start_time").eq("id", class_id).execute().data[0]
            start_time = datetime.fromisoformat(clase["start_time"])
            ahora = datetime.now(timezone.utc)
            diferencia_horas = (start_time - ahora).total_seconds() / 3600
            if (clase["professor_id"] is None) and (diferencia_horas <= 12):
                supabase.table("classes").update({"status": "cancelled", "cancellation_reason": "Cancelación automática por falta de profesor"}).eq("id", class_id).execute()
                reservas = supabase.table("reservations").select("*").eq("class_id", class_id).eq("status", "active").execute()
                for reserva in reservas.data:
                    supabase.table("reservations").update({"status": "cancelled"}).eq("id", reserva["id"]).execute()
                    otorgar_credito(reserva["user_id"], reserva["class_id"]) #pendiente_de_implementar
                return {"message": "Clase cancelada automáticamente por falta de profesor."}
        else:
            return {"error": "El ID de la clase es obligatorio para la cancelación automática."}
    except Exception as e:
        return {"error de ID": str(e)}