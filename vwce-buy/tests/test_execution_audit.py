import pytest
from vwce_buy.audit import execution_event

def test_requested_and_execution_exchanges_are_distinct_fields():
    assert execution_event(requested_exchange="IBIS2")["execution_exchange"] is None
    with pytest.raises(ValueError): execution_event(requested_exchange="IBIS2", execution_exchange="IBIS2")
