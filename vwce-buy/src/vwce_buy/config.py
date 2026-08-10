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
        selected_host = host or os.getenv("IBKR_HOST", "127.0.0.1")
        if selected_host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("ABORT: Remote TWS hosts are not allowed.")
        port_name = "IBKR_LIVE_PORT" if live else "IBKR_PAPER_PORT"
        port = int(os.getenv(port_name, "7496" if live else "7497"))
        return cls(live, selected_host, port, client_id if client_id is not None else int(os.getenv("IBKR_CLIENT_ID", "71")), account or os.getenv("IBKR_ACCOUNT"))
