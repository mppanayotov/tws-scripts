from decimal import Decimal
from types import SimpleNamespace
import pytest
from vwce_buy.contract import ResolvedContract
from vwce_buy.ibkr_client import PaperOrderClient
from vwce_buy.order import build_contract
from vwce_buy.paper_order import approve_paper_order, build_paper_order, require_paper_order_gate, validate_paper_order

def test_paper_order_submission_is_gated_exact_and_single_attempt(monkeypatch):
    monkeypatch.setenv("IBKR_RUN_PAPER_TESTS", "1"); monkeypatch.setenv("IBKR_RUN_PAPER_ORDER", "1")
    resolved = ResolvedContract(1, "VWCE", "VWCE", "IE00BK5BQT80", "EUR", "STK", ("IBIS2",)); contract = build_contract(resolved); order = build_paper_order("DU1234", Decimal("160.00"))
    kwargs = dict(account="DU1234", configured_account="DU1234", limit=Decimal("160.00"), increment=Decimal("0.02"), available_eur=Decimal("170.00"), resolved=resolved, contract=contract, order=order, session="OPEN", duplicate=False, host="127.0.0.1", port=7497, client_id=42, configured_limit="160.00")
    validate_paper_order(**kwargs); approved = approve_paper_order(**kwargs)
    for changed in ({"configured_limit": None}, {"host": "localhost"}, {"port": 7496}, {"client_id": 0}, {"configured_account": "DU9999"}, {"session": "CLOSED"}, {"session": "UNKNOWN"}, {"duplicate": True}, {"available_eur": Decimal("169.99")}, {"increment": Decimal("0.03")}, {"limit": Decimal("250.02")}):
        with pytest.raises(ValueError): validate_paper_order(**(kwargs | changed))
    for attribute, value in (("conId", 2), ("exchange", "SMART"), ("currency", "USD")):
        unsafe_contract = build_contract(resolved); setattr(unsafe_contract, attribute, value)
        with pytest.raises(ValueError): validate_paper_order(**(kwargs | {"contract": unsafe_contract}))
    for attribute, value in (("action", "SELL"), ("totalQuantity", 2), ("orderType", "MKT"), ("tif", "GTC"), ("outsideRth", True), ("whatIf", True), ("transmit", False)):
        unsafe_order = build_paper_order("DU1234", Decimal("160.00")); setattr(unsafe_order, attribute, value)
        with pytest.raises(ValueError): validate_paper_order(**(kwargs | {"order": unsafe_order}))
    require_paper_order_gate("DU1234", "160.00", "127.0.0.1", 7497, 42)
    client = PaperOrderClient("127.0.0.1", 7497, 42); client.callbacks.next_order_id = 100; called = []
    def place_order(order_id, *_):
        called.append(order_id); client.callbacks.orderStatus(order_id, "Submitted", 0, 1, 0, 1, 0, 0, 42, "", 0)
    monkeypatch.setattr(client._client, "placeOrder", place_order)
    result = client.submit_vwce_order(approved, timeout=0.01)
    assert result.order_id == 100 and result.status == "Submitted" and not result.is_filled and result.is_working and called == [100]
    retry = client.submit_vwce_order(approved, timeout=0.01)
    assert retry.order_id == 101 and called == [100, 101]
    client.callbacks.orderStatus(100, "Filled", 1, 0, 160, 7, 0, 160, 42, "", 0)
    client.callbacks.execDetails(-1, SimpleNamespace(), SimpleNamespace(orderId=100, execId="x", time="20260811 10:00:00", acctNumber="DU1234", side="BOT", shares=1, price=160, exchange="IBIS2", permId=7))
    update = client.callbacks.order_updates[100]
    assert update["status"] == "Filled" and client.callbacks.order_executions[100][0].execution_exchange == "IBIS2"
