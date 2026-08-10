from types import SimpleNamespace
from vwce_buy.open_orders import has_active_vwce_buy
from vwce_buy.positions import vwce_position

def test_positions_are_allowed_and_only_active_vwce_buys_are_duplicates():
    contract = SimpleNamespace(conId=7); buy = SimpleNamespace(action="BUY")
    assert vwce_position([("U1", contract, 4.0, 100.0)], 7) == 4.0
    assert has_active_vwce_buy([(1, contract, buy, SimpleNamespace(status="Submitted"))], 7)
    assert not has_active_vwce_buy([(1, contract, buy, SimpleNamespace(status="Filled"))], 7)
