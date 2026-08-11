"""PAPER-only adapters for the official callback-based IBKR API."""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from threading import Event, Lock, Thread
from typing import Any
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.wrapper import EWrapper
from .paper_order import ApprovedPaperOrder, PaperExecution, PaperOrderResult

_INFO_CODES = {2104, 2106, 2158}

@dataclass
class CallbackStore:
    accounts: list[str] = field(default_factory=list); details: dict[int, list[object]] = field(default_factory=dict)
    summaries: dict[int, list[tuple[str, str, str, str]]] = field(default_factory=dict); positions: list[tuple[str, object, float, float]] = field(default_factory=list)
    open_orders: list[tuple[int, object, object, object]] = field(default_factory=list); rules: dict[int, list[object]] = field(default_factory=dict)
    errors: dict[int, list[dict[str, object]]] = field(default_factory=dict)

@dataclass(frozen=True)
class WhatIfResult:
    outcome: str; order_id: int; state: object | None = None; reason: str | None = None; error: dict[str, object] | None = None

@dataclass(frozen=True)
class OrderState:
    order_id: int
    status: str
    filled: float = 0
    remaining: float = 0

class _ReadOnlyCallbacks(EWrapper):
    def __init__(self) -> None:
        super().__init__(); self.store = CallbackStore(); self.next_order_id: int | None = None; self.ready = Event(); self.accounts_done = Event(); self.contract_done: dict[int, Event] = {}; self.summary_done: dict[int, Event] = {}; self.positions_done = Event(); self.orders_done = Event(); self.rule_done: dict[int, Event] = {}; self.whatif_done: dict[int, Event] = {}; self.whatif_states: dict[int, object] = {}; self.whatif_errors: dict[int, dict[str, object]] = {}; self.order_updates: dict[int, dict[str, object]] = {}; self.order_executions: dict[int, list[PaperExecution]] = {}; self.order_update_events: dict[int, Event] = {}; self._lock = Lock()
    def nextValidId(self, orderId: int) -> None: self.next_order_id = orderId; self.ready.set()
    def error(self, reqId: int, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson: str = "") -> None:
        if errorCode not in _INFO_CODES:
            error = {"time": errorTime, "code": errorCode, "message": errorString, "advanced_reject": advancedOrderRejectJson}
            with self._lock:
                self.store.errors.setdefault(reqId, []).append(error)
                if reqId in self.whatif_done: self.whatif_errors[reqId] = error; self.whatif_done[reqId].set()
                if reqId in self.order_update_events: self.order_update_events[reqId].set()
    def managedAccounts(self, accountsList: str) -> None: self.store.accounts = [item.strip() for item in accountsList.split(",") if item.strip()]; self.accounts_done.set()
    def contractDetails(self, reqId: int, contractDetails: object) -> None: self.store.details.setdefault(reqId, []).append(contractDetails)
    def contractDetailsEnd(self, reqId: int) -> None: self.contract_done.setdefault(reqId, Event()).set()
    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str) -> None: self.store.summaries.setdefault(reqId, []).append((account, tag, value, currency))
    def accountSummaryEnd(self, reqId: int) -> None: self.summary_done.setdefault(reqId, Event()).set()
    def position(self, account: str, contract: object, position: float, avgCost: float) -> None: self.store.positions.append((account, contract, position, avgCost))
    def positionEnd(self) -> None: self.positions_done.set()
    def openOrder(self, orderId: int, contract: object, order: object, orderState: object) -> None:
        self.store.open_orders.append((orderId, contract, order, orderState))
        if getattr(order, "whatIf", False): self.whatif_states[orderId] = orderState; self.whatif_done.setdefault(orderId, Event()).set()
    def openOrderEnd(self) -> None: self.orders_done.set()
    def marketRule(self, marketRuleId: int, priceIncrements: list[object]) -> None: self.store.rules[marketRuleId] = list(priceIncrements); self.rule_done.setdefault(marketRuleId, Event()).set()
    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float) -> None:
        self.order_updates[orderId] = {"status": status, "filled": Decimal(str(filled)), "remaining": Decimal(str(remaining)), "average_fill_price": None if not avgFillPrice else Decimal(str(avgFillPrice)), "perm_id": permId or None, "why_held": whyHeld or None, "mkt_cap_price": None if not mktCapPrice else Decimal(str(mktCapPrice))}; self.order_update_events.setdefault(orderId, Event()).set()
    def execDetails(self, reqId: int, contract: object, execution: object) -> None:
        order_id = int(getattr(execution, "orderId", 0)); item = PaperExecution(str(getattr(execution, "execId", "")), str(getattr(execution, "time", "")), str(getattr(execution, "acctNumber", "")), str(getattr(execution, "side", "")), Decimal(str(getattr(execution, "shares", 0))), Decimal(str(getattr(execution, "price", 0))), str(getattr(execution, "exchange", "")), int(getattr(execution, "permId", 0)), order_id); self.order_executions.setdefault(order_id, []).append(item); self.order_update_events.setdefault(order_id, Event()).set()

