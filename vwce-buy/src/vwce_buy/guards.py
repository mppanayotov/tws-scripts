from decimal import Decimal, InvalidOperation
from .config import FEE_BUFFER_EUR, MAX_ORDER_EUR

def parse_price(value: str) -> Decimal:
    try:
        price = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError("ABORT: Limit price is malformed.") from None
    if not price.is_finite() or price <= 0 or -price.as_tuple().exponent > 2:
        raise ValueError("ABORT: Limit price must be positive with at most two decimal places.")
    if price > MAX_ORDER_EUR:
        raise ValueError(f"ABORT: Order value EUR {price:.2f} exceeds hard maximum EUR {MAX_ORDER_EUR:.2f}.")
    return price

def require_cash(available_eur: Decimal, price: Decimal) -> None:
    if available_eur < price + FEE_BUFFER_EUR:
        raise ValueError("ABORT: Available EUR cash is insufficient.")

def require_confirmation(price: Decimal, typed: str) -> None:
    if typed != f"BUY 1 VWCE AT {price:.2f}":
        raise ValueError("ABORT: Confirmation mismatch.")
