from datetime import datetime, timezone
import json
import os
from pathlib import Path

def mask_account(account: str) -> str:
    return "****" + account[-4:] if len(account) >= 4 else "****"

def append_audit(record: dict, directory: Path | None = None) -> Path:
    if directory is not None:
        target = directory
    elif os.name == "nt":
        target = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "tws-scripts" / "audit"
    else:
        target = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "tws-scripts" / "audit"
    target.mkdir(parents=True, exist_ok=True)
    path = target / "vwce-buy.jsonl"
    prohibited = {"password", "token", "api_key", "secret", "two_factor"}
    if prohibited.intersection(record):
        raise ValueError("ABORT: Sensitive data may not be written to audit logs.")
    record = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), **record}
    path.open("a", encoding="utf-8").write(json.dumps(record, default=str) + "\n")
    return path

def execution_event(*, requested_exchange: str, execution_exchange: str | None = None, **fields: object) -> dict:
    if execution_exchange == requested_exchange:
        raise ValueError("ABORT: Execution exchange must be IBKR-reported, not copied from requested route.")
    return {**fields, "requested_exchange": requested_exchange, "execution_exchange": execution_exchange}

def paper_whatif_event(*, masked_account: str, con_id: int, limit_price: str, status: str, session_state: str, **preview: object) -> dict:
    prohibited = {"execution_exchange", "execution_id", "execution_time", "fill_price", "fill_quantity", "average_fill_price"}
    if prohibited.intersection(preview): raise ValueError("ABORT: WhatIf audit may not contain execution fields.")
    if "status" in preview: raise ValueError("ABORT: Use preview_status rather than a duplicate status field.")
    return {"event": "PAPER_WHATIF", "account": masked_account, "con_id": con_id, "isin": "IE00BK5BQT80", "limit_price": limit_price, "requested_exchange": "IBIS2", "quantity": 1, "order_type": "LMT", "what_if": True, "preview_status": status, "session_state": session_state, **preview}

def paper_order_event(*, masked_account: str, con_id: int, limit_price: str, order_id: int, status: str, **fields: object) -> dict:
    return {"event": "PAPER_ORDER", "account": masked_account, "con_id": con_id, "isin": "IE00BK5BQT80", "action": "BUY", "quantity": 1, "limit_price": limit_price, "requested_exchange": "IBIS2", "tif": "DAY", "outside_rth": False, "order_ref": "VWCE_DCA_PAPER", "order_id": order_id, "status": status, **fields}
