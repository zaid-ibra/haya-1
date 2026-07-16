import pandas as pd
import pytest

from tradingagents.advanced_analysis import analyze_market


def candles(trend: float = 0.4, n: int = 260) -> pd.DataFrame:
    rows = []
    price = 2300.0
    for i in range(n):
        wave = ((i % 12) - 6) * 0.08
        open_ = price
        close = price + trend + wave
        rows.append({"open": open_, "high": max(open_, close) + 0.7, "low": min(open_, close) - 0.7, "close": close, "tick_volume": 100 + i})
        price = close
    return pd.DataFrame(rows)


def test_bullish_trend_scores_buy():
    result = analyze_market(candles(0.45))
    assert result.direction == "BUY"
    assert result.buy_score > result.sell_score
    assert result.indicators["ema20"] > result.indicators["ema50"] > result.indicators["ema200"]


def test_bearish_trend_scores_sell():
    result = analyze_market(candles(-0.45))
    assert result.direction == "SELL"
    assert result.sell_score > result.buy_score
    assert result.indicators["ema20"] < result.indicators["ema50"] < result.indicators["ema200"]


def test_requires_enough_candles():
    with pytest.raises(ValueError, match="At least 60"):
        analyze_market(candles(0.2, n=20))


def test_phase4_result_contains_fibonacci_and_zones():
    result = analyze_market(candles(0.35))
    module = result.fibonacci_supply_demand
    assert "fibonacci" in module
    assert "demand_zones" in module
    assert "supply_zones" in module
    assert module["fibonacci"]["direction"] in {"BULLISH", "BEARISH", "UNKNOWN"}


def test_supply_demand_scores_are_capped_confluence():
    result = analyze_market(candles(0.45))
    module = result.fibonacci_supply_demand
    assert module["buy_score"] <= 22
    assert module["sell_score"] <= 22


def test_phase5_volume_profile_uses_tick_volume():
    result = analyze_market(candles(0.25))
    module = result.volume_profile
    assert module["profile"]["available"] is True
    assert module["profile"]["poc"] is not None
    assert module["profile"]["val"] <= module["profile"]["poc"] <= module["profile"]["vah"]


def test_volume_profile_score_is_low_weight_confluence():
    result = analyze_market(candles(0.45))
    module = result.volume_profile
    assert module["buy_score"] <= 8
    assert module["sell_score"] <= 8


def test_volume_profile_gracefully_handles_missing_volume():
    frame = candles(0.2).drop(columns=["tick_volume"])
    result = analyze_market(frame)
    assert result.volume_profile["profile"]["available"] is False
    assert result.volume_profile["direction"] == "NEUTRAL"
