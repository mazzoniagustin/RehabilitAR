from database import supabase
from fastapi import HTTPException
from datetime import datetime, timezone
from utils import benefits
#from services.mercadoPago_service import depositar_reserva #pendiente_de_implementar


def cancelar_reserva(reservation_id):
    try:
        if (reservation_id != None):
            reserva = supabase.table("reservations").select("*").eq("id", reservation_id).execute().data[0]
            clase = supabase.table("classes").select("start_time").eq("id", reserva["class_id"]).execute().data[0]
            user = supabase.table("users").select("*").eq("id", reserva["user_id"]).execute().data[0]
            start_time = datetime.fromisoformat(clase["start_time"])
            ahora = datetime.now(timezone.utc)
            diferencia_horas = (start_time - ahora).total_seconds() / 3600
            mensaje = "Reserva cancelada exitosamente."
            if (diferencia_horas >= 48):
                if (user["rol"] == "ABONADO"):
                    if (user["cancellation_amount"] < 2):
                        benefits.otorgar_credito(user["id"])
                        supabase.table("reservations").update({"status": "CANCELADA"}).eq("id", reservation_id).execute()
                        supabase.table("users").update({"cancellation_amount": user["cancellation_amount"] + 1}).eq("id", user["id"]).execute()
                        return {"message": mensaje}
                    else:
                        if (user["cancellation_amount"] == 2):
                            benefits.cancelar_descuentos(user["id"])
                            benefits.retirar_Todoscredito(user["id"])
                            mensaje = "Has alcanzado el límite de cancelaciones. Se han retirado tus créditos y descuentos"
                        supabase.table("reservations").update({"status": "CANCELADA"}).eq("id", reservation_id).execute()
                        supabase.table("users").update({"cancellation_amount": user["cancellation_amount"] + 1}).eq("id", user["id"]).execute()
                        return {"message": mensaje}
                else:
                    supabase.table("reservations").update({"status": "CANCELADA"}).eq("id", reservation_id).execute()
                    #depositar_reserva(reserva["amount_paid"], user["email"]) #pendiente_de_implementar   
                    return {"message": mensaje}
            elif (diferencia_horas >= 24) and (diferencia_horas < 48):
                if (user["rol"] == "ABONADO"):
                    if (user["cancellation_amount"] < 2):
                        if (user["cancellation_amount"] == 0):
                            benefits.otorgar_descuento20(user["id"])
                        else:
                            benefits.otorgar_descuento30(user["id"])
                        supabase.table("reservations").update({"status": "CANCELADA"}).eq("id", reservation_id).execute()
                        supabase.table("users").update({"cancellation_amount": user["cancellation_amount"] + 1}).eq("id", user["id"]).execute()
                        return {"message": mensaje}
                    else:
                        if (user["cancellation_amount"] == 2):
                            benefits.cancelar_descuentos(user["id"])
                            benefits.retirar_Todoscredito(user["id"])
                            mensaje = "Has alcanzado el límite de cancelaciones. Se han retirado tus créditos y descuentos"
                        supabase.table("reservations").update({"status": "CANCELADA"}).eq("id", reservation_id).execute()
                        supabase.table("users").update({"cancellation_amount": user["cancellation_amount"] + 1}).eq("id", user["id"]).execute()
                        return {"message": mensaje}
                else:
                    supabase.table("reservations").update({"status": "CANCELADA"}).eq("id", reservation_id).execute()
                    #depositar_reserva(reserva["amount_paid"], user["email"]) #pendiente_de_implementar   
                    return {"message": mensaje}
            else:
                supabase.table("reservations").update({"status": "no_show"}).eq("id", reservation_id).execute()
                raise HTTPException(status_code=400, detail={"message": "No puede obtener beneficio ya que canceló con menos de 48 horas de anticipación"})
        else:
            raise HTTPException(status_code=400, detail={"error": "El ID de la reserva es obligatorio para la cancelación."})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error de ID de reserva": str(e)})