"""Human-run only: exactly one PAPER WhatIf preview; never a normal order."""
import os
from datetime import datetime, timezone
import pytest
from vwce_buy.account import eur_available_funds, select_account
from vwce_buy.audit import append_audit, mask_account, paper_whatif_event
from vwce_buy.config import Settings
from vwce_buy.contract import resolve
from vwce_buy.guards import parse_price, require_cash
from vwce_buy.ibkr_client import PaperWhatIfClient
from vwce_buy.open_orders import has_active_vwce_buy
from vwce_buy.order import build_contract
from vwce_buy.positions import vwce_position
from vwce_buy.runtime import api_diagnostics
from vwce_buy.sessions import session_state
from vwce_buy.whatif import build_whatif_order, require_tick_aligned, require_whatif_gate, tick_increment, validate_whatif
from vwce_buy.whatif_safety import require_whatif_postconditions
from vwce_buy.whatif_preview import display_value, normalize_order_state

@pytest.mark.integration
def test_paper_whatif_preview_only():
    if os.getenv("IBKR_RUN_PAPER_TESTS") != "1" or os.getenv("IBKR_RUN_PAPER_WHATIF") != "1": pytest.skip("set both IBKR_RUN_PAPER_TESTS=1 and IBKR_RUN_PAPER_WHATIF=1")
    account_env, limit_env = os.getenv("IBKR_PAPER_ACCOUNT"), os.getenv("IBKR_PAPER_WHATIF_LIMIT")
    if not account_env: pytest.fail("ABORT: IBKR_PAPER_ACCOUNT is required for PAPER WhatIf.")
    if not limit_env: pytest.fail("ABORT: IBKR_PAPER_WHATIF_LIMIT is required for PAPER WhatIf.")
    settings = Settings.from_environment(live=False, host=None, client_id=None, account=account_env)
    assert settings.host == "127.0.0.1" and settings.port == 7497 and settings.client_id != 0 and not settings.live
    price = parse_price(limit_env); require_whatif_gate(settings.account, settings.host, settings.port, settings.client_id)
    with PaperWhatIfClient(settings.host, settings.port, settings.client_id) as client:
        account = select_account(client.get_managed_accounts(), settings.account)
        rows = client.get_contract_details(); resolved = resolve(rows); detail = next(d for d in rows if d.contract.conId == resolved.con_id)
        exchanges = [x.strip() for x in detail.validExchanges.split(",") if x.strip()]; rules = [int(x) for x in detail.marketRuleIds.split(",") if x]
        ibis_rule = rules[exchanges.index("IBIS2")] if len(exchanges) == len(rules) else None
        if ibis_rule is None: pytest.fail("ABORT: IBIS2 market rule mapping is ambiguous.")
        tick = tick_increment(price, client.get_market_rule(ibis_rule)); require_tick_aligned(price, tick)
        session = session_state(detail.timeZoneId, detail.tradingHours, datetime.now(timezone.utc))
        if session == "UNKNOWN": pytest.fail("ABORT: Market session cannot be parsed.")
        funds = eur_available_funds(client.get_account_summary(), account); require_cash(funds, price)
        position_before = vwce_position(client.get_positions(), resolved.con_id); before = client.get_open_orders()
        if has_active_vwce_buy(before, resolved.con_id): pytest.fail("ABORT: Existing active VWCE BUY order detected.")
        contract, order = build_contract(resolved), build_whatif_order(account, price); validate_whatif(account, contract, order)
        print(f"PAPER WHATIF TEST\nAPI: {api_diagnostics()['ibapi_version']}\nHost: {settings.host}\nPort: {settings.port}\nAccount: {mask_account(account)}\nconId: {resolved.con_id}\nMarket rule: {ibis_rule}\nApplicable tick: EUR {tick}\nSession: {session}\nVWCE position: {position_before}\nREQUEST: PAPER WHATIF")
        result = client.preview_vwce_order(contract, order)
        if result.outcome == "BLOCKED":
            print(f"PAPER WHATIF BLOCKED\nReason: TWS API Read-Only mode\nIBKR error: {result.error['code'] if result.error else 'unavailable'}\nNO PREVIEW WAS PRODUCED\nNO ORDER WAS CREATED")
            append_audit(paper_whatif_event(masked_account=mask_account(account), con_id=resolved.con_id, limit_price=str(price), status="BLOCKED", session_state=session, reason=result.reason))
            return
        if result.outcome == "REJECTED": pytest.fail(f"ABORT: PAPER WhatIf rejected: {result.error}")
        if result.outcome == "TIMEOUT": pytest.fail("ABORT: Timed out waiting for PAPER WhatIf result.")
        state = result.state
        after = client.get_open_orders(); position_after = vwce_position(client.get_positions(), resolved.con_id)
        require_whatif_postconditions(has_active_vwce_buy(after, resolved.con_id), position_before, position_after)
        preview = normalize_order_state(state)
        fields = preview.audit_fields(); fields.pop("status")
        append_audit(paper_whatif_event(masked_account=mask_account(account), con_id=resolved.con_id, limit_price=str(price), status=str(preview.status or "UNAVAILABLE"), session_state=session, **fields))
        print("IBKR WHATIF\n----------------------------------------\n" + "\n".join(f"{label}: {display_value(getattr(preview, field))}" for label, field in (("Callback status", "status"), ("Commission/fees", "commission_and_fees"), ("Minimum commission", "min_commission_and_fees"), ("Maximum commission", "max_commission_and_fees"), ("Commission currency", "commission_currency"), ("Initial margin before", "init_margin_before"), ("Initial margin change", "init_margin_change"), ("Initial margin after", "init_margin_after"), ("Maintenance before", "maintenance_margin_before"), ("Maintenance change", "maintenance_margin_change"), ("Maintenance after", "maintenance_margin_after"), ("Equity with loan before", "equity_with_loan_before"), ("Equity with loan change", "equity_with_loan_change"), ("Equity with loan after", "equity_with_loan_after"), ("Suggested size", "suggested_size"), ("Warning", "warning_text"), ("Reject reason", "reject_reason"))))
        print("PAPER WHATIF PREVIEW ONLY\nNO WORKING ORDER CREATED\nPOSITION UNCHANGED")
