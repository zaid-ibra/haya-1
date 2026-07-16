# TradingAgents Gold Platform — Core V1

This build adds deterministic XAUUSD/M5 analysis layers to TradingAgents:

1. Market structure, EMA, MACD, RSI divergence
2. Price action
3. SMC: liquidity, FVG, order blocks, premium/discount
4. Fibonacci and supply/demand
5. Approximate candle Volume Profile
6. ICT heuristics: kill zones, OTE, session sweep/Judas candidate
7. Wyckoff heuristics: spring, upthrust, SOS/SOW candidates
8. Elliott swing-sequence candidates
9. Final decision gate
10. Structural risk planning
11. MT5 dry-run/live execution adapter
12. Walk-forward backtest utility

## Safety default

`run_gold_cycle(..., dry_run=True)` never sends an order. Live order submission requires `dry_run=False`, MT5 availability, valid broker symbol settings, and separate demo validation.

## Important limitations

SMC, ICT, Wyckoff, and Elliott labels are deterministic approximations. Tick volume is broker activity, not centralized gold-market volume. The default point value must be configured for the broker before position sizing can be trusted.
