from datetime import datetime, timezone

import pytest

from vwce_buy import market_client


@pytest.mark.parametrize("outcome", ["complete", "permission", "timeout"])
def test_finite_ibkr_history_request_and_failure_cleanup(monkeypatch, outcome):
    calls = []

    class FakeClient:
        def __init__(self, callbacks):
            self.callbacks = callbacks

        def connect(self, *args):
            calls.append(("connect", args))
            self.callbacks.nextValidId(1)

        def run(self):
            pass

        def disconnect(self):
            calls.append(("disconnect",))

        def reqHistoricalData(self, *args):
            calls.append(("history", args))
            request = args[0]
            self.callbacks.historicalData(request, object())
            if outcome == "complete":
                self.callbacks.historicalDataEnd(request, "", "")
            elif outcome == "permission":
                self.callbacks.error(request, 0, 162, "No historical data permission")

        def cancelHistoricalData(self, request):
            calls.append(("cancel", request))

        def __getattr__(self, name):
            if name in {
                "placeOrder",
                "reqMktData",
                "reqAccountUpdates",
                "reqPositions",
            }:
                raise AssertionError(f"Unexpected broker operation: {name}")
            raise AttributeError(name)

    monkeypatch.setattr(market_client, "EClient", FakeClient)
    with market_client.VwceMarketClient(timeout=0.01) as client:
        contract = market_client.ibis2_contract(123)
        end = datetime(2026, 10, 15, 17, tzinfo=timezone.utc)
        if outcome == "complete":
            assert len(client.get_daily_bars(contract, end)) == 1
        else:
            with pytest.raises(RuntimeError, match="permission|Timed out"):
                client.get_daily_bars(contract, end)

    request = next(args for name, args in calls if name == "history")
    assert request[1] is contract
    assert request[2:] == (
        "20261015-17:00:00",
        "3 M",
        "1 day",
        "TRADES",
        1,
        1,
        False,
        [],
    )
    assert [name for name, *_ in calls].count("cancel") == (outcome != "complete")
    assert calls[-1] == ("disconnect",)
