from decimal import Decimal
import pytest
from vwce_buy.account import eur_available_funds, select_account

def test_account_selection_and_eur_cash_are_unambiguous():
    assert select_account(["U1234"], None) == "U1234"
    assert select_account(["U1", "U2"], "U2") == "U2"
    with pytest.raises(ValueError): select_account(["U1", "U2"], None)
    with pytest.raises(ValueError): select_account(["U1"], "U2")
    assert eur_available_funds([("U1", "AvailableFunds", "200.00", "EUR")], "U1") == Decimal("200.00")
