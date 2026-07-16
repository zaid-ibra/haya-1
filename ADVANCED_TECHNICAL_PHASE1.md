# Advanced Technical Analysis — Phase 1

This phase adds a deterministic OHLCV analysis engine before the LLM layer.

## Included

- Swing-high and swing-low detection
- Bullish/Bearish BOS and CHoCH
- EMA 20/50/200 alignment and EMA20/EMA50 crossover
- MACD line, signal, histogram, and momentum scoring
- Regular and hidden RSI divergence
- BUY/SELL/HOLD score, confidence, evidence, levels, and indicator values
- `get_advanced_technical_analysis` LangChain tool
- Market Analyst registration

## Direct Python usage

```python
import pandas as pd
from tradingagents.advanced_analysis import analyze_market

frame = pd.read_csv("xauusd_m5.csv")
result = analyze_market(frame)
print(result.to_dict())
```

Required columns: `open`, `high`, `low`, `close`. `volume` is optional; MT5 `tick_volume` is accepted.
At least 60 candles are required; 250–500 M5 candles are recommended.

## Important

This phase produces technical evidence, not guaranteed profitable trades. Backtesting, spread/slippage modeling, risk limits, and demo validation are required before live execution.
