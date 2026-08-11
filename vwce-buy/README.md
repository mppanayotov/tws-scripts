# vwce-buy

`vwce-buy` is a deliberately restricted command for one VWCE (ISIN `IE00BK5BQT80`) EUR limit purchase through the official IBKR TWS API. It is not a trading bot, market-data tool, generic order client, or portfolio allocator.

## Status and safety

This build remains PAPER-only. The default CLI validates and records a PAPER preview, then submits no order. A separate, explicitly gated integration test implements the first normal PAPER order after a WhatIf preview. `--live` is intentionally disabled. No live order was executed while building or testing it.

The fixed order shape is BUY, one whole share, LMT, DAY, `outsideRth=False`, route `IBIS2`, and order reference `VWCE_DCA`. The price is the only trading input. It rejects non-positive or over-precision prices, values over EUR 250, non-local hosts, and live submissions. It never requests market data.

## Install

Install the official IBKR Python API and this package in a virtual environment:

```powershell
cd C:\Users\mppan\repos\tws-scripts\vwce-buy
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -e .
```

Install the official Interactive Brokers API from its local source distribution, then install this package. Do not substitute an unrelated PyPI package:

```powershell
cd "C:\TWS API\source\pythonclient"
C:\Users\mppan\repos\tws-scripts\vwce-buy\.venv\Scripts\python.exe -m pip install .
cd C:\Users\mppan\repos\tws-scripts\vwce-buy
.\.venv\Scripts\python.exe -m pip install -e .
```

In TWS, enable API socket clients and keep API Read-Only enabled while using this paper-only build. PAPER uses port 7497; port 7496 is rejected. Configure `IBKR_PAPER_ACCOUNT` locally for integration diagnostics; never commit account IDs or credentials.

## Usage

```powershell
vwce-buy 168.60
vwce-buy 168.60 --paper
```

The future live form is `vwce-buy 168.60 --live`; it is dangerous and intentionally disabled in this release. The PAPER transport test is intentionally not a normal CLI command. It requires all of `IBKR_RUN_PAPER_TESTS=1`, `IBKR_RUN_PAPER_ORDER=1`, `IBKR_PAPER_ACCOUNT`, and `IBKR_PAPER_ORDER_LIMIT`.

## WhatIf preview output

IBKR WhatIf commission and margin values are preview data from IBKR. Unavailable values display as `N/A`. A callback status such as `PreSubmitted` is not a working order; the integration independently checks open orders and positions afterward. A WhatIf preview is neither an execution nor a fill.

Audit records are JSON Lines under the user data directory (`%LOCALAPPDATA%\\tws-scripts\\audit` on Windows, or `$XDG_DATA_HOME/tws-scripts/audit` on other systems). Account IDs are masked. Paper executions are simulated; live execution uses real money when later enabled. No market-data subscription is required because no market-data API is called.

## Limitations

The normal PAPER-order integration uses a fresh normal-order ID after the WhatIf ID, collects status and execution callbacks, and reconciles open orders and positions. Each explicit submission invocation sends one order. It does not cancel, modify, reprice, request market data, or expose LIVE order submission. Integration tests remain opt-in and must never target LIVE TWS.

## Versioning and CI

The canonical version is mirrored in `VERSION`, `pyproject.toml`, `vwce_buy.__version__`, and the current `CHANGELOG.md` entry. Create a signed annotated tag as `v<version>` only after the matching release commit is reviewed. GitHub Actions runs the unit suite on Windows and Linux for Python 3.11 and 3.12, and rejects a pushed version tag that does not match `VERSION` and `pyproject.toml`.
