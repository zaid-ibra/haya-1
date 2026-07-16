# Advanced Technical Analysis — Phase 2

Phase 2 adds a deterministic Price Action Engine to the Phase 1 market-structure and momentum engine.

## Implemented patterns

- Bullish and bearish engulfing
- Bullish and bearish pin bars / wick rejection
- Inside bars and outside bars
- Bullish and bearish momentum candles
- Indecision candles
- Bullish and bearish swing-level breakouts
- Bullish and bearish fake breakouts (liquidity-style level sweeps)
- Bullish and bearish retests of broken swing levels

## Integration

`analyze_market()` now calls `analyze_price_action()` and includes the result under:

```python
result.price_action
```

Price-action scores are added to the combined BUY/SELL score, while all detected patterns and candle metrics remain visible for audit and backtesting.

## Direct usage

```python
from tradingagents.advanced_analysis import analyze_price_action

result = analyze_price_action(
    dataframe,
    last_swing_high=3350.0,
    last_swing_low=3332.0,
)
print(result.to_dict())
```

## Safety note

These rules are deterministic confirmations, not a guarantee of profitability. Before live execution, run historical backtests, walk-forward tests, spread/slippage simulation, and demo-account validation on the broker's XAUUSD feed.
