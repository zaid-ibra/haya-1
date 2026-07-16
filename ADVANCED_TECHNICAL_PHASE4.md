# Advanced Technical Analysis — Phase 4

Phase 4 adds deterministic Fibonacci retracement and supply/demand-zone analysis.

## Fibonacci

- Uses the latest confirmed swing pair.
- Calculates 0.236, 0.382, 0.5, 0.618, 0.705 and 0.786 retracement levels.
- Calculates 1.272 and 1.618 extensions.
- Gives limited confluence when price is inside the 0.618–0.705 golden zone.

## Supply and Demand

- Detects compact base candles followed by directional displacement.
- Tracks active, fresh, touched and invalidated zones.
- Scores only current interaction with an active zone.
- Weights are capped so zones do not duplicate SMC order-block scoring.

Results are available under:

```python
result.fibonacci_supply_demand
```

These are algorithmic approximations for research and backtesting, not guaranteed institutional order-flow labels or standalone trade instructions.
