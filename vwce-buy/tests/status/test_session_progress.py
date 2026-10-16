from datetime import datetime, timezone

import pytest

from vwce_buy.market_status import session_progress


@pytest.mark.parametrize(
    ("hours", "now", "state", "phase", "fraction", "next_hour"),
    [
        (
            "20260810:0900-1700",
            datetime(2026, 8, 10, 6, tzinfo=timezone.utc),
            "CLOSED",
            "BEFORE_OPEN",
            0,
            9,
        ),
        (
            "20260810:0900-1700",
            datetime(2026, 8, 10, 11, tzinfo=timezone.utc),
            "OPEN",
            "OPEN",
            0.5,
            None,
        ),
        (
            "20260810:0900-1700",
            datetime(2026, 8, 10, 15, tzinfo=timezone.utc),
            "CLOSED",
            "AFTER_CLOSE",
            1,
            None,
        ),
        (
            "20260810:0900-20260810:1700",
            datetime(2026, 8, 10, 11, tzinfo=timezone.utc),
            "OPEN",
            "OPEN",
            0.5,
            None,
        ),
        (
            "20260810:0900-1200,1300-1700",
            datetime(2026, 8, 10, 10, tzinfo=timezone.utc),
            "CLOSED",
            "BREAK",
            3 / 7,
            13,
        ),
        (
            "20260810:0900-1200,1300-1700",
            datetime(2026, 8, 10, 12, tzinfo=timezone.utc),
            "OPEN",
            "OPEN",
            4 / 7,
            None,
        ),
        (
            "20260810:0900-1700;20260811:CLOSED",
            datetime(2026, 8, 10, 11, tzinfo=timezone.utc),
            "OPEN",
            "OPEN",
            0.5,
            None,
        ),
        (
            "20260810:0900-1700;20260811:CLOSED",
            datetime(2026, 8, 11, 11, tzinfo=timezone.utc),
            "CLOSED",
            "NON_TRADING",
            None,
            None,
        ),
        (
            "20260811:0900-1700",
            datetime(2026, 8, 10, 11, tzinfo=timezone.utc),
            "UNKNOWN",
            "UNKNOWN",
            None,
            None,
        ),
        (
            "20260810:0900-1200,1100-1700",
            datetime(2026, 8, 10, 11, tzinfo=timezone.utc),
            "UNKNOWN",
            "UNKNOWN",
            None,
            None,
        ),
        (
            "20260810:bogus",
            datetime(2026, 8, 10, 11, tzinfo=timezone.utc),
            "UNKNOWN",
            "UNKNOWN",
            None,
            None,
        ),
        (
            "20260810:0900-1700",
            datetime(2026, 8, 10, 11),
            "UNKNOWN",
            "UNKNOWN",
            None,
            None,
        ),
        (
            "20260810:0900-1700;20260810:CLOSED",
            datetime(2026, 8, 10, 11, tzinfo=timezone.utc),
            "UNKNOWN",
            "UNKNOWN",
            None,
            None,
        ),
        (
            "20261024:2200-20261025:0400",
            datetime(2026, 10, 25, 0, tzinfo=timezone.utc),
            "OPEN",
            "OPEN",
            4 / 7,
            None,
        ),
    ],
)
def test_session_progress_boundaries(hours, now, state, phase, fraction, next_hour):
    result = session_progress("Europe/Berlin", hours, now)
    assert (result.state, result.phase, result.time_zone) == (
        state,
        phase,
        "Europe/Berlin",
    )
    if fraction is None:
        assert result.fraction is None
    else:
        assert result.fraction == pytest.approx(fraction)
    assert (
        result.next_open.hour if result.next_open is not None else None
    ) == next_hour
    if phase == "OPEN":
        assert 0 <= result.elapsed_seconds <= result.total_seconds
    assert session_progress("Missing/Zone", hours, now).state == "UNKNOWN"
