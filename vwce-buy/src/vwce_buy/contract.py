from dataclasses import dataclass
from .config import DESTINATION, ISIN, SYMBOL

@dataclass(frozen=True)
class ResolvedContract:
    con_id: int
    symbol: str
    local_symbol: str
    isin: str
    currency: str
    sec_type: str
    valid_exchanges: tuple[str, ...]

def resolve(details: list[object]) -> ResolvedContract:
    matches: list[ResolvedContract] = []
    for detail in details:
        contract = detail.contract
        exchanges = tuple(x.strip() for x in getattr(detail, "validExchanges", "").split(",") if x.strip())
        isin = getattr(detail, "secIdList", [])
        found_isin = next((x.value for x in isin if getattr(x, "tag", "") == "ISIN"), "")
        candidate = ResolvedContract(contract.conId, contract.symbol, contract.localSymbol, found_isin, contract.currency, contract.secType, exchanges)
        if candidate.isin == ISIN and candidate.sec_type == "STK" and candidate.currency == "EUR" and (candidate.symbol == SYMBOL or candidate.local_symbol == SYMBOL):
            matches.append(candidate)
    if len(matches) != 1:
        raise ValueError("ABORT: VWCE contract could not be uniquely resolved.")
    result = matches[0]
    if DESTINATION not in result.valid_exchanges:
        raise ValueError("ABORT: IBIS2 is not valid for resolved contract.")
    return result
