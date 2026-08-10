from dataclasses import dataclass
from .config import DESTINATION, ISIN, SYMBOL

@dataclass(frozen=True)
class ResolvedContract:
    con_id: int; symbol: str; local_symbol: str; isin: str; currency: str; sec_type: str; valid_exchanges: tuple[str, ...]

def extract_isin(detail: object) -> str:
    for item in getattr(detail, "secIdList", []) or []:
        if getattr(item, "tag", "") == "ISIN": return str(getattr(item, "value", ""))
    return ""

def candidate_diagnostic(detail: object) -> dict[str, object]:
    contract = detail.contract
    exchanges = tuple(item.strip() for item in getattr(detail, "validExchanges", "").split(",") if item.strip())
    isin = extract_isin(detail)
    symbol, local = getattr(contract, "symbol", ""), getattr(contract, "localSymbol", "")
    return {"conId": getattr(contract, "conId", 0), "symbol": symbol, "localSymbol": local, "secType": getattr(contract, "secType", ""), "currency": getattr(contract, "currency", ""), "exchange": getattr(contract, "exchange", ""), "primaryExchange": getattr(contract, "primaryExchange", ""), "validExchanges": getattr(detail, "validExchanges", ""), "marketRuleIds": getattr(detail, "marketRuleIds", ""), "minTick": getattr(detail, "minTick", None), "secIdList_type": type(getattr(detail, "secIdList", [])).__name__, "secIdList_len": len(getattr(detail, "secIdList", []) or []), "secIdList_items": [(type(item).__name__, getattr(item, "tag", ""), getattr(item, "value", "")) for item in (getattr(detail, "secIdList", []) or [])], "discovered_isin": isin, "isin_ok": isin == ISIN, "sec_type_ok": getattr(contract, "secType", "") == "STK", "currency_ok": getattr(contract, "currency", "") == "EUR", "symbol_ok": symbol == SYMBOL or local == SYMBOL, "ibis2_available": DESTINATION in exchanges}

def resolve(details: list[object]) -> ResolvedContract:
    diagnostics = [candidate_diagnostic(detail) for detail in details]
    matches = [item for item in diagnostics if item["isin_ok"] and item["sec_type_ok"] and item["currency_ok"] and item["symbol_ok"]]
    if len(matches) != 1: raise ValueError("ABORT: VWCE contract could not be uniquely resolved.")
    result = matches[0]
    if not result["ibis2_available"]: raise ValueError("ABORT: IBIS2 is not valid for resolved contract.")
    return ResolvedContract(int(result["conId"]), str(result["symbol"]), str(result["localSymbol"]), str(result["discovered_isin"]), str(result["currency"]), str(result["secType"]), tuple(item.strip() for item in str(result["validExchanges"]).split(",") if item.strip()))
