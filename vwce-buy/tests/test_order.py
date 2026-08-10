from decimal import Decimal
from vwce_buy.contract import ResolvedContract
from vwce_buy.order import build_contract, build_order

def test_order_and_contract_are_immutable_invariants():
    resolved = ResolvedContract(1, "VWCE", "VWCE", "IE00BK5BQT80", "EUR", "STK", ("IBIS2",))
    contract, order = build_contract(resolved), build_order("U1234", Decimal("168.60"))
    assert (contract.exchange, order.action, order.totalQuantity, order.orderType, order.tif, order.outsideRth) == ("IBIS2", "BUY", 1, "LMT", "DAY", False)
