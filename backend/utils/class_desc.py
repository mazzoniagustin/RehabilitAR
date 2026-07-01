from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TZ_AR = ZoneInfo('America/Argentina/Buenos_Aires')

_DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_class_datetime_ar(start_time_iso: str) -> str:
    dt = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
    dt_ar = _to_utc(dt).astimezone(TZ_AR)
    return f"{_DIAS[dt_ar.weekday()]} {dt_ar.strftime('%d/%m/%Y')} a las {dt_ar.strftime('%H:%M')}"


def build_class_desc(clase: dict) -> str:
    """
    Arma una descripción legible de la clase a partir de un dict que incluya
    activity_type, start_time y, opcionalmente, rooms.name (embed de Supabase).
    Ej: "TREN_SUPERIOR en Sala 1 el lunes 01/07/2026 a las 14:30"
    """
    activity = clase.get('activity_type', '') or ''
    room = (clase.get('rooms') or {}).get('name', '') if clase.get('rooms') else ''
    when = format_class_datetime_ar(clase['start_time']) if clase.get('start_time') else ''
    return ' '.join(filter(None, [activity, f'en {room}' if room else '', f'el {when}' if when else ''])).strip()
