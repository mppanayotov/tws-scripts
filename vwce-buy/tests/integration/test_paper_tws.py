"""Opt-in, PAPER-only read-only diagnostic. No order, WhatIf, cancel, or market data."""
import os
from datetime import datetime, timezone
import pytest
from vwce_buy.account import eur_available_funds, select_account
from vwce_buy.audit import mask_account
from vwce_buy.config import Settings
from vwce_buy.contract import candidate_diagnostic, resolve
from vwce_buy.ibkr_client import ReadOnlyPaperClient
from vwce_buy.open_orders import has_active_vwce_buy
from vwce_buy.positions import vwce_position
from vwce_buy.sessions import session_state
from vwce_buy.runtime import api_diagnostics

@pytest.mark.integration
def test_paper_tws_read_only_diagnostics():
    if os.getenv("IBKR_RUN_PAPER_TESTS") != "1": pytest.skip("set IBKR_RUN_PAPER_TESTS=1 to connect to PAPER TWS")
    if not os.getenv("IBKR_PAPER_ACCOUNT"): pytest.fail("ABORT: IBKR_PAPER_ACCOUNT is required for PAPER integration.")
    settings = Settings.from_environment(live=False, host=None, client_id=None, account=None)
    assert settings.host == "127.0.0.1" and settings.port != 7496 and not settings.live
    with ReadOnlyPaperClient(settings.host, settings.port, settings.client_id) as client:
        account = select_account(client.get_managed_accounts(), settings.account)
        rows = client.get_contract_details()
        print(f"ContractDetails rows: {len(rows)}")
        for detail in rows:
            candidate = candidate_diagnostic(detail)
            print("CONTRACT CANDIDATE")
            for key in ("conId", "symbol", "localSymbol", "secType", "currency", "exchange", "primaryExchange", "validExchanges", "marketRuleIds", "minTick", "secIdList_type", "secIdList_len", "secIdList_items", "discovered_isin", "isin_ok", "sec_type_ok", "currency_ok", "symbol_ok", "ibis2_available"):
                print(f"{key}: {candidate[key]}")
        resolved = resolve(rows)
        details = next(item for item in client.callbacks.store.details.values() for item in item if item.contract.conId == resolved.con_id)
        rule_ids = [int(item) for item in getattr(details, "marketRuleIds", "").split(",") if item]
        exchanges = [item.strip() for item in getattr(details, "validExchanges", "").split(",") if item.strip()]
        ibis_index = exchanges.index("IBIS2")
        ibis_rule = rule_ids[ibis_index] if len(rule_ids) == len(exchanges) else None
        increments = client.get_market_rule(ibis_rule) if ibis_rule else []
        summary = client.get_account_summary(); available_eur = eur_available_funds(summary, account)
        position = vwce_position(client.get_positions(), resolved.con_id)
        duplicate = has_active_vwce_buy(client.get_open_orders(), resolved.con_id)
        state = session_state(getattr(details, "timeZoneId", ""), getattr(details, "tradingHours", ""), datetime.now(timezone.utc))
        print(f"PAPER TWS CONNECTED\nAPI version: {api_diagnostics()['ibapi_version']}\nHost: {settings.host}\nPort: {settings.port}\nAccount: {mask_account(account)}")
        print(f"CONTRACT\nSymbol: {resolved.symbol}\nLocal symbol: {resolved.local_symbol}\nconId: {resolved.con_id}\nValid exchanges: {getattr(details, 'validExchanges', '')}\nIBIS2: YES")
        print(f"SESSION\nTime zone: {getattr(details, 'timeZoneId', '')}\nTrading hours: {getattr(details, 'tradingHours', '')}\nLiquid hours: {getattr(details, 'liquidHours', '')}\nParsed state: {state}")
        print(f"MARKET RULE\nRule IDs: {getattr(details, 'marketRuleIds', '')}\nIBIS2 rule: {ibis_rule}\nPrice increments: {[(item.lowEdge, item.increment) for item in increments]}")
        print(f"ACCOUNT\nAvailable EUR: {available_eur}\nPOSITION\nVWCE position: {position}\nOPEN ORDERS\nActive VWCE BUY: {'YES' if duplicate else 'NO'}")
