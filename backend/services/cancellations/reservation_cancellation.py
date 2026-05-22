from database import supabase
from services.users_service import incrementar_cancellation_amount #pendiente_de_implementar
from services.mercadoPago_service import depositar_reserva #pendiente_de_implementar
import services.credits_service as credits_service #pendiente_de_implementar
import services.subscriptions_service as subscriptions_service #pendiente_de_implementar


def cancelar_reserva(reservation_id):
    try:
        if (reservation_id != None):
            reserva = supabase.table("reservations").select("*").eq("id", reservation_id).execute().data[0]
            clase = supabase.table("classes").select("start_time").eq("id", reserva["class_id"]).execute().data[0]
            user = supabase.table("users").select("*").eq("id", reserva["user_id"]).execute().data[0]
            credits = supabase.table("credits").select("*").eq("user_id", reserva["user_id"]).execute().data[0]
            start_time = datetime.fromisoformat(clase["start_time"])
            ahora = datetime.now(timezone.utc)
            diferencia_horas = (start_time - ahora).total_seconds() / 3600
            mensaje = "Reserva cancelada exitosamente."
            if (diferencia_horas >= 48):
                if (user["role"] == "ABONADO"):
                    if (user["cancellation_amount"] < 2):
                        credits_service.otorgar_credito(user["id"]) #pendiente_de_implementar
                        supabase.table("reservations").update({"status": "cancelled"}).eq("id", reservation_id).execute()
                        incrementar_cancellation_amount(user["id"]) #pendiente_de_implementar
                    else:
                        if (user["cancellation_amount"] == 2):
                            subscriptions_service.cancelar_descuentos(user["id"]) #pendiente_de_implementar
                            credits_service.retirar_credito(user["id"]) #pendiente_de_implementar
                            mensaje = "Has alcanzado el límite de cancelaciones. Se han retirado tus créditos y descuentos"
                        supabase.table("reservations").update({"status": "cancelled"}).eq("id", reservation_id).execute()
                        incrementar_cancellation_amount(user["id"]) #pendiente_de_implementar
                else:
                    supabase.table("reservations").update({"status": "cancelled"}).eq("id", reservation_id).execute()
                    depositar_reserva(reserva["amount_paid"], user["email"]) #pendiente_de_implementar   
                return {"message": mensaje}
            elif (diferencia_horas >= 24) and (diferencia_horas < 48):
                if (user["role"] == "ABONADO"):
                    if (user["cancellation_amount"] < 2):
                        if (user["cancellation_amount"] == 0):
                            subscriptions_service.otorgar_descuento20(user["id"]) #pendiente_de_implementar
                        else:
                            subscriptions_service.otorgar_descuento30(user["id"]) #pendiente_de_implementar
                        supabase.table("reservations").update({"status": "cancelled"}).eq("id", reservation_id).execute()
                        incrementar_cancellation_amount(user["id"]) #pendiente_de_implementar
                    else:
                        if (user["cancellation_amount"] == 2):
                            subscriptions_service.cancelar_descuentos(user["id"]) #pendiente_de_implementar
                            credits_service.retirar_credito(user["id"]) #pendiente_de_implementar
                            mensaje = "Has alcanzado el límite de cancelaciones. Se han retirado tus créditos y descuentos"
                        supabase.table("reservations").update({"status": "cancelled"}).eq("id", reservation_id).execute()
                        incrementar_cancellation_amount(user["id"]) #pendiente_de_implementar
                else:
                    supabase.table("reservations").update({"status": "cancelled"}).eq("id", reservation_id).execute()
                    depositar_reserva(reserva["amount_paid"], user["email"]) #pendiente_de_implementar   
                return {"message": mensaje}
            else:
                supabase.table("reservations").update({"status": "no_show"}).eq("id", reservation_id).execute()
                return {"message": "No puede obtener beneficio ya que canceló con menos de 48 horas de anticipación"}
        else:
            return {"error": "El ID de la reserva es obligatorio para la cancelación."}
    except Exception as e:
        return {"error de ID de reserva": str(e)}