"""Pure calculations for exchange session progress and historical VWCE prices."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from statistics import median
from typing import Sequence
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class SessionProgress:
    state: str
    phase: str
    time_zone: str
    windows: tuple[tuple[datetime, datetime], ...]
    elapsed_seconds: float
    total_seconds: float
    fraction: float | None
    next_open: datetime | None


@dataclass(frozen=True)
class PriceMedians:
    count: int
    first_date: date
    last_date: date
    median_open: Decimal
    median_close: Decimal
    median_typical: Decimal


_ENTRY = re.compile(r"(?P<day>\d{8}):(?P<spans>.+)")
_SPAN = re.compile(
    r"(?:(?P<start_day>\d{8}):)?(?P<start>\d{4})-(?:(?P<end_day>\d{8}):)?(?P<end>\d{4})"
)


def _local_time(day_text: str, clock_text: str, zone: ZoneInfo) -> datetime:
    local = datetime.strptime(day_text + clock_text, "%Y%m%d%H%M").replace(tzinfo=zone)
    if (
        local.astimezone(timezone.utc).astimezone(zone).replace(fold=local.fold)
        != local
    ):
        raise ValueError("schedule contains a nonexistent local time")
    return local


def _seconds(start: datetime, end: datetime) -> float:
    return (
        end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
    ).total_seconds()


def _unknown(time_zone_id: str) -> SessionProgress:
    return SessionProgress("UNKNOWN", "UNKNOWN", time_zone_id, (), 0.0, 0.0, None, None)


def session_progress(time_zone_id: str, hours: str, now: datetime) -> SessionProgress:
    """Interpret IBKR dated trading windows using half-open intervals."""
    try:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        zone = ZoneInfo(time_zone_id)
        local_now = now.astimezone(zone)
        if not hours or not hours.strip():
            raise ValueError("empty trading schedule")

        by_day: dict[date, list[tuple[datetime, datetime]]] = {}
        closed_days: set[date] = set()
        for raw_entry in hours.split(";"):
            entry = raw_entry.strip()
            match = _ENTRY.fullmatch(entry)
            if match is None:
                raise ValueError("malformed schedule entry")
            day_text = match.group("day")
            day = datetime.strptime(day_text, "%Y%m%d").date()
            spans_text = match.group("spans")
            if spans_text == "CLOSED":
                if day in by_day or day in closed_days:
                    raise ValueError("duplicate schedule date")
                closed_days.add(day)
                continue
            if day in closed_days:
                raise ValueError("closed date has trading windows")
            windows = by_day.setdefault(day, [])
            for raw_span in spans_text.split(","):
                span = _SPAN.fullmatch(raw_span.strip())
                if span is None:
                    raise ValueError("malformed trading window")
                start_day = span.group("start_day") or day_text
                end_day = span.group("end_day") or day_text
                if start_day != day_text:
                    raise ValueError("trading window starts on another schedule date")
                start = _local_time(start_day, span.group("start"), zone)
                end = _local_time(end_day, span.group("end"), zone)
                if _seconds(start, end) <= 0:
                    raise ValueError("trading window has nonpositive duration")
                windows.append((start, end))

        all_windows = sorted(
            (window for day_windows in by_day.values() for window in day_windows),
            key=lambda window: window[0].astimezone(timezone.utc),
        )
        for previous, following in zip(all_windows, all_windows[1:]):
            if _seconds(previous[1], following[0]) < 0:
                raise ValueError("overlapping trading windows")

        current_day = local_now.date()
        now_utc = local_now.astimezone(timezone.utc)
        active_previous = [
            day
            for day, windows in by_day.items()
            if day < current_day
            and any(
                start.astimezone(timezone.utc) <= now_utc < end.astimezone(timezone.utc)
                for start, end in windows
            )
        ]
        session_day = active_previous[0] if active_previous else current_day
        if session_day in closed_days:
            return SessionProgress(
                "CLOSED", "NON_TRADING", time_zone_id, (), 0.0, 0.0, None, None
            )
        if session_day not in by_day:
            return _unknown(time_zone_id)
        windows = tuple(
            sorted(
                by_day[session_day],
                key=lambda window: window[0].astimezone(timezone.utc),
            )
        )
        total = sum(_seconds(start, end) for start, end in windows)
        elapsed = sum(
            max(0.0, min(_seconds(start, local_now), _seconds(start, end)))
            for start, end in windows
        )
        next_open = next(
            (start for start, _ in windows if _seconds(local_now, start) > 0), None
        )
        if any(
            _seconds(start, local_now) >= 0 and _seconds(local_now, end) > 0
            for start, end in windows
        ):
            phase, state = "OPEN", "OPEN"
        elif next_open is not None:
            phase = "BEFORE_OPEN" if next_open == windows[0][0] else "BREAK"
            state = "CLOSED"
        else:
            phase, state = "AFTER_CLOSE", "CLOSED"
        return SessionProgress(
            state,
            phase,
            time_zone_id,
            windows,
            elapsed,
            total,
            elapsed / total,
            next_open,
        )
    except (AttributeError, TypeError, ValueError, OverflowError, KeyError):
        return _unknown(time_zone_id)


def historical_medians(
    bars: Sequence[object], *, completed_through: date, count: int = 30
) -> PriceMedians:
    """Return exact medians for the latest completed, unique trading dates."""
    if count <= 0:
        raise ValueError("count must be positive")
    selected: dict[date, tuple[Decimal, Decimal, Decimal]] = {}
    for bar in bars:
        try:
            day_text = bar.date
            if (
                not isinstance(day_text, str)
                or re.fullmatch(r"\d{8}", day_text) is None
            ):
                raise ValueError("bar date must be YYYYMMDD")
            day = datetime.strptime(day_text, "%Y%m%d").date()
            if day > completed_through:
                continue
            if day in selected:
                raise ValueError(f"duplicate completed trading date: {day}")
            values = tuple(
                Decimal(str(getattr(bar, field)))
                for field in ("open", "high", "low", "close")
            )
            opening, high, low, close = values
            if any(not value.is_finite() or value <= 0 for value in values):
                raise ValueError(f"invalid OHLC values for {day}")
            if low > min(opening, close) or high < max(opening, close) or high < low:
                raise ValueError(f"inconsistent OHLC bounds for {day}")
            selected[day] = (opening, close, (high + low + close) / Decimal(3))
        except (AttributeError, InvalidOperation, TypeError) as exc:
            raise ValueError("invalid historical bar") from exc
    if len(selected) < count:
        raise ValueError(
            f"need {count} completed trading sessions; got {len(selected)}"
        )
    recent_days = sorted(selected)[-count:]
    return PriceMedians(
        count,
        recent_days[0],
        recent_days[-1],
        median(selected[day][0] for day in recent_days),
        median(selected[day][1] for day in recent_days),
        median(selected[day][2] for day in recent_days),
    )
