import pytest
from vwce_buy.config import Settings

def test_paper_configuration_cannot_select_live_mode_or_port(monkeypatch):
    assert Settings.from_environment(live=False, host=None, client_id=None, account=None).port == 7497
    with pytest.raises(ValueError): Settings.from_environment(live=True, host=None, client_id=None, account=None)
    monkeypatch.setenv("IBKR_PAPER_PORT", "7496")
    with pytest.raises(ValueError): Settings.from_environment(live=False, host=None, client_id=None, account=None)
    with pytest.raises(ValueError): Settings.from_environment(live=False, host="192.0.2.1", client_id=None, account=None)
    with pytest.raises(ValueError): Settings.from_environment(live=False, host=None, client_id=0, account=None)
    monkeypatch.delenv("IBKR_PAPER_PORT")
    assert Settings.from_environment(live=False, host=None, client_id=42, account=None).client_id == 42
