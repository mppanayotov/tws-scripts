# Changelog

## 0.3.0

- Add the read-only `vwce` command for IBIS2 session status, daily trading progress, and 30 completed-session historical price medians.
- Keep historical reporting separate from the existing PAPER order clients and preserve disabled LIVE trading.

## 0.2.1

- Remove interactive confirmation and the single-attempt latch from the explicitly gated PAPER integration path.

## 0.2.0

- Add the tightly gated, human-confirmed PAPER normal-order implementation.
- Add GitHub Actions unit-test and version-tag validation.

## 0.1.0

- Initial PAPER read-only and WhatIf safety foundation.
