"""The read-only ``vwce`` session and historical-price report."""

from __future__ import annotations

import argparse
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import json
import os
from zoneinfo import ZoneInfo

from .config import DESTINATION, ISIN, SYMBOL
from .contract import resolve
from .market_client import VwceMarketClient, discovery_contract, ibis2_contract
from .market_status import historical_medians, session_progress


def collect_status(client: VwceMarketClient, now: datetime | None = None) -> dict:
    resolved = resolve(client.get_contract_details(discovery_contract()))
    contract = ibis2_contract(resolved.con_id)
    matches = [
        detail
        for detail in client.get_contract_details(contract)
        if getattr(getattr(detail, "contract", None), "conId", None) == resolved.con_id
        and getattr(detail.contract, "exchange", None) == DESTINATION
        and getattr(detail.contract, "currency", None) == "EUR"
        and getattr(detail.contract, "secType", None) == "STK"
    ]
    if len(matches) != 1:
        raise ValueError("Could not uniquely verify the VWCE IBIS2 exchange schedule.")
    detail = matches[0]
    observed = now or datetime.now(timezone.utc)
    zone_name = getattr(detail, "timeZoneId", "")
    liquid_hours = getattr(detail, "liquidHours", "")
    progress = session_progress(
        zone_name if isinstance(zone_name, str) else "",
        liquid_hours if isinstance(liquid_hours, str) else "",
        observed,
    )
    errors = []
    report = {
        "symbol": SYMBOL,
        "isin": ISIN,
        "exchange": DESTINATION,
        "currency": "EUR",
        "as_of": observed.isoformat(),
        "session": {
            "state": progress.state,
            "phase": progress.phase,
            "time_zone": progress.time_zone,
            "windows": [
                [start.isoformat(), end.isoformat()] for start, end in progress.windows
            ],
            "elapsed_seconds": progress.elapsed_seconds,
            "total_seconds": progress.total_seconds,
            "progress_percent": None
            if progress.fraction is None
            else progress.fraction * 100,
            "next_open": progress.next_open.isoformat() if progress.next_open else None,
        },
        "history": None,
        "errors": errors,
    }
    if progress.state == "UNKNOWN":
        errors.append(
            "IBKR regular-hours schedule is missing, malformed, or does not cover today."
        )
    try:
        zone = ZoneInfo(progress.time_zone)
        local_today = observed.astimezone(zone).date()
        cutoff = (
            local_today
            if progress.phase == "AFTER_CLOSE"
            else local_today - timedelta(days=1)
        )
        end = min(
            observed, datetime.combine(cutoff + timedelta(days=1), time.min, zone)
        )
        medians = historical_medians(
            client.get_daily_bars(contract, end), completed_through=cutoff
        )
        report["history"] = {
            "source": "IBKR TRADES, regular trading hours, split-adjusted",
            "sessions": medians.count,
            "first_date": medians.first_date.isoformat(),
            "last_date": medians.last_date.isoformat(),
            "median_open_eur": str(medians.median_open),
            "median_close_eur": str(medians.median_close),
            "median_typical_eur": str(medians.median_typical),
            "typical_formula": "(high + low + close) / 3",
        }
    except (ValueError, RuntimeError, KeyError) as exc:
        errors.append(f"Historical medians unavailable: {exc}")
    return report


def _duration(seconds: float) -> str:
    minutes, second = divmod(int(seconds), 60)
    hour, minute = divmod(minutes, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def print_status(report: dict) -> None:
    session = report["session"]
    print(f"VWCE | {report['exchange']} | EUR")
    print(f"As of: {report['as_of']}")
    print(f"Session: {session['state']} ({session['phase'].replace('_', ' ').lower()})")
    windows = [
        f"{datetime.fromisoformat(start):%H:%M}-{datetime.fromisoformat(end):%H:%M}"
        for start, end in session["windows"]
    ]
    print(
        f"Trading window ({session['time_zone']}): {', '.join(windows) if windows else 'N/A'}"
    )
    if session["progress_percent"] is None:
        print("Daily progress: N/A (no verified trading window)")
    else:
        elapsed, total = session["elapsed_seconds"], session["total_seconds"]
        print(
            f"Daily progress: {session['progress_percent']:.1f}% | "
            f"{_duration(elapsed)} elapsed / {_duration(total)} total | "
            f"{_duration(total - elapsed)} remaining"
        )
    if session["next_open"]:
        print(f"Next window opens: {session['next_open']}")
    history = report["history"]
    if history is None:
        print("Historical medians (30 completed trading sessions): UNAVAILABLE")
    else:
        print(
            f"History: {history['sessions']} completed trading sessions, {history['first_date']} to {history['last_date']}"
        )
        print(f"Median open: EUR {Decimal(history['median_open_eur']):.2f}")
        print(f"Median close: EUR {Decimal(history['median_close_eur']):.2f}")
        print(
            f"Median typical price ((high + low + close) / 3): EUR {Decimal(history['median_typical_eur']):.2f}"
        )
        print(f"Data: {history['source']}")
    for error in report["errors"]:
        print(f"Unavailable: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vwce",
        description="Read-only VWCE IBIS2 session status and 30-session price medians.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print a structured status report."
    )
    parser.add_argument(
        "--client-id",
        type=int,
        help="Dedicated TWS API client ID (default: IBKR_STATUS_CLIENT_ID or 74).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20,
        help="Request timeout in seconds (default: 20).",
    )
    args = parser.parse_args(argv)
    try:
        client_id = (
            args.client_id
            if args.client_id is not None
            else int(os.getenv("IBKR_STATUS_CLIENT_ID", "74"))
        )
        with VwceMarketClient(
            os.getenv("IBKR_HOST", "127.0.0.1"),
            int(os.getenv("IBKR_PAPER_PORT", "7497")),
            client_id,
            args.timeout,
        ) as client:
            report = collect_status(client)
    except (ValueError, RuntimeError, OSError) as exc:
        report = {
            "symbol": SYMBOL,
            "exchange": DESTINATION,
            "currency": "EUR",
            "isin": ISIN,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "session": {
                "state": "UNKNOWN",
                "phase": "UNKNOWN",
                "time_zone": "unavailable",
                "windows": [],
                "elapsed_seconds": 0,
                "total_seconds": 0,
                "progress_percent": None,
                "next_open": None,
            },
            "history": None,
            "errors": [str(exc)],
        }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_status(report)
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
