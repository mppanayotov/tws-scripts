from decimal import Decimal, InvalidOperation

def select_account(accounts: list[str], configured: str | None) -> str:
    unique = list(dict.fromkeys(account for account in accounts if account))
    if configured:
        if configured not in unique:
            raise ValueError("ABORT: Configured account was not returned by TWS.")
        return configured
    if len(unique) != 1:
        raise ValueError("ABORT: Multiple or no managed accounts; set IBKR_ACCOUNT.")
    return unique[0]

def eur_available_funds(rows: list[tuple[str, str, str, str]], account: str) -> Decimal:
    values = [value for row_account, tag, value, currency in rows if row_account == account and tag == "AvailableFunds" and currency == "EUR"]
    if len(values) != 1:
        raise ValueError("ABORT: EUR AvailableFunds is unavailable or ambiguous.")
    try:
        return Decimal(values[0])
    except InvalidOperation:
        raise ValueError("ABORT: EUR AvailableFunds is malformed.") from None
