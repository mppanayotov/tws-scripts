from dataclasses import asdict, dataclass
from ibapi.common import UNSET_DECIMAL
from ibapi.utils import UNSET_DOUBLE

def _value(value: object) -> object | None:
    if value is None or (isinstance(value, str) and not value.strip()): return None
    if value == UNSET_DOUBLE or value == UNSET_DECIMAL: return None
    return value

@dataclass(frozen=True)
class WhatIfPreview:
    status: object | None; commission_and_fees: object | None; min_commission_and_fees: object | None; max_commission_and_fees: object | None; commission_currency: object | None
    init_margin_before: object | None; init_margin_change: object | None; init_margin_after: object | None
    maintenance_margin_before: object | None; maintenance_margin_change: object | None; maintenance_margin_after: object | None
    equity_with_loan_before: object | None; equity_with_loan_change: object | None; equity_with_loan_after: object | None
    warning_text: object | None; reject_reason: object | None; suggested_size: object | None
    def audit_fields(self) -> dict[str, object | None]: return asdict(self)

def normalize_order_state(state: object) -> WhatIfPreview:
    fields = {"status": "status", "commission_and_fees": "commissionAndFees", "min_commission_and_fees": "minCommissionAndFees", "max_commission_and_fees": "maxCommissionAndFees", "commission_currency": "commissionAndFeesCurrency", "init_margin_before": "initMarginBefore", "init_margin_change": "initMarginChange", "init_margin_after": "initMarginAfter", "maintenance_margin_before": "maintMarginBefore", "maintenance_margin_change": "maintMarginChange", "maintenance_margin_after": "maintMarginAfter", "equity_with_loan_before": "equityWithLoanBefore", "equity_with_loan_change": "equityWithLoanChange", "equity_with_loan_after": "equityWithLoanAfter", "warning_text": "warningText", "reject_reason": "rejectReason", "suggested_size": "suggestedSize"}
    return WhatIfPreview(**{key: _value(getattr(state, raw, None)) for key, raw in fields.items()})

def display_value(value: object | None) -> str: return "N/A" if value is None else str(value)
