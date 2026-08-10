from vwce_buy.cli import main

def test_paper_default_and_live_disabled(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("vwce_buy.cli.append_audit", lambda record: tmp_path / "audit.jsonl")
    assert main(["168.60"]) == 0
    monkeypatch.setattr("builtins.input", lambda _: "BUY 1 VWCE AT 168.60")
    assert main(["168.60", "--live"]) == 2
    assert "PAPER safety preview" in capsys.readouterr().out
