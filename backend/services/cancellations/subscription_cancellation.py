from database import supabase
from services.users_service import incrementar_cancellation_amount #pendiente_de_implementar

def cancelar_suscripcion(user_id):
    try:
        if (user_id != None):
            user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
            if (user["role"] == "ABONADO"):
                supabase.table("users").update({"role": "NO_ABONADO"}).eq("id", user_id).execute()
                return {"message": "Suscripción cancelada exitosamente."}
            else:
                return {"error": "El usuario no tiene una suscripción activa."}
        else:
            return {"error": "El ID del usuario es obligatorio para la cancelación de la suscripción."}
    except Exception as e:
        return {"error de ID de usuario": str(e)}