# Proposed automatic buy-limit suggestion

The `vwce` status command reports historical context. It does not suggest or submit an order in this release. The following mechanism is a proposed future addition, with no backtested execution or return claims.

| #   | Mechanism                                                                 | Benefit and tradeoff                                                                                             | Actionable | Preferred |
| --- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------- | --------- |
| 1   | Use a fresh IBIS2 bid/ask midpoint, rounded down to an allowed order tick | Produces an indicative limit tied to the current spread; requires live quote permissions and may remain unfilled | Yes        | Yes       |
| 2   | Use the 30-session median typical price as the buy limit                  | Reuses historical data, but can be far from the current market and has no established execution advantage        | Yes        | No        |

## Mechanism 1

1. Resolve the existing VWCE ISIN, EUR, and IBIS2 contract. Require the current IBKR regular-hours session to be `OPEN`.
2. Briefly collect live bid and ask updates from the same exchange using a separate read-only quote client. Require IBKR market-data type 1 (live), positive prices and sizes, bid strictly below ask, and a bounded capture with both sides received recently. Delayed, frozen, unavailable, and stale data produce no suggestion. Local callback receipt time alone does not prove exchange freshness; require broker/exchange timestamps and report that evidence. If the entitled quote API cannot establish freshness, produce no suggestion.
3. Fetch the IBIS2 market rule using the contract's matching market-rule ID. Do not assume `minTick` covers every price tier.
4. Compute `midpoint = (bid + ask) / 2`. Reject an unusually wide spread. An initial configurable threshold could be a spread of at most 0.15% of midpoint; this is a proposed policy parameter requiring evaluation, not an exchange rule or an established optimal setting.
5. Select the largest permitted order price at or below the midpoint. Respect the applicable price tier and the existing two-decimal price contract. If no representable valid tick exists, produce no suggestion rather than rounding up or changing the contract.
6. Display the candidate, bid/ask, quote source/time, spread, tick, and distance from the three historical medians. Keep the EUR 250 maximum and other order gates. A future explicit order action must revalidate the quote, session, cash, duplicates, contract, and price; displaying a suggestion must never submit, cancel, modify, or repeatedly reprice an order.

For an illustrative bid of EUR 168.60, ask of EUR 168.64, and valid tick of EUR 0.01, the midpoint candidate is EUR 168.62. This is an example, not a current VWCE quote. A midpoint buy limit can remain unfilled; crossing to the ask trades execution likelihood against price and would need a separately selected policy.

The historical medians are context, not price forecasts or automatic caps. A static 30-session cap can prevent purchases throughout a rising market. Before calling either mechanism better, compare them against explicit alternatives in PAPER with timestamped quotes, fill rates, time to fill, spread costs, and the number of unfilled DAY orders. Historical daily bars alone cannot establish achievable midpoint fills.

## Sources

- [IBKR historical bars](https://www.interactivebrokers.com/docs/tws-api/doc/md/historical-bars): `TRADES` OHLC, regular-hours selection, one-time history, and split/dividend adjustment semantics.
- [IBKR streaming data](https://www.interactivebrokers.com/docs/tws-api/doc/md/streaming-data): live bid/ask callbacks, snapshots, and subscription requirements.
- [IBKR delayed data](https://www.interactivebrokers.com/docs/tws-api/doc/md/delayed-data): live, frozen, delayed, and delayed-frozen market-data types.
- [IBKR ContractDetails reference](https://interactivebrokers.github.io/tws-api/classIBApi_1_1ContractDetails.html): exchange-specific liquid hours, market-rule IDs, and price increments.
