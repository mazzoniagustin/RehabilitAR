import calendar
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from database import supabase
from fastapi import HTTPException


LOCAL_TZ = timezone(timedelta(hours=-3))

def get_stats(year: int = None, month: int = None):
    try:

        if not year:
            year = datetime.now().year

        if month:
            start_date = f'{year}-{month:02d}-01T00:00:00-03:00'
            last_day = calendar.monthrange(year, month)[1]
            end_date = f'{year}-{month:02d}-{last_day}T23:59:59-03:00'
        else:
            start_date = f'{year}-01-01T00:00:00-03:00'
            end_date = f'{year}-12-31T23:59:59-03:00'


        payments_list = (
            supabase.table('payments')
            .select('amount, status, payment_reason, paid_at')
            .gte('paid_at', start_date)
            .lte('paid_at', end_date)
            .execute()
            .data or []
        )

        total_revenue = 0.0
        revenue = {'SUBSCRIPTION': 0.0, 'RESERVATION': 0.0, 'DEBT': 0.0, 'OTHER': 0.0}
        revenue_by_month = {}

        for p in payments_list:
            if p.get('status') != 'PAGADO':
                continue

            amount = float(p.get('amount') or 0.0)
            total_revenue += amount

            reason = p.get('payment_reason', '')
            if 'RESERVATION' in reason:
                revenue['RESERVATION'] += amount
            elif reason in ['SUBSCRIPTION', 'DEBT']:
                revenue[reason] += amount
            else:
                revenue['OTHER'] += amount


            paid_at = p.get('paid_at')
            if paid_at:
                month_key = paid_at[:7]
                revenue_by_month[month_key] = revenue_by_month.get(month_key, 0.0) + amount

        sorted_months = sorted(revenue_by_month.keys())

        reservations_list = (
            supabase.table('reservations')
            .select('status, classes(activity_type)')
            .gte('created_at', start_date)
            .lte('created_at', end_date)
            .execute()
            .data or []
        )

        total_valid = 0
        total_absences = 0
        activities = {'TREN_SUPERIOR': 0, 'TREN_MEDIO': 0, 'TREN_INFERIOR': 0}

        for res in reservations_list:
            status = res.get('status')
            if status in ['CONFIRMADA', 'AUSENTE']:
                total_valid += 1
                if status == 'AUSENTE':
                    total_absences += 1

            act_type = (res.get('classes') or {}).get('activity_type')
            if act_type in activities:
                activities[act_type] += 1

        absenteeism = round((total_absences / total_valid * 100), 2) if total_valid > 0 else 0.0


        logs_list = (
            supabase.table('user_status_history')
            .select('reason, created_at, new_status, acted_by, user_id')
            .gte('created_at', start_date)
            .lte('created_at', end_date)
            .order('created_at', desc=True)
            .limit(10)
            .execute()
            .data or []
        )

        user_ids = list({log[k] for log in logs_list for k in ['acted_by', 'user_id'] if log.get(k)})
        users_map = {}

        if user_ids:
            users_res = supabase.table('users').select('id, name, surname').in_('id', user_ids).execute()
            users_map = {u['id']: f"{u['name']} {u['surname']}" for u in (users_res.data or [])}

        track = [
            {
                'date': log.get('created_at'),
                'actor': users_map.get(log.get('acted_by'), "Sistema"),
                'target': users_map.get(log.get('user_id'), "Usuario"),
                'action': log.get('new_status'),
                'reason': log.get('reason'),
            }
            for log in logs_list
        ]

        return {
            'financials': {
                'totalRevenue': total_revenue,
                'breakdown': revenue,
                'chartLabels': sorted_months if sorted_months else ["Sin Datos"],
                'chartData': [revenue_by_month[m] for m in sorted_months] if sorted_months else [0],
            },
            'operations': {
                'absenteeism': absenteeism,
                'activities': activities,
            },
            'traceability': track,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener los datos: {str(e)}")
    
def get_user_stats(user_id: str):
    try:
        user_res = supabase.table('users').select(
            'id, name, surname, rol, account_status, absence_count, cancellation_count, specialty'
        ).eq('id', user_id).single().execute()
        if not user_res.data:
            raise HTTPException(status_code=404, detail="El usuario solicitado no fue encontrado.")
        user_data = user_res.data
        rol = user_data.get('rol')

        history_res = supabase.table('user_status_history')\
            .select('reason, created_at')\
            .eq('user_id', user_id)\
            .eq('new_status', 'SUSPENDIDA')\
            .order('created_at', desc=True)\
            .execute()

        suspension_history = [
            {'reason': entry.get('reason'), 'createdAt': entry.get('created_at')}
            for entry in (history_res.data or [])
        ]

        base = {
            'name': user_data.get('name'),
            'surname': user_data.get('surname'),
            'rol': rol,
            'accountStatus': user_data.get('account_status'),
            'totalSuspensions': len(suspension_history),
            'suspensionHistory': suspension_history,
        }

        if rol in ('ABONADO', 'NO_ABONADO'):
            payments_res = supabase.table('payments').select('amount, status, payment_reason').eq('user_id', user_id).execute()
            total_paid = sum(float(p.get('amount') or 0) for p in (payments_res.data or []) if p.get('status') == 'PAGADO')
            total_debt = sum(
                float(p.get('amount') or 0) for p in (payments_res.data or [])
                if p.get('status') == 'PENDIENTE' and p.get('payment_reason') == 'DEBT'
            )
            base.update({
                'absenceCount': user_data.get('absence_count') or 0,
                'cancellationCount': user_data.get('cancellation_count') or 0,
                'financials': {'totalPaid': total_paid, 'totalDebt': total_debt},
            })

            credits_res = supabase.table('credits').select('used_credits').eq('user_id', user_id).execute()
            used_credits = credits_res.data[0].get('used_credits') if credits_res.data else 0
            base['usedCredits'] = used_credits

        elif rol == "PROFESOR":
            classes_res = supabase.table('classes').select('id', count='exact').eq('professor_id', user_id).execute()
            base.update({
                'specialty': user_data.get('specialty'),
                'totalClasses': classes_res.count if classes_res.count is not None else 0,
            })

        return base

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener el historial del usuario: {str(e)}"
        )