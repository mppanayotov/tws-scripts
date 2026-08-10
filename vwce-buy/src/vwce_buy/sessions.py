from datetime import datetime
from zoneinfo import ZoneInfo

def session_state(time_zone_id: str, hours: str, now: datetime) -> str:
    """Return OPEN, CLOSED, or UNKNOWN for IBKR's date:HHMM-HHMM schedule format."""
    try:
        local_now = now.astimezone(ZoneInfo(time_zone_id))
        entries = [entry.strip() for entry in hours.split(";") if entry.strip()]
        if not entries or any("CLOSED" in entry.upper() for entry in entries):
            return "CLOSED"
        for entry in entries:
            date_text, span = entry.split(":", 1)
            start_text, end_text = span.split("-", 1)
            start = datetime.strptime(date_text + start_text, "%Y%m%d%H%M").replace(tzinfo=ZoneInfo(time_zone_id))
            end_parts = end_text.split(":")
            end_date, end_clock = (end_parts[0], end_parts[1]) if len(end_parts) == 2 else (date_text, end_text)
            end = datetime.strptime(end_date + end_clock, "%Y%m%d%H%M").replace(tzinfo=ZoneInfo(time_zone_id))
            if start <= local_now <= end: return "OPEN"
        return "CLOSED"
    except Exception:
        return "UNKNOWN"
