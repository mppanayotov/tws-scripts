"""Non-sensitive runtime diagnostics for the externally installed IBKR API."""
from __future__ import annotations
import platform
import ibapi

def api_diagnostics() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "ibapi_path": str(getattr(ibapi, "__file__", "unknown")),
        "ibapi_version": str(getattr(ibapi, "__version__", "unknown")),
    }
