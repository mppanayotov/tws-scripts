"""Pure WhatIf-only order construction and invariant checks."""
from decimal import Decimal
import os
from ibapi.order import Order
from ibapi.contract import Contract

def tick_increment(price: Decimal, increments: list[object]) -> Decimal:
    choices = [(Decimal(str(item.lowEdge)), Decimal(str(item.increment))) for item in increments]
    valid = [item for item in choices if item[0] <= price]
    if not valid: raise ValueError("ABORT: IBIS2 price increment is unknown for this price.")
    return max(valid, key=lambda item: item[0])[1]

def require_whatif_gate(account: str | None, host: str, port: int, client_id: int) -> None:
    if os.getenv("IBKR_RUN_PAPER_TESTS") != "1" or os.getenv("IBKR_RUN_PAPER_WHATIF") != "1" or not account or host != "127.0.0.1" or port != 7497 or client_id == 0:
        raise ValueError("ABORT: PAPER WhatIf integration gate is not satisfied.")

def require_tick_aligned(price: Decimal, increment: Decimal) -> None:
    if price % increment != 0: raise ValueError("ABORT: Limit price does not align with the IBIS2 market-rule increment.")

def build_whatif_order(account: str, price: Decimal) -> Order:
    order = Order(); order.account, order.action, order.totalQuantity, order.orderType, order.lmtPrice = account, "BUY", 1, "LMT", float(price)
    order.tif, order.outsideRth, order.orderRef, order.whatIf, order.transmit = "DAY", False, "VWCE_DCA_WHATIF", True, True
    return order

def validate_whatif(account: str, contract: Contract, order: Order) -> None:
    if not all((account, order.account == account, contract.exchange == "IBIS2", order.whatIf is True, order.transmit is True, order.action == "BUY", order.totalQuantity == 1, order.orderType == "LMT", order.tif == "DAY", order.outsideRth is False)):
        raise ValueError("ABORT: PAPER WhatIf invariants failed.")
