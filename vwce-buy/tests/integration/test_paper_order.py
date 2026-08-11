"""Human-run only: one gated normal PAPER order, never a LIVE order."""
import os
from datetime import datetime, timezone
import pytest
from vwce_buy.account import eur_available_funds, select_account
from vwce_buy.audit import append_audit, mask_account, paper_order_event
from vwce_buy.config import Settings
from vwce_buy.contract import resolve
from vwce_buy.guards import parse_price
from vwce_buy.ibkr_client import PaperOrderClient, PaperWhatIfClient
from vwce_buy.open_orders import has_active_vwce_buy
from vwce_buy.order import build_contract
from vwce_buy.paper_order import approve_paper_order, build_paper_order, require_paper_order_gate
from vwce_buy.positions import vwce_position
from vwce_buy.sessions import session_state
from vwce_buy.whatif import build_whatif_order, require_tick_aligned, tick_increment
from vwce_buy.whatif_preview import display_value, normalize_order_state

@pytest.mark.integration
def test_paper_order_once_after_preview():
    account_env, limit_env = os.getenv("IBKR_PAPER_ACCOUNT"), os.getenv("IBKR_PAPER_ORDER_LIMIT")
    if os.getenv("IBKR_RUN_PAPER_TESTS") != "1" or os.getenv("IBKR_RUN_PAPER_ORDER") != "1" or not account_env or not limit_env:
        pytest.skip("set all PAPER order gates: IBKR_RUN_PAPER_TESTS, IBKR_RUN_PAPER_ORDER, IBKR_PAPER_ACCOUNT, IBKR_PAPER_ORDER_LIMIT")
    settings = Settings.from_environment(live=False, host=None, client_id=None, account=account_env)
    price = parse_price(limit_env); require_paper_order_gate(account_env, limit_env, settings.host, settings.port, settings.client_id)
    with PaperWhatIfClient(settings.host, settings.port, settings.client_id) as preview_client:
        account = select_account(preview_client.get_managed_accounts(), settings.account); rows = preview_client.get_contract_details(); resolved = resolve(rows); detail = next(d for d in rows if d.contract.conId == resolved.con_id)
        exchanges, rules = [x.strip() for x in detail.validExchanges.split(",") if x.strip()], [int(x) for x in detail.marketRuleIds.split(",") if x]
        ibis_rule = rules[exchanges.index("IBIS2")] if len(exchanges) == len(rules) else None
        if ibis_rule is None: pytest.fail("ABORT: IBIS2 market rule mapping is ambiguous.")
        tick = tick_increment(price, preview_client.get_market_rule(ibis_rule)); require_tick_aligned(price, tick)
        session = session_state(detail.timeZoneId, detail.liquidHours or detail.tradingHours, datetime.now(timezone.utc))
        funds = eur_available_funds(preview_client.get_account_summary(), account); position_before = vwce_position(preview_client.get_positions(), resolved.con_id); duplicate = has_active_vwce_buy(preview_client.get_open_orders(), resolved.con_id)
        whatif = preview_client.preview_vwce_order(build_contract(resolved), build_whatif_order(account, price))
    if whatif.outcome != "PREVIEW_RECEIVED": pytest.fail(f"ABORT: PAPER WhatIf must be PREVIEW_RECEIVED, got {whatif.outcome}: {whatif.reason}")
    preview = normalize_order_state(whatif.state); print("PAPER WHATIF PREVIEW\n" + "\n".join(f"{label}: {display_value(getattr(preview, field))}" for label, field in (("Status", "status"), ("Commission", "commission_and_fees"), ("Warning", "warning_text"), ("Reject reason", "reject_reason"))))
    order = build_paper_order(account, price); approved = approve_paper_order(account=account, configured_account=account_env, limit=price, increment=tick, available_eur=funds, resolved=resolved, contract=build_contract(resolved), order=order, session=session, duplicate=duplicate, host=settings.host, port=settings.port, client_id=settings.client_id, configured_limit=limit_env)
    with PaperOrderClient(settings.host, settings.port, settings.client_id) as order_client:
        order_client.reserve_after_order_id(whatif.order_id)
        result = order_client.submit_vwce_order(approved); after_orders = order_client.get_open_orders(); position_after = vwce_position(order_client.get_positions(), resolved.con_id)
    if result.order_id == whatif.order_id: pytest.fail("ABORT: PAPER order ID must not reuse the WhatIf order ID.")
    if result.is_filled and position_after != position_before + 1: pytest.fail("ABORT: Filled PAPER order did not reconcile to position +1.")
    fields = preview.audit_fields(); fields.pop("status")
    event = paper_order_event(masked_account=mask_account(account), con_id=resolved.con_id, limit_price=str(price), order_id=result.order_id, status=result.status or "NO_STATUS", preview_status=preview.status, **fields, perm_id=result.perm_id, filled=str(result.filled), remaining=str(result.remaining), average_fill_price=str(result.average_fill_price) if result.average_fill_price is not None else None, executions=[{"execution_id": item.exec_id, "execution_time": item.execution_time, "execution_exchange": item.execution_exchange, "execution_price": str(item.execution_price), "execution_quantity": str(item.shares)} for item in result.executions])
    append_audit(event)
    print("PAPER ORDER FILLED" if result.is_filled else "PAPER ORDER WORKING" if result.is_working else f"PAPER ORDER STATUS: {result.status}")
    assert not (result.is_filled and has_active_vwce_buy(after_orders, resolved.con_id))
