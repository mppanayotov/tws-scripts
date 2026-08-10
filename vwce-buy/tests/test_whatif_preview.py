import json
from decimal import Decimal
from ibapi.order_state import OrderState
from vwce_buy.audit import append_audit, mask_account, paper_whatif_event
from vwce_buy.whatif_preview import display_value, normalize_order_state

def test_order_state_preview_normalizes_defaults_and_audit_uses_same_fields(tmp_path):
    state = OrderState(); state.status = "PreSubmitted"; state.commissionAndFees = 1.25; state.commissionAndFeesCurrency = "EUR"; state.warningText = "  check  "
    preview = normalize_order_state(state)
    assert preview.status == "PreSubmitted" and preview.commission_and_fees == 1.25 and preview.min_commission_and_fees is None and preview.warning_text == "  check  "
    fields = preview.audit_fields(); fields.pop("status")
    event = paper_whatif_event(masked_account=mask_account("DU123456"), con_id=1, limit_price="160.00", status=str(preview.status), session_state="CLOSED", **fields)
    row = json.loads(append_audit(event, tmp_path).read_text(encoding="utf-8"))
    assert row["commission_and_fees"] == 1.25 and row["account"] == "****3456" and not {"execution_exchange", "execution_id", "execution_time", "fill_price", "fill_quantity", "average_fill_price"}.intersection(row)
    assert preview.suggested_size is None and display_value(preview.suggested_size) == "N/A" and row["suggested_size"] is None
    for value in (Decimal("0"), Decimal("1"), Decimal("1000000")):
        state.suggestedSize = value
        assert normalize_order_state(state).suggested_size == value
