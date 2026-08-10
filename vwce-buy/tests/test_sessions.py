from datetime import datetime, timezone
from vwce_buy.sessions import session_state

def test_session_parser_fails_closed_for_closed_and_malformed_schedules():
    now = datetime(2026, 8, 10, 10, tzinfo=timezone.utc)
    assert session_state("Europe/Berlin", "20260810:0900-20260810:1730", now) == "OPEN"
    assert session_state("Europe/Berlin", "20260810:CLOSED", now) == "CLOSED"
    assert session_state("Europe/Berlin", "broken", now) == "UNKNOWN"
