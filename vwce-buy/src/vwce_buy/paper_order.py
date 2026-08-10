"""Pure invariants for the narrowly scoped PAPER VWCE order path."""
from decimal import Decimal
import os
from ibapi.contract import Contract
from ibapi.order import Order
from .contract import ResolvedContract
from .order import build_contract

def require_paper_order_gate(account: str | None, host: str, port: int, client_id: int) -> None:
    if os.getenv("IBKR_RUN_PAPER_TESTS") != "1" or os.getenv("IBKR_RUN_PAPER_ORDER") != "1" or not account or host != "127.0.0.1" or port != 7497 or client_id == 0:
        raise ValueError("ABORT: PAPER order integration gate is not satisfied.")

def build_paper_order(account: str, price: Decimal) -> Order:
    order = Order(); order.account, order.action, order.totalQuantity, order.orderType, order.lmtPrice = account, "BUY", 1, "LMT", float(price)
    order.tif, order.outsideRth, order.orderRef, order.whatIf, order.transmit = "DAY", False, "VWCE_DCA_PAPER", False, True
    return order

def require_paper_confirmation(price: Decimal, typed: str) -> None:
    if typed != f"PAPER BUY 1 VWCE AT {price:.2f} VIA IBIS2": raise ValueError("ABORT: PAPER confirmation mismatch.")

def validate_paper_order(account: str, resolved: ResolvedContract, contract: Contract, order: Order, session: str, duplicate: bool) -> None:
    if not all((account, order.account == account, contract.conId == resolved.con_id, contract.exchange == "IBIS2", contract.currency == "EUR", order.action == "BUY", order.totalQuantity == 1, order.orderType == "LMT", order.tif == "DAY", order.outsideRth is False, order.whatIf is False, order.transmit is True, session == "OPEN", not duplicate)):
        raise ValueError("ABORT: PAPER order invariants failed.")