class ReadOnlyPaperClient:
    """No normal order placement, cancellation, or market-data API is exposed."""
    def __init__(self, host: str, port: int, client_id: int = 42) -> None:
        if host != "127.0.0.1": raise ValueError("ABORT: PAPER clients require host 127.0.0.1.")
        if port != 7497: raise ValueError("ABORT: PAPER clients require port 7497.")
        if client_id == 0: raise ValueError("ABORT: PAPER clients may not use client ID 0.")
        self.host, self.port, self.client_id = host, port, client_id; self.callbacks = _ReadOnlyCallbacks(); self._client = EClient(self.callbacks); self._thread: Thread | None = None; self._next_req = 10
    def __enter__(self): self.connect(); return self
    def __exit__(self, *exc: Any): self.disconnect()
    def connection_diagnostics(self) -> dict[str, object]: return {"connected": self._client.isConnected(), "server_version": self._client.serverVersion(), "connection_time": self._client.twsConnectionTime(), "network_thread_alive": bool(self._thread and self._thread.is_alive()), "ready": self.callbacks.ready.is_set(), "errors": self.callbacks.store.errors}
    def connect(self) -> None: self._request("connect", self._client.connect, self.host, self.port, self.client_id); self._thread = Thread(target=self._client.run, daemon=True); self._thread.start(); self.wait_until_ready()
    def disconnect(self) -> None: self._client.disconnect()
    def wait_until_ready(self, timeout: float = 10) -> None: self._wait(self.callbacks.ready, "nextValidId", timeout, -1)
    def _id(self) -> int: self._next_req += 1; return self._next_req
    def _request(self, label: str, fn: object, *args: object) -> None: print(f"REQUEST: {label}"); fn(*args)  # type: ignore[operator]
    def _wait(self, event: Event, label: str, timeout: float, req_id: int) -> None:
        if not event.wait(timeout): raise RuntimeError(f"ABORT: Timed out waiting for {label}. Diagnostics: {self.connection_diagnostics()}")
        errors = self.callbacks.store.errors.get(req_id, []) + self.callbacks.store.errors.get(-1, [])
        if errors: raise RuntimeError(f"ABORT: {errors[-1]['code']}: {errors[-1]['message']}")
    def get_managed_accounts(self, timeout: float = 10) -> list[str]: self._request("managedAccounts", self._client.reqManagedAccts); self._wait(self.callbacks.accounts_done, "managedAccounts", timeout, -1); return list(self.callbacks.store.accounts)
    def get_contract_details(self, timeout: float = 10) -> list[object]:
        req = self._id(); self.callbacks.contract_done[req] = Event(); contract = Contract(); contract.secType, contract.secIdType, contract.secId, contract.exchange, contract.currency = "STK", "ISIN", "IE00BK5BQT80", "SMART", "EUR"; self._request("contractDetails", self._client.reqContractDetails, req, contract); self._wait(self.callbacks.contract_done[req], "contractDetailsEnd", timeout, req); return list(self.callbacks.store.details.get(req, []))
    def get_market_rule(self, rule_id: int, timeout: float = 10) -> list[object]: self.callbacks.rule_done[rule_id] = Event(); self._request("marketRule", self._client.reqMarketRule, rule_id); self._wait(self.callbacks.rule_done[rule_id], "marketRule", timeout, rule_id); return list(self.callbacks.store.rules.get(rule_id, []))
    def get_account_summary(self, timeout: float = 10) -> list[tuple[str, str, str, str]]: req = self._id(); self.callbacks.summary_done[req] = Event(); self._request("accountSummary", self._client.reqAccountSummary, req, "All", "AvailableFunds,TotalCashValue,BaseCurrency"); self._wait(self.callbacks.summary_done[req], "accountSummaryEnd", timeout, req); return list(self.callbacks.store.summaries.get(req, []))
    def get_positions(self, timeout: float = 10) -> list[tuple[str, object, float, float]]: self.callbacks.positions_done.clear(); self.callbacks.store.positions.clear(); self._request("positions", self._client.reqPositions); self._wait(self.callbacks.positions_done, "positionEnd", timeout, -1); return list(self.callbacks.store.positions)
    def get_open_orders(self, timeout: float = 10) -> list[tuple[int, object, object, object]]: self.callbacks.orders_done.clear(); self.callbacks.store.open_orders.clear(); self._request("allOpenOrders", self._client.reqAllOpenOrders); self._wait(self.callbacks.orders_done, "openOrderEnd", timeout, -1); return list(self.callbacks.store.open_orders)

