from decimal import Decimal
import pytest
from vwce_buy.guards import parse_price, require_cash, require_confirmation

def test_price_cash_and_confirmation_guards():
    assert parse_price("168.60") == Decimal("168.60")
    for value in ("x", "0", "-1", "250.01", "1.001", "NaN"):
        with pytest.raises(ValueError): parse_price(value)
    with pytest.raises(ValueError): require_cash(Decimal("178.59"), Decimal("168.60"))
    with pytest.raises(ValueError): require_confirmation(Decimal("168.60"), "no")
