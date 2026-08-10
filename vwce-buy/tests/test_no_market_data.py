from vwce_buy.ibkr_client import ReadOnlyPaperClient

def test_read_only_client_contains_no_market_data_or_order_submission_calls(monkeypatch):
    forbidden = ["reqMktData", "reqHistoricalData", "reqRealTimeBars", "reqTickByTickData", "placeOrder", "cancelOrder", "reqOpenOrders", "reqAutoOpenOrders"]
    client = ReadOnlyPaperClient("127.0.0.1", 7497, 71)
    for name in forbidden:
        monkeypatch.setattr(client._client, name, lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError(name)))
    monkeypatch.setattr(client._client, "reqAllOpenOrders", client.callbacks.openOrderEnd)
    assert client.get_open_orders(timeout=0.01) == []
    assert client.callbacks.store.open_orders == []
