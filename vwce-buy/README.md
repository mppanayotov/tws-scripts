# vwce-buy

This package provides `vwce`, a read-only status report, and `vwce-buy`, a deliberately restricted preview/order utility for VWCE (ISIN `IE00BK5BQT80`) in EUR through the official IBKR TWS API.

## vwce status

After installing or upgrading this package in the virtual environment, run:

```powershell
.\.venv\Scripts\vwce.exe
.\.venv\Scripts\vwce.exe --json
```

With the virtual environment activated, the command is simply `vwce`. It connects to PAPER TWS at `127.0.0.1:7497`; TWS can remain in API Read-Only mode. No account ID is required, no account or portfolio data is requested, and no order or WhatIf request is sent. This reporting transport is separate from the existing order clients.

The report prints:

- `OPEN`, `CLOSED`, or `UNKNOWN`, using the resolved VWCE IBIS2 contract's IBKR `liquidHours` and exchange time zone. Unknown data is never treated as a closed market.
- Today's trading windows, elapsed trading time, remaining trading time, and percentage complete. Before the first opening it is 0%; after the final close it is 100%. Breaks do not count toward elapsed trading time. Explicit non-trading days have no progress percentage.
- Median opening price and median closing price over the last 30 completed trading sessions.
- Median daily typical price, where each day's typical price is `(high + low + close) / 3`. This is a median of daily summaries, not a median of all intraday trades or a volume-weighted price.
- The exact historical date range and the report timestamp. Text prices are displayed to two decimal places; JSON retains the calculated Decimal values as strings.

One finite IBKR historical request retrieves up to three months of daily `TRADES` bars with `useRTH=1` and `keepUpToDate=False`. The latest 30 completed dates are selected. Today's incomplete bar is excluded; today becomes eligible only after the final verified regular-hours close. IBKR `TRADES` prices are split-adjusted and are not adjusted for cash distributions. No streaming quotes, polling, cache, inferred holiday calendar, or fallback data provider is used.

Historical data requires the applicable IBKR data permissions. A permission error, timeout, invalid bar, or fewer than 30 completed sessions produces an explicit unavailable result and exit code 2. If contract and schedule data succeeded, that session status remains visible when history fails. Successful complete reports return 0. A closed session is a valid status and is not an error. Displayed historical medians are descriptive and are not an executable buy-price recommendation.

The status connection uses a separate default client ID of 74. Set `IBKR_STATUS_CLIENT_ID` or use `--client-id` if it conflicts with another API client. `--timeout` controls each finite request, defaulting to 20 seconds. `IBKR_HOST` and `IBKR_PAPER_PORT` are read, but this build still requires `127.0.0.1:7497`.

See [the proposed buy-limit mechanism](docs/buy-price-suggestion.md) for a future quote-aware suggestion. It is a proposal and is not implemented by this command.

## Status and safety

This build remains PAPER-only. The default CLI validates and records a PAPER preview, then submits no order. A separate, explicitly gated integration test implements the first normal PAPER order after a WhatIf preview. `--live` is intentionally disabled. No live order was executed while building or testing it.

The fixed order shape is BUY, one whole share, LMT, DAY, `outsideRth=False`, route `IBIS2`, and order reference `VWCE_DCA`. The price is the only trading input. It rejects non-positive or over-precision prices, values over EUR 250, non-local hosts, and live submissions. The order clients never request market data; the separate status client requests historical bars only.

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

The canonical version is mirrored in `VERSION`, `pyproject.toml`, `vwce_buy.__version__`, and the current `CHANGELOG.md` entry. Create a signed annotated tag as `v<version>` only after the matching release commit is reviewed. GitHub Actions runs the unit suite on Windows and Linux for Python 3.11 and 3.12, and rejects a pushed version tag that does not match the canonical version.

From the repository root, run the same correctness gate locally:

```powershell
.\vwce-buy\.venv\Scripts\python.exe -B scripts/repository_quality_gate.py
.\vwce-buy\.venv\Scripts\python.exe -B scripts/repository_quality_gate.py --version-only --tag v0.3.0
```

An installed MPP toolchain can be supplied with `--cache-root` after its cache preflight; its Format/Lint auto-fix findings are advisory and always continue to Test. Without that toolchain, the gate reports the unavailable formatting diagnostic and still runs version validation and the offline unit suite. The gate never runs broker integration tests.
