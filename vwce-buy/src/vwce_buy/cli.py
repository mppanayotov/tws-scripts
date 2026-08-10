from __future__ import annotations
import argparse
from decimal import Decimal
from .audit import append_audit, mask_account
from .config import DESTINATION, FEE_BUFFER_EUR, ISIN, MAX_ORDER_EUR, Settings
from .guards import parse_price, require_confirmation

def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vwce-buy", description="Restricted VWCE limit-order utility.")
    p.add_argument("price", help="EUR limit price")
    mode = p.add_mutually_exclusive_group(); mode.add_argument("--live", action="store_true", help="Use configured live TWS port (requires typed confirmation).")
    mode.add_argument("--paper", action="store_true", help="Explicit paper mode (the default).")
    p.add_argument("--host"); p.add_argument("--client-id", type=int); p.add_argument("--account"); p.add_argument("--verbose", action="store_true")
    return p

def preview(price: Decimal, settings: Settings) -> None:
    title = "LIVE ORDER" if settings.live else "PAPER ORDER"
    print("#" * 40 if settings.live else "=" * 40); print(title); print("#" * 40 if settings.live else "=" * 40)
    print(f"Instrument: VWCE\nISIN: {ISIN}\nAction: BUY\nQuantity: 1\nCurrency: EUR\nType: LIMIT\nLimit: EUR {price:.2f}\nDestination: {DESTINATION}\nTIF: DAY\nOutside RTH: NO\nCash buffer: EUR {FEE_BUFFER_EUR:.2f}\nMax notional: EUR {MAX_ORDER_EUR:.2f}")

def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        price = parse_price(args.price); settings = Settings.from_environment(live=args.live, host=args.host, client_id=args.client_id, account=args.account)
        preview(price, settings)
        if settings.live:
            try: typed = input(f"Type exactly: BUY 1 VWCE AT {price:.2f}\n")
            except (EOFError, KeyboardInterrupt): raise ValueError("ABORT: Confirmation unavailable.") from None
            require_confirmation(price, typed)
            raise ValueError("ABORT: Live submission is intentionally disabled in this paper-only build.")
        # Paper submission is deliberately not attempted until contract, account, duplicate,
        # and session callback collectors are configured against a paper TWS instance.
        append_audit({"environment": "PAPER", "account": mask_account(settings.account) if settings.account else None, "isin": ISIN, "action": "BUY", "quantity": 1, "limit_price": str(price), "requested_exchange": DESTINATION, "tif": "DAY", "order_ref": "VWCE_DCA", "status": "PREVIEW_ONLY"})
        print("PAPER safety preview recorded. No order was submitted.")
        return 0
    except (ValueError, RuntimeError) as exc:
        print(str(exc)); return 2

if __name__ == "__main__": raise SystemExit(main())
