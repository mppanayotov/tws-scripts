"""Human-run only PAPER order integration. Never invoked by the normal CLI."""
import os
import pytest
from vwce_buy.config import Settings
from vwce_buy.guards import parse_price
from vwce_buy.paper_order import require_paper_confirmation, require_paper_order_gate

@pytest.mark.integration
def test_paper_order_requires_explicit_human_authorization_and_confirmation():
    if os.getenv("IBKR_RUN_PAPER_TESTS") != "1" or os.getenv("IBKR_RUN_PAPER_ORDER") != "1": pytest.skip("set IBKR_RUN_PAPER_TESTS=1 and IBKR_RUN_PAPER_ORDER=1")
    account, limit = os.getenv("IBKR_PAPER_ACCOUNT"), os.getenv("IBKR_PAPER_ORDER_LIMIT")
    if not account: pytest.fail("ABORT: IBKR_PAPER_ACCOUNT is required for PAPER order integration.")
    if not limit: pytest.fail("ABORT: IBKR_PAPER_ORDER_LIMIT is required for PAPER order integration.")
    settings = Settings.from_environment(live=False, host=None, client_id=None, account=account)
    assert settings.host == "127.0.0.1" and settings.port == 7497 and settings.client_id != 0 and not settings.live
    price = parse_price(limit); require_paper_order_gate(account, settings.host, settings.port, settings.client_id)
    try: typed = input(f"Type exactly: PAPER BUY 1 VWCE AT {price:.2f} VIA IBIS2\n")
    except (EOFError, KeyboardInterrupt): pytest.fail("ABORT: PAPER confirmation unavailable.")
    require_paper_confirmation(price, typed)
    pytest.fail("PAPER order transport integration is intentionally not enabled until full WhatIf/state orchestration is integrated.")
