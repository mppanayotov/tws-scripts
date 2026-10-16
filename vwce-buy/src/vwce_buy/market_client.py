"""Read-only historical-data transport, separate from all order clients."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Event, Lock, Thread

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper

from .config import DESTINATION, ISIN

_INFORMATIONAL_CODES = {2104, 2106, 2107, 2108, 2158}


class _MarketCallbacks(EWrapper):
    def __init__(self) -> None:
        super().__init__()
        self.ready = Event()
        self.done: dict[int, Event] = {}
        self.details: dict[int, list[object]] = {}
        self.bars: dict[int, list[object]] = {}
        self.errors: dict[int, list[str]] = {}
        self.historical_ended: set[int] = set()
        self.lock = Lock()

    def nextValidId(self, orderId: int) -> None:
        self.ready.set()

    def error(
        self,
        reqId: int,
        errorTime: int,
        errorCode: int,
        errorString: str,
        advancedOrderRejectJson: str = "",
    ) -> None:
        if errorCode in _INFORMATIONAL_CODES:
            return
        with self.lock:
            self.errors.setdefault(reqId, []).append(f"IBKR {errorCode}: {errorString}")
            if reqId < 0:
                self.ready.set()
                for event in self.done.values():
                    event.set()
            elif reqId in self.done:
                self.done[reqId].set()

    def connectionClosed(self) -> None:
        self.error(-1, 0, 504, "TWS connection closed.")

    def contractDetails(self, reqId: int, contractDetails: object) -> None:
        self.details.setdefault(reqId, []).append(contractDetails)

    def contractDetailsEnd(self, reqId: int) -> None:
        if reqId in self.done:
            self.done[reqId].set()

    def historicalData(self, reqId: int, bar: object) -> None:
        self.bars.setdefault(reqId, []).append(bar)

    def historicalDataEnd(self, reqId: int, start: str, end: str) -> None:
        self.historical_ended.add(reqId)
        if reqId in self.done:
            self.done[reqId].set()


class VwceMarketClient:
    """Only contract-details and finite historical-data requests are exposed."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 74,
        timeout: float = 20,
    ) -> None:
        if host != "127.0.0.1" or port != 7497 or client_id <= 0:
            raise ValueError("Status requires 127.0.0.1:7497 and a positive client ID.")
        if not 0 < timeout <= 120:
            raise ValueError("Timeout must be between 0 and 120 seconds.")
        self.host, self.port, self.client_id = host, port, client_id
        self.timeout = timeout
        self.callbacks = _MarketCallbacks()
        self._client = EClient(self.callbacks)
        self._thread: Thread | None = None
        self._next_request = 1000

    def __enter__(self) -> VwceMarketClient:
        try:
            self._client.connect(self.host, self.port, self.client_id)
            self._thread = Thread(target=self._client.run, daemon=True)
            self._thread.start()
            self._wait(self.callbacks.ready, -1, "TWS connection")
            return self
        except BaseException:
            self.disconnect()
            raise

    def __exit__(self, *exc: object) -> None:
        self.disconnect()

    def disconnect(self) -> None:
        self._client.disconnect()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _request_id(self) -> int:
        self._next_request += 1
        request = self._next_request
        with self.callbacks.lock:
            self.callbacks.done[request] = Event()
        return request

    def _wait(self, event: Event, request: int, description: str) -> None:
        completed = event.wait(self.timeout)
        with self.callbacks.lock:
            errors = self.callbacks.errors.get(-1, [])
            if request >= 0:
                errors = errors + self.callbacks.errors.get(request, [])
        if errors:
            raise RuntimeError(errors[0])
        if not completed:
            raise RuntimeError(f"Timed out waiting for {description}.")

    def get_contract_details(self, contract: Contract) -> list[object]:
        request = self._request_id()
        self._client.reqContractDetails(request, contract)
        self._wait(self.callbacks.done[request], request, "contract details")
        return list(self.callbacks.details.get(request, []))

    def get_daily_bars(self, contract: Contract, end: datetime) -> list[object]:
        if end.tzinfo is None:
            raise ValueError("Historical request end time must include a time zone.")
        if (
            contract.exchange != DESTINATION
            or contract.currency != "EUR"
            or contract.secType != "STK"
        ):
            raise ValueError(
                "Historical data requires the resolved VWCE IBIS2 EUR stock contract."
            )
        request = self._request_id()
        try:
            self._client.reqHistoricalData(
                request,
                contract,
                end.astimezone(timezone.utc).strftime("%Y%m%d-%H:%M:%S"),
                "3 M",
                "1 day",
                "TRADES",
                1,
                1,
                False,
                [],
            )
            self._wait(self.callbacks.done[request], request, "daily historical bars")
            return list(self.callbacks.bars.get(request, []))
        finally:
            if request not in self.callbacks.historical_ended:
                self._client.cancelHistoricalData(request)


def discovery_contract() -> Contract:
    contract = Contract()
    contract.secType, contract.secIdType, contract.secId = "STK", "ISIN", ISIN
    contract.exchange, contract.currency = "SMART", "EUR"
    return contract


def ibis2_contract(con_id: int) -> Contract:
    if con_id <= 0:
        raise ValueError("VWCE contract ID must be positive.")
    contract = Contract()
    contract.conId, contract.exchange = con_id, DESTINATION
    contract.secType, contract.currency = "STK", "EUR"
    return contract
