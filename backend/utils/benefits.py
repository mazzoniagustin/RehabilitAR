from database import supabase
from fastapi import HTTPException

def otorgar_credito(user_id: str):
    try:
        credito = supabase.table("credits").select("available_credits").eq("user_id", user_id).execute().data[0]
        supabase.table("credits").update({"available_credits": credito["available_credits"] + 1}).eq("user_id", user_id).execute()
        supabase.table("credits_history").insert({
            "user_id": user_id,
            "type": "CREDITO_OTORGADO",
            "reason": "Crédito otorgado por cancelación o cancelación de clase."
        }).execute()
        return {"message": "Crédito otorgado exitosamente."}
    except IndexError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al otorgar crédito: {str(e)}")

def retirar_credito(user_id: str):
    try:
        credito = supabase.table("credits").select("available_credits").eq("user_id", user_id).execute().data[0]
        if credito["available_credits"] > 0:
            supabase.table("credits").update({"available_credits": credito["available_credits"] - 1}).eq("user_id", user_id).execute()
            supabase.table("credits_history").insert({
                "user_id": user_id,
                "type": "CREDITO_RETIRADO",
                "reason": "Crédito utilizado por el usuario."
            }).execute()
            return {"message": "Crédito retirado exitosamente."}
        else:
            raise HTTPException(status_code=400, detail="No hay créditos disponibles para retirar.")
    except IndexError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al retirar crédito: {str(e)}")

def retirar_Todoscredito(user_id: str):
    try:
        credito = supabase.table("credits").select("available_credits").eq("user_id", user_id).execute().data[0]
        if credito["available_credits"] > 0:
            supabase.table("credits").update({"available_credits": 0}).eq("user_id", user_id).execute()
            supabase.table("credits_history").insert({
                "user_id": user_id,
                "type": "CREDITOS_RETIRADOS_TODOS",
                "reason": "Todos los créditos retirados por alcanzar el límite de cancelaciones."
            }).execute()
            return {"message": "Créditos retirados exitosamente."}
        else:
            raise HTTPException(status_code=400, detail="No hay créditos disponibles para retirar.")
    except IndexError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al retirar crédito: {str(e)}")
    
def otorgar_descuento20(user_id: str):
    try:
        supabase.table("subscriptions").update({"discount_percentage": 20}).eq("user_id", user_id).execute()
        return {"message": "Descuento del 20% otorgado exitosamente."}
    except IndexError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al otorgar descuento: {str(e)}")

def otorgar_descuento30(user_id: str):
    try:
        supabase.table("subscriptions").update({"discount_percentage": 30}).eq("user_id", user_id).execute()
        return {"message": "Descuento del 30% otorgado exitosamente."}
    except IndexError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al otorgar descuento: {str(e)}")
    
def cancelar_descuentos(user_id: str):
    try:
        supabase.table("subscriptions").update({"discount_percentage": 0}).eq("user_id", user_id).execute()
        return {"message": "Descuentos cancelados exitosamente."}
    except IndexError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cancelar descuentos: {str(e)}")