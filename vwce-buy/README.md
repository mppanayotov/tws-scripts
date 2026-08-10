# vwce-buy

`vwce-buy` is a deliberately restricted command for one VWCE (ISIN `IE00BK5BQT80`) EUR limit purchase through the official IBKR TWS API. It is not a trading bot, market-data tool, generic order client, or portfolio allocator.

## Status and safety

This initial build is paper-only: its default path validates and records a PAPER preview, then submits no order. `--live` requires the exact typed phrase but is intentionally disabled. No live order was executed while building or testing it.

The fixed order shape is BUY, one whole share, LMT, DAY, `outsideRth=False`, route `IBIS2`, and order reference `VWCE_DCA`. The price is the only trading input. It rejects non-positive or over-precision prices, values over EUR 250, non-local hosts, and live submissions. It never requests market data.

## Install

Install the official IBKR Python API and this package in a virtual environment:

```powershell
cd C:\Users\mppan\repos\tws-scripts\vwce-buy
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -e .
```

The project pins the official `ibapi==9.81.1.post1`. In TWS, enable API socket clients and keep API Read-Only enabled while using this paper-only build. TWS paper commonly uses port 7497; live commonly uses 7496. Both may be changed with `IBKR_PAPER_PORT` and `IBKR_LIVE_PORT`. Configure an account locally with `IBKR_ACCOUNT`; never commit account IDs or credentials.

## Usage

```powershell
vwce-buy 168.60
vwce-buy 168.60 --paper
```

The future live form is `vwce-buy 168.60 --live`; it is dangerous and intentionally disabled in this release.

Audit records are JSON Lines under the user data directory (`%LOCALAPPDATA%\\tws-scripts\\audit` on Windows, or `$XDG_DATA_HOME/tws-scripts/audit` on other systems). Account IDs are masked. Paper executions are simulated; live execution uses real money when later enabled. No market-data subscription is required because no market-data API is called.

## Limitations

The offline build does not yet collect contract details, account cash, open orders, positions, session schedules, or WhatIf callbacks from a paper TWS instance. Therefore it fails closed by not submitting. A future activation must add and test those callback collectors before paper submission is enabled; integration tests must remain opt-in through `IBKR_RUN_PAPER_TESTS=1` and must never target live TWS.
