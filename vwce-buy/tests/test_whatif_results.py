from types import SimpleNamespace
from vwce_buy.ibkr_client import PaperWhatIfClient

def test_whatif_terminal_errors_complete_immediately_and_results_are_truthful(monkeypatch):
    client = PaperWhatIfClient("127.0.0.1", 7497, 42); client.callbacks.next_order_id = 11
    order = SimpleNamespace(whatIf=True); contract = SimpleNamespace()
    monkeypatch.setattr(client, "_send_whatif", lambda order_id, contract, order: client.callbacks.error(order_id, 0, 321, "API interface is currently in Read-Only mode"))
    blocked = client.preview_vwce_order(contract, order, timeout=0.01)
    assert blocked.outcome == "BLOCKED" and blocked.reason == "TWS_READ_ONLY" and blocked.error["code"] == 321
    client.callbacks.next_order_id = 12
    monkeypatch.setattr(client, "_send_whatif", lambda order_id, contract, order: client.callbacks.error(order_id, 0, 413, "What-if order should have the transmit flag set to true"))
    rejected = client.preview_vwce_order(contract, order, timeout=0.01)
    assert rejected.outcome == "REJECTED" and rejected.reason == "WHATIF_TRANSMIT_INVALID"
    client.callbacks.next_order_id = 13
    monkeypatch.setattr(client, "_send_whatif", lambda *args: None)
    assert client.preview_vwce_order(contract, order, timeout=0.001).outcome == "TIMEOUT"
    client.callbacks.next_order_id = 14
    monkeypatch.setattr(client, "_send_whatif", lambda order_id, contract, order: client.callbacks.openOrder(order_id, contract, order, SimpleNamespace(status="PreSubmitted")))
    assert client.preview_vwce_order(contract, order, timeout=0.01).outcome == "PREVIEW_RECEIVED"
    client.callbacks.whatif_done[99] = __import__("threading").Event()
    client.callbacks.error(98, 0, 2104, "farm connected")
    client.callbacks.error(98, 0, 200, "other request failed")
    assert not client.callbacks.whatif_done[99].is_set()
