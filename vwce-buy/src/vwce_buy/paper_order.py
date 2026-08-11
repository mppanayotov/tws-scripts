"""PAPER-order-only models and final submission invariants."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import os

from ibapi.contract import Contract
from ibapi.order import Order

from .config import DESTINATION, MAX_ORDER_EUR
from .contract import ResolvedContract
from .guards import parse_price, require_cash
from .whatif import require_tick_aligned


@dataclass(frozen=True)
class PaperExecution:
    exec_id: str
    execution_time: str
    account: str
    side: str
    shares: Decimal
    execution_price: Decimal
    execution_exchange: str
    perm_id: int
    order_id: int


@dataclass(frozen=True)
class PaperOrderResult:
    order_id: int
    perm_id: int | None
    status: str | None
    filled: Decimal
    remaining: Decimal
    average_fill_price: Decimal | None
    why_held: str | None
    mkt_cap_price: Decimal | None
    executions: tuple[PaperExecution, ...] = ()

    @property
    def is_filled(self) -> bool:
        return self.status == "Filled"

    @property
    def is_working(self) -> bool:
        return self.status in {"PendingSubmit", "PreSubmitted", "Submitted", "PendingCancel"}


@dataclass(frozen=True)
class ApprovedPaperOrder:
    contract: Contract
    order: Order


def require_paper_order_gate(account: str | None, limit: str | None, host: str, port: int, client_id: int) -> None:
    if (os.getenv("IBKR_RUN_PAPER_TESTS") != "1" or os.getenv("IBKR_RUN_PAPER_ORDER") != "1"
            or not account or not limit or host != "127.0.0.1" or port != 7497 or client_id == 0):
        raise ValueError("ABORT: PAPER order integration gate is not satisfied.")


def build_paper_order(account: str, price: Decimal) -> Order:
    order = Order()
    order.account, order.action, order.totalQuantity, order.orderType, order.lmtPrice = account, "BUY", 1, "LMT", float(price)
    order.tif, order.outsideRth, order.orderRef, order.whatIf, order.transmit = "DAY", False, "VWCE_DCA_PAPER", False, True
    return order


def paper_confirmation_phrase(price: Decimal) -> str:
    return f"PAPER BUY 1 VWCE AT {price:.2f} VIA IBIS2"


def require_paper_confirmation(price: Decimal, typed: str) -> None:
    if typed != paper_confirmation_phrase(price):
        raise ValueError("ABORT: PAPER confirmation mismatch.")


def validate_paper_order(*, account: str, configured_account: str, limit: Decimal, increment: Decimal,
                         available_eur: Decimal, resolved: ResolvedContract, contract: Contract, order: Order,
                         session: str, duplicate: bool, host: str, port: int, client_id: int,
                         configured_limit: str | None) -> None:
    require_paper_order_gate(configured_account, configured_limit, host, port, client_id)
    if account != configured_account:
        raise ValueError("ABORT: Verified PAPER account does not match configuration.")
    parse_price(str(limit))
    require_tick_aligned(limit, increment)
    require_cash(available_eur, limit)
    if session != "OPEN":
        raise ValueError("ABORT: PAPER order requires an OPEN IBKR trading session.")
    if duplicate:
        raise ValueError("ABORT: Existing active VWCE BUY order detected.")
    if not all((resolved.isin == "IE00BK5BQT80", resolved.sec_type == "STK", resolved.currency == "EUR",
                DESTINATION in resolved.valid_exchanges, contract.conId == resolved.con_id,
                contract.exchange == DESTINATION, contract.currency == "EUR", contract.secType == "STK",
                order.account == account, order.action == "BUY", order.totalQuantity == 1,
                order.orderType == "LMT", Decimal(str(order.lmtPrice)) == limit, limit <= MAX_ORDER_EUR,
                order.tif == "DAY", order.outsideRth is False, order.whatIf is False, order.transmit is True,
                order.orderRef == "VWCE_DCA_PAPER")):
        raise ValueError("ABORT: PAPER order invariants failed.")


def approve_paper_order(**kwargs: object) -> ApprovedPaperOrder:
    validate_paper_order(**kwargs)  # type: ignore[arg-type]
    return ApprovedPaperOrder(kwargs["contract"], kwargs["order"])  # type: ignore[arg-type]
