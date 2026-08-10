from types import SimpleNamespace
import pytest
from vwce_buy.contract import resolve

def test_contract_invariants_and_ambiguity():
    valid = SimpleNamespace(contract=SimpleNamespace(conId=1, symbol="VWCE", localSymbol="VWCE", currency="EUR", secType="STK"), secIdList=[SimpleNamespace(tag="ISIN", value="IE00BK5BQT80")], validExchanges="IBIS2,SMART")
    assert resolve([valid]).con_id == 1
    with pytest.raises(ValueError): resolve([valid, valid])
