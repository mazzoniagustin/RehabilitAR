import calendar
import collections
from datetime import datetime, timedelta, timezone

from database import supabase
from fastapi import HTTPException

def get_stats(year: int = None, month: int = None):
    try:
        date_filter_active = False
        start_date = None
        end_date = None
        
        if month and not year:
            year = datetime.now().year

        if year:
            date_filter_active = True
            if month:
                start_date = f"{year}-{month:02d}-01T00:00:00-03:00"
                last_day = calendar.monthrange(year, month)[1]
                end_date = f"{year}-{month:02d}-{last_day}T23:59:59-03:00"
            else:

                start_date = f"{year}-01-01T00:00:00-03:00"
                end_date = f"{year}-12-31T23:59:59-03:00"

        payments = supabase.table("payments").select("amount, status, payment_reason, paid_at")
        if date_filter_active:
            payments = payments.gte("paid_at", start_date).lte("paid_at", end_date)
        
        payments_list = payments.execute().data or []
        
        total_revenue = 0.0
        revenue = {"SUBSCRIPTION": 0.0, "RESERVATION": 0.0, "DEBT": 0.0, "OTHER": 0.0}
        revenue_by_month = collections.defaultdict(float)
        
        for payment in payments_list:
            amount_val = float(payment.get("amount") or 0.0)
            status_val = payment.get("status", "").strip()
            reason_val = payment.get("payment_reason", "").strip()
            paid_at_val = payment.get("paid_at")
            
            if status_val == "PAGADO":
                total_revenue += amount_val
                
                if reason_val == "SUBSCRIPTION":
                    revenue["SUBSCRIPTION"] += amount_val
                elif reason_val in ["RESERVATION_50", "RESERVATION_100"]:
                    revenue["RESERVATION"] += amount_val
                elif reason_val == "DEBT":
                    revenue["DEBT"] += amount_val
                else:
                    revenue["OTHER"] += amount_val

                if paid_at_val:
                    try:
                        clean_date = paid_at_val.replace("Z", "+00:00")
                        dt_utc = datetime.fromisoformat(clean_date)
                        if dt_utc.tzinfo is None:
                            dt_utc = dt_utc.replace(tzinfo=timezone.utc)

                        dt_arg = dt_utc.astimezone(timezone(timedelta(hours=-3)))
                        mes_clave = dt_arg.strftime("%Y-%m")
                        revenue_by_month[mes_clave] += amount_val
                    except Exception:

                        mes_clave = paid_at_val[:7]
                        revenue_by_month[mes_clave] += amount_val

        sorted_months = sorted(revenue_by_month.keys())
        chart_labels_revenue = sorted_months
        chart_data_revenue = [revenue_by_month[m] for m in sorted_months]

        reservations = supabase.table("reservations").select("status, created_at, classes(activity_type)")
        if date_filter_active:
            reservations = reservations.gte("created_at", start_date).lte("created_at", end_date)

        reservations_list = reservations.execute().data or []
        
        total_confirmed_or_absent = 0
        total_absences = 0
        activity_count = {"TREN_SUPERIOR": 0, "TREN_MEDIO": 0, "TREN_INFERIOR": 0}
        
        for res in reservations_list:
            status = res.get("status")
            class_data = res.get("classes") or {}
            act_type = class_data.get("activity_type")
            
            if status in ["CONFIRMADA", "AUSENTE"]:
                total_confirmed_or_absent += 1
                if status == "AUSENTE":
                    total_absences += 1
            
            if act_type in activity_count:
                activity_count[act_type] += 1
                
        absenteeism_rate = round((total_absences / total_confirmed_or_absent * 100), 2) if total_confirmed_or_absent > 0 else 0.0

        logs = supabase.table("user_status_history").select("reason, created_at, new_status, acted_by, user_id").order("created_at", desc=True)
        if date_filter_active:
            logs = logs.gte("created_at", start_date).lte("created_at", end_date)
        logs = logs.limit(10)
        logs_list = logs.execute().data or []
        
        user_ids = set(log.get("acted_by") for log in logs_list if log.get("acted_by"))
        user_ids.update(log.get("user_id") for log in logs_list if log.get("user_id"))
        
        users_map = {}
        if user_ids:
            users_res = supabase.table("users").select("id, name, surname").in_("id", list(user_ids)).execute()
            for u in (users_res.data or []):
                users_map[u["id"]] = f"{u['name']} {u['surname']}"

        track = []
        for log in logs_list:
            track.append({
                "date": log.get("created_at"),
                "actor": users_map.get(log.get("acted_by"), "Sistema"),
                "target": users_map.get(log.get("user_id"), "Usuario"),
                "action": log.get("new_status"),
                "reason": log.get("reason")
            })

        return {
            "financials": {
                "totalRevenue": total_revenue,
                "breakdown": revenue,
                "chartLabels": chart_labels_revenue if chart_labels_revenue else ["Sin Datos"],
                "chartData": chart_data_revenue if chart_data_revenue else [0]
            },
            "operations": {
                "absenteeismRate": absenteeism_rate,
                "activities": activity_count
            },
            "traceability": track
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener los datos: {str(e)}")
    
    
def get_user_stats(user_id: str):
    try:
        user_res = supabase.table("users").select(
            "id, name, surname, rol, account_status, absence_count, cancellation_count, specialty"
        ).eq("id", user_id).single().execute()
        if not user_res.data:
            raise HTTPException(status_code=404, detail="El usuario solicitado no fue encontrado.")
        user_data = user_res.data
        rol = user_data.get("rol")

        history_res = supabase.table("user_status_history")\
            .select("reason, created_at")\
            .eq("user_id", user_id)\
            .eq("new_status", "SUSPENDIDA")\
            .order("created_at", desc=True)\
            .execute()

        suspension_history = [
            {"reason": entry.get("reason"), "createdAt": entry.get("created_at")}
            for entry in (history_res.data or [])
        ]

        base = {
            "name": user_data.get("name"),
            "surname": user_data.get("surname"),
            "rol": rol,
            "accountStatus": user_data.get("account_status"),
            "totalSuspensions": len(suspension_history),
            "suspensionHistory": suspension_history,
        }

        if rol in ("ABONADO", "NO_ABONADO", "RECEPCIONISTA"):
            payments_res = supabase.table("payments").select("amount, status, payment_reason").eq("user_id", user_id).execute()
            total_paid = sum(float(p.get("amount") or 0) for p in (payments_res.data or []) if p.get("status") == "PAGADO")
            total_debt = sum(
                float(p.get("amount") or 0) for p in (payments_res.data or [])
                if p.get("status") == "PENDIENTE" and p.get("payment_reason") == "DEBT"
            )
            base.update({
                "absenceCount": user_data.get("absence_count") or 0,
                "cancellationCount": user_data.get("cancellation_count") or 0,
                "financials": {"totalPaid": total_paid, "totalDebt": total_debt},
            })

            if rol == "ABONADO":
                credits_res = supabase.table("credits").select("used_credits").eq("user_id", user_id).execute()
                used_credits = credits_res.data[0].get("used_credits") if credits_res.data else 0
                base["usedCredits"] = used_credits

        elif rol == "PROFESOR":
            classes_res = supabase.table("classes").select("id", count="exact").eq("professor_id", user_id).execute()
            base.update({
                "specialty": user_data.get("specialty"),
                "totalClasses": classes_res.count if classes_res.count is not None else 0,
            })

        return base

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener el historial del usuario: {str(e)}"
        )