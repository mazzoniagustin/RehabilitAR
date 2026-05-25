from database import supabase
from fastapi import HTTPException

def cancelar_suscripcion(user_id):
    try:
        if (user_id != None):
            user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
            if (user["rol"] == "ABONADO"):
                supabase.table("users").update({"rol": "NO_ABONADO"}).eq("id", user_id).execute()
                return {"message": "Suscripción cancelada exitosamente."}
            else:
                raise HTTPException(status_code=400, detail={"error": "El usuario no tiene una suscripción activa."})
        else:
            raise HTTPException(status_code=400, detail={"error": "El ID del usuario es obligatorio para la cancelación de la suscripción."})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error de ID de usuario": str(e)})