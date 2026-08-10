from datetime import datetime, timezone
import json
import os
from pathlib import Path

def mask_account(account: str) -> str:
    return "*" * max(0, len(account) - 4) + account[-4:]

def append_audit(record: dict, directory: Path | None = None) -> Path:
    if directory is not None:
        target = directory
    elif os.name == "nt":
        target = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "tws-scripts" / "audit"
    else:
        target = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "tws-scripts" / "audit"
    target.mkdir(parents=True, exist_ok=True)
    path = target / "vwce-buy.jsonl"
    record = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), **record}
    path.open("a", encoding="utf-8").write(json.dumps(record, default=str) + "\n")
    return path
