import json
import pytest
from vwce_buy.audit import append_audit, mask_account, paper_whatif_event

def test_audit_masks_accounts_and_does_not_create_sensitive_fields(tmp_path):
    assert mask_account("U1234567") == "****4567" and mask_account("U1") == "****"
    path = append_audit({"account": mask_account("U1234567"), "status": "PREVIEW_ONLY"}, tmp_path)
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["account"] == "****4567" and "password" not in row and "token" not in row
    with pytest.raises(ValueError): append_audit({"token": "nope"}, tmp_path)
    assert paper_whatif_event(masked_account="****1234", con_id=1, limit_price="168.60", status="PreSubmitted", session_state="CLOSED")["event"] == "PAPER_WHATIF"
