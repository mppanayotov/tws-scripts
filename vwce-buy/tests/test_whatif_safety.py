import pytest
from vwce_buy.whatif_safety import require_whatif_postconditions

def test_whatif_postconditions_reject_working_orders_and_position_changes():
    require_whatif_postconditions(False, 2, 2)
    with pytest.raises(RuntimeError, match="working order"): require_whatif_postconditions(True, 2, 2)
    with pytest.raises(RuntimeError, match="position changed"): require_whatif_postconditions(False, 2, 3)
