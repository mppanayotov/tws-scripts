from decimal import Decimal
from types import SimpleNamespace
import pytest
from vwce_buy.contract import ResolvedContract
from vwce_buy.ibkr_client import PaperOrderClient
from vwce_buy.order import build_contract
from vwce_buy.paper_order import build_paper_order, require_paper_confirmation, require_paper_order_gate, validate_paper_order

def test_paper_order_gate_confirmation_and_invariants_prevent_unsafe_submission(monkeypatch):
    resolved = ResolvedContract(1, "VWCE", "VWCE", "IE00BK5BQT80", "EUR", "STK", ("IBIS2",)); contract = build_contract(resolved); order = build_paper_order("DU1234", Decimal("160.00"))
    with pytest.raises(ValueError): require_paper_order_gate(None, "127.0.0.1", 7497, 42)
    with pytest.raises(ValueError): require_paper_confirmation(Decimal("160.00"), "bad")
    validate_paper_order("DU1234", resolved, contract, order, "OPEN", False)
    order.action = "SELL"
    with pytest.raises(ValueError): validate_paper_order("DU1234", resolved, contract, order, "OPEN", False)
    client = PaperOrderClient("127.0.0.1", 7497, 42); called=[]; monkeypatch.setattr(client._client, "placeOrder", lambda *args: called.append(args)); order.whatIf = True
    with pytest.raises(ValueError): client._send_paper_order(1, contract, order)
    assert not called
