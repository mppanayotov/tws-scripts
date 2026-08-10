from types import SimpleNamespace
import pytest
from vwce_buy.ibkr_client import _ReadOnlyCallbacks, ReadOnlyPaperClient

def test_callback_collectors_complete_accumulate_and_propagate_errors():
    callbacks = _ReadOnlyCallbacks(); callbacks.contract_done[11] = __import__("threading").Event()
    callbacks.contractDetails(11, SimpleNamespace(contract=SimpleNamespace(conId=1)))
    callbacks.contractDetails(11, SimpleNamespace(contract=SimpleNamespace(conId=2)))
    callbacks.contractDetailsEnd(11)
    assert len(callbacks.store.details[11]) == 2 and callbacks.contract_done[11].is_set()
    callbacks.error(11, 0, 2104, "farm ok"); assert 11 not in callbacks.store.errors
    callbacks.error(11, 0, 200, "bad contract", "{}"); assert callbacks.store.errors[11][0]["advanced_reject"] == "{}"
    client = ReadOnlyPaperClient("127.0.0.1", 7497)
    event = __import__("threading").Event()
    with pytest.raises(RuntimeError, match="Diagnostics"): client._wait(event, "contractDetailsEnd", 0.001, 11)
