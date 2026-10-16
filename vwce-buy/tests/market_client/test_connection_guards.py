import pytest

from vwce_buy import market_client


def test_connection_failure_disconnects_and_status_settings_reject_unsafe_values(
    monkeypatch,
):
    calls = []

    class FailingClient:
        def __init__(self, callbacks):
            self.callbacks = callbacks

        def connect(self, *args):
            calls.append("connect")
            raise OSError("connection refused")

        def disconnect(self):
            calls.append("disconnect")

    monkeypatch.setattr(market_client, "EClient", FailingClient)
    with pytest.raises(OSError, match="connection refused"):
        with market_client.VwceMarketClient():
            pass
    assert calls == ["connect", "disconnect"]

    for args in [
        {"host": "remote.example"},
        {"port": 7496},
        {"client_id": 0},
        {"timeout": 0},
        {"timeout": 121},
    ]:
        with pytest.raises(ValueError):
            market_client.VwceMarketClient(**args)
    with pytest.raises(ValueError, match="time zone"):
        market_client.VwceMarketClient().get_daily_bars(
            market_client.ibis2_contract(123),
            __import__("datetime").datetime(2026, 10, 15),
        )
