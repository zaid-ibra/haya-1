from __future__ import annotations

import io
import json
from typing import Annotated

import pandas as pd
from langchain_core.tools import tool

from tradingagents.advanced_analysis import analyze_market


@tool
def get_advanced_technical_analysis(
    ohlcv_csv: Annotated[str, "CSV text containing at least open, high, low, close columns"],
    swing_window: Annotated[int, "Candles on each side used to validate a swing"] = 3,
) -> str:
    """Analyze OHLCV candles using market structure, EMA 20/50/200, MACD, RSI divergence, price action, deterministic SMC-style liquidity/order-block/FVG analysis, Fibonacci retracement, supply/demand zones, and Volume Profile (POC/VAH/VAL/HVN/LVN)."""
    try:
        frame = pd.read_csv(io.StringIO(ohlcv_csv))
        result = analyze_market(frame, swing_window=swing_window)
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
