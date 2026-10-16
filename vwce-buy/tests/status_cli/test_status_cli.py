import json

from vwce_buy import status_cli


def test_cli_structured_exit_codes_and_read_only_client(monkeypatch, capsys):
    opened = []

    class FakeMarketClient:
        def __init__(self, host, port, client_id, timeout):
            opened.append((host, port, client_id, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    monkeypatch.setattr(status_cli, "VwceMarketClient", FakeMarketClient)
    report = {
        "symbol": "VWCE",
        "exchange": "IBIS2",
        "currency": "EUR",
        "isin": "IE00BK5BQT80",
        "as_of": "2026-10-15T12:00:00+00:00",
        "session": {
            "state": "OPEN",
            "phase": "OPEN",
            "time_zone": "Europe/Berlin",
            "windows": [],
            "elapsed_seconds": 18000,
            "total_seconds": 28800,
            "progress_percent": 62.5,
            "next_open": None,
        },
        "history": None,
        "errors": [],
    }
    monkeypatch.setattr(status_cli, "collect_status", lambda client: report)
    assert status_cli.main(["--json", "--client-id", "75", "--timeout", "4"]) == 0
    assert json.loads(capsys.readouterr().out) == report
    assert opened == [("127.0.0.1", 7497, 75, 4)]

    report["errors"] = ["Historical medians unavailable: permission denied"]
    assert status_cli.main(["--json"]) == 2
    partial = json.loads(capsys.readouterr().out)
    assert partial["session"]["state"] == "OPEN"
    assert partial["history"] is None
    assert "permission denied" in partial["errors"][0]

    from vwce_buy.market_client import VwceMarketClient

    monkeypatch.setattr(status_cli, "VwceMarketClient", VwceMarketClient)
    monkeypatch.setenv("IBKR_PAPER_PORT", "7496")
    assert status_cli.main(["--json"]) == 2
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["session"]["state"] == "UNKNOWN"
    assert "127.0.0.1:7497" in rejected["errors"][0]
