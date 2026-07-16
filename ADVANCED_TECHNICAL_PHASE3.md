# Advanced Technical Analysis — Phase 3 (SMC)

This phase adds deterministic, testable SMC-style confirmations to the existing engine:

- Equal highs / equal lows and liquidity pools
- Buy-side and sell-side liquidity sweeps
- Bullish and bearish fair value gaps, with fill status
- Heuristic bullish and bearish order-block zones, mitigation and invalidation state
- Premium, discount and equilibrium inside the latest dealing range
- Integration into the aggregate BUY / SELL score and TradingAgents market-analysis tool

## Important limitation

SMC labels are rule-based approximations. They are designed for confluence, research and backtesting, not as guaranteed institutional order-flow information or a standalone live-trading trigger.

## Result field

```python
result.smc
```

contains liquidity, order blocks, FVGs, dealing-range location, evidence and module scores.
