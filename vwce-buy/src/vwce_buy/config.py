from dataclasses import dataclass
from decimal import Decimal
import os

ISIN = "IE00BK5BQT80"
SYMBOL = "VWCE"
DESTINATION = "IBIS2"
MAX_ORDER_EUR = Decimal("250.00")
FEE_BUFFER_EUR = Decimal("10.00")

@dataclass(frozen=True)
class Settings:
    live: bool
    host: str
    port: int
    client_id: int
    account: str | None

    @classmethod
    def from_environment(cls, *, live: bool, host: str | None, client_id: int | None, account: str | None) -> "Settings":
        if live:
            raise ValueError("ABORT: Live mode is not implemented in this paper-only build.")
        selected_host = host or os.getenv("IBKR_HOST", "127.0.0.1")
        if selected_host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("ABORT: Remote TWS hosts are not allowed.")
        port = int(os.getenv("IBKR_PAPER_PORT", "7497"))
        if port == 7496:
            raise ValueError("ABORT: PAPER mode may not use the conventional live TWS port 7496.")
        selected_client_id = client_id if client_id is not None else int(os.getenv("IBKR_CLIENT_ID", "42"))
        if selected_client_id == 0:
            raise ValueError("ABORT: PAPER diagnostics may not use client ID 0.")
        return cls(False, selected_host, port, selected_client_id, account or os.getenv("IBKR_PAPER_ACCOUNT"))
