"""Small synchronous adapter over the official callback-based ibapi client.

No market-data request method is imported or called here.
"""
from __future__ import annotations
from dataclasses import dataclass
from threading import Event, Thread
from typing import Any
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

@dataclass
class OrderState:
    order_id: int
    status: str = "Unknown"
    filled: float = 0
    remaining: float = 0
    average_fill_price: float = 0
    perm_id: int = 0
    why_held: str = ""

class _Callbacks(EWrapper):
    def __init__(self) -> None:
        super().__init__(); self.next_id: int | None = None; self.next_id_ready = Event(); self.errors: list[str] = []; self.order_states: dict[int, OrderState] = {}
    def nextValidId(self, orderId: int) -> None: self.next_id = orderId; self.next_id_ready.set()
    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson: str = "") -> None:
        if errorCode not in {2104, 2106, 2158}: self.errors.append(f"{errorCode}: {errorString}")
    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float = 0) -> None:
        self.order_states[orderId] = OrderState(orderId, status, filled, remaining, avgFillPrice, permId, whyHeld)

class IbkrClient:
    def __init__(self, host: str, port: int, client_id: int) -> None:
        self.callbacks = _Callbacks(); self.client = EClient(self.callbacks); self.host, self.port, self.client_id = host, port, client_id; self._thread: Thread | None = None
    def __enter__(self) -> "IbkrClient":
        self.client.connect(self.host, self.port, self.client_id)
        self._thread = Thread(target=self.client.run, daemon=True); self._thread.start()
        self.client.reqIds(-1)
        if not self.callbacks.next_id_ready.wait(10) or self.callbacks.next_id is None: raise RuntimeError("ABORT: Cannot connect to TWS or obtain an order ID.")
        if self.callbacks.errors: raise RuntimeError("ABORT: " + self.callbacks.errors[-1])
        return self
    def __exit__(self, *exc: Any) -> None: self.client.disconnect()
    def place_one(self, contract: Contract, order: Order) -> OrderState:
        if self.callbacks.next_id is None: raise RuntimeError("ABORT: No TWS order ID available.")
        order_id = self.callbacks.next_id; self.callbacks.next_id += 1
        self.client.placeOrder(order_id, contract, order)
        return self.callbacks.order_states.get(order_id, OrderState(order_id, "Submitted"))
