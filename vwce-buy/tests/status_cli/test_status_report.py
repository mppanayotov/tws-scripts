from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from vwce_buy import status_cli
from vwce_buy.config import ISIN


def test_completed_sessions_schedule_and_partial_history_are_visible():
    today = date(2026, 10, 15)
    trading_days = []
    day = today - timedelta(days=1)
    while len(trading_days) < 31:
        if day.weekday() < 5:
            trading_days.append(day)
        day -= timedelta(days=1)
    trading_days.reverse()
    trading_days.append(today)
    bars = [
        SimpleNamespace(
            date=day.strftime("%Y%m%d"),
            open=str(index + 100),
            low=str(index + 98),
            high=str(index + 104),
            close=str(index + 102),
        )
        for index, day in enumerate(trading_days)
    ]
    discovered = SimpleNamespace(
        contract=SimpleNamespace(
            conId=123, symbol="VWCE", localSymbol="VWCE", secType="STK", currency="EUR"
        ),
        secIdList=[SimpleNamespace(tag="ISIN", value=ISIN)],
        validExchanges="SMART,IBIS2",
    )
    exchange = SimpleNamespace(
        contract=SimpleNamespace(
            conId=123, exchange="IBIS2", currency="EUR", secType="STK"
        ),
        timeZoneId="Europe/Berlin",
        liquidHours="20261015:0900-1700",
    )

    class Broker:
        def __init__(self):
            self.requests = []
            self.permission_error = False

        def get_contract_details(self, contract):
            self.requests.append(("details", contract))
            return [discovered] if contract.exchange == "SMART" else [exchange]

        def get_daily_bars(self, contract, end):
            self.requests.append(("bars", contract, end))
            if self.permission_error:
                raise RuntimeError("IBKR 162: no historical data permission")
            return bars

    broker = Broker()
    open_report = status_cli.collect_status(
        broker, datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    )
    assert (open_report["session"]["state"], open_report["session"]["phase"]) == (
        "OPEN",
        "OPEN",
    )
    assert open_report["session"]["progress_percent"] == 62.5
    assert open_report["history"]["sessions"] == 30
    assert open_report["history"]["last_date"] == trading_days[-2].isoformat()
    assert open_report["history"]["median_open_eur"] == "115.5"
    assert open_report["history"]["median_close_eur"] == "117.5"
    assert abs(
        Decimal(open_report["history"]["median_typical_eur"])
        - (Decimal("15.5") + Decimal(304) / 3)
    ) < Decimal("0.000000000000000000000001")
    assert broker.requests[0][1].secId == ISIN
    assert broker.requests[0][1].exchange == "SMART"
    assert broker.requests[1][1].exchange == "IBIS2"
    assert broker.requests[2][1].exchange == "IBIS2"
    assert broker.requests[2][2].date() == today

    closed_report = status_cli.collect_status(
        broker, datetime(2026, 10, 15, 16, tzinfo=timezone.utc)
    )
    assert closed_report["session"]["phase"] == "AFTER_CLOSE"
    assert closed_report["history"]["last_date"] == today.isoformat()
    assert closed_report["history"]["median_open_eur"] == "116.5"

    broker.permission_error = True
    partial = status_cli.collect_status(
        broker, datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    )
    assert partial["session"]["state"] == "OPEN"
    assert partial["history"] is None
    assert "permission" in partial["errors"][0]

    broker.permission_error = False
    exchange.liquidHours = ""
    unknown = status_cli.collect_status(
        broker, datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    )
    assert unknown["session"]["state"] == "UNKNOWN"
    assert "schedule" in unknown["errors"][0]
