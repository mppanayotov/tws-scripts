from types import SimpleNamespace
import pytest
from vwce_buy.contract import candidate_diagnostic, extract_isin, resolve

def test_contract_invariants_and_ambiguity():
    valid = SimpleNamespace(contract=SimpleNamespace(conId=1, symbol="VWCE", localSymbol="VWCE", currency="EUR", secType="STK"), secIdList=[SimpleNamespace(tag="ISIN", value="IE00BK5BQT80")], validExchanges="IBIS2,SMART")
    assert resolve([valid]).con_id == 1
    with pytest.raises(ValueError): resolve([valid, valid])
    valid.validExchanges = "SMART"
    with pytest.raises(ValueError): resolve([valid])
    valid.validExchanges = "IBIS2"; valid.contract.currency = ""
    assert not candidate_diagnostic(valid)["currency_ok"]
    valid.contract.currency = "EUR"; valid.contract.symbol = "OTHER"; valid.contract.localSymbol = "VWCE"
    assert extract_isin(valid) == "IE00BK5BQT80" and candidate_diagnostic(valid)["symbol_ok"]
