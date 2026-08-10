from decimal import Decimal
from types import SimpleNamespace
import pytest
from vwce_buy.contract import ResolvedContract
from vwce_buy.ibkr_client import PaperWhatIfClient
from vwce_buy.order import build_contract
from vwce_buy.whatif import build_whatif_order, require_tick_aligned, require_whatif_gate, tick_increment, validate_whatif

def test_whatif_invariants_tick_and_non_whatif_orders_cannot_reach_place_order(monkeypatch):
    resolved = ResolvedContract(1, "VWCE", "VWCE", "IE00BK5BQT80", "EUR", "STK", ("IBIS2",)); contract = build_contract(resolved); order = build_whatif_order("DU1234", Decimal("168.60"))
    validate_whatif("DU1234", contract, order)
    assert tick_increment(Decimal("168.60"), [SimpleNamespace(lowEdge=0, increment=0.02)]) == Decimal("0.02")
    with pytest.raises(ValueError): require_tick_aligned(Decimal("168.61"), Decimal("0.02"))
    contract.exchange = "SMART"
    with pytest.raises(ValueError): validate_whatif("DU1234", contract, order)
    client = PaperWhatIfClient("127.0.0.1", 7497, 42); called = []
    monkeypatch.setattr(client._client, "placeOrder", lambda *args: called.append(args))
    order.whatIf = False
    with pytest.raises(ValueError): client._send_whatif(1, build_contract(resolved), order)
    assert not called
    with pytest.raises(ValueError): require_whatif_gate(None, "127.0.0.1", 7497, 42)
