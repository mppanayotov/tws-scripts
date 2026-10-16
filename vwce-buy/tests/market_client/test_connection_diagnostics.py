import pytest

from vwce_buy.market_client import VwceMarketClient


def test_primary_connection_error_survives_cleanup_callbacks():
    client = VwceMarketClient(timeout=0.01)
    client.callbacks.error(-1, 0, 502, "Could not connect to PAPER TWS.")
    client.callbacks.connectionClosed()
    with pytest.raises(RuntimeError, match="502: Could not connect"):
        client._wait(client.callbacks.ready, -1, "TWS connection")