class PaperWhatIfClient(ReadOnlyPaperClient):
    def _send_whatif(self, order_id: int, contract: Contract, order: Order) -> None:
        if not getattr(order, "whatIf", False): raise ValueError("ABORT: Non-WhatIf orders cannot reach placeOrder.")
        self._request("paperWhatIf", self._client.placeOrder, order_id, contract, order)
    def preview_vwce_order(self, contract: Contract, order: Order, timeout: float = 15) -> WhatIfResult:
        if self.callbacks.next_order_id is None: raise RuntimeError("ABORT: No nextValidId received for PAPER WhatIf.")
        order_id = self.callbacks.next_order_id; self.callbacks.next_order_id += 1; self.callbacks.whatif_done[order_id] = Event(); self._send_whatif(order_id, contract, order)
        if not self.callbacks.whatif_done[order_id].wait(timeout): return WhatIfResult("TIMEOUT", order_id, reason="NO_RESPONSE")
        if order_id in self.callbacks.whatif_errors:
            error = self.callbacks.whatif_errors[order_id]; reason = "TWS_READ_ONLY" if error["code"] == 321 else "WHATIF_TRANSMIT_INVALID" if error["code"] == 413 else "IBKR_REJECTION"; return WhatIfResult("BLOCKED" if reason == "TWS_READ_ONLY" else "REJECTED", order_id, reason=reason, error=error)
        return WhatIfResult("PREVIEW_RECEIVED", order_id, state=self.callbacks.whatif_states[order_id])

class PaperOrderClient(ReadOnlyPaperClient):
    """The only normal-order writer; one submission per client instance."""
    def __init__(self, host: str, port: int, client_id: int = 42) -> None: super().__init__(host, port, client_id); self._submitted = False
    def reserve_after_order_id(self, consumed_order_id: int) -> None:
        if self.callbacks.next_order_id is None: raise RuntimeError("ABORT: No nextValidId received for PAPER order.")
        self.callbacks.next_order_id = max(self.callbacks.next_order_id, consumed_order_id + 1)
    def submit_vwce_order(self, approved: ApprovedPaperOrder, timeout: float = 15) -> PaperOrderResult:
        if self._submitted: raise RuntimeError("ABORT: PAPER order submission was already attempted; no retry is allowed.")
        if self.callbacks.next_order_id is None: raise RuntimeError("ABORT: No nextValidId received for PAPER order.")
        if getattr(approved.order, "whatIf", True): raise ValueError("ABORT: WhatIf order cannot reach PAPER order submission.")
        order_id = self.callbacks.next_order_id; self.callbacks.next_order_id += 1; self._submitted = True; self.callbacks.order_update_events[order_id] = Event()
        self._request("paperOrder", self._client.placeOrder, order_id, approved.contract, approved.order)
        self.callbacks.order_update_events[order_id].wait(timeout)
        update = self.callbacks.order_updates.get(order_id, {})
        return PaperOrderResult(order_id, update.get("perm_id"), update.get("status"), update.get("filled", Decimal("0")), update.get("remaining", Decimal("1")), update.get("average_fill_price"), update.get("why_held"), update.get("mkt_cap_price"), tuple(self.callbacks.order_executions.get(order_id, [])))
