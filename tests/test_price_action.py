import pandas as pd

from tradingagents.advanced_analysis import analyze_price_action


def base_candles(n: int = 25) -> pd.DataFrame:
    rows = []
    price = 100.0
    for i in range(n):
        open_ = price
        close = price + (0.12 if i % 2 == 0 else -0.05)
        rows.append({
            "open": open_,
            "high": max(open_, close) + 0.35,
            "low": min(open_, close) - 0.35,
            "close": close,
            "volume": 100 + i,
        })
        price = close
    return pd.DataFrame(rows)


def test_bullish_engulfing_is_detected():
    frame = base_candles()
    frame.loc[len(frame) - 2, ["open", "high", "low", "close"]] = [101.0, 101.2, 99.8, 100.0]
    frame.loc[len(frame) - 1, ["open", "high", "low", "close"]] = [99.8, 101.7, 99.6, 101.4]
    result = analyze_price_action(frame)
    assert "BULLISH_ENGULFING" in result.patterns
    assert result.buy_score > result.sell_score


def test_bearish_pin_bar_is_detected():
    frame = base_candles()
    frame.loc[len(frame) - 1, ["open", "high", "low", "close"]] = [100.1, 103.2, 99.9, 100.0]
    result = analyze_price_action(frame)
    assert "BEARISH_PIN_BAR" in result.patterns
    assert result.sell_score > result.buy_score


def test_bullish_breakout_is_detected():
    frame = base_candles()
    frame.loc[len(frame) - 2, ["open", "high", "low", "close"]] = [100.0, 100.8, 99.7, 100.4]
    frame.loc[len(frame) - 1, ["open", "high", "low", "close"]] = [100.3, 102.2, 100.1, 101.8]
    result = analyze_price_action(frame, last_swing_high=101.0)
    assert "BULLISH_BREAKOUT" in result.patterns
    assert result.buy_score >= 20


def test_swing_high_sweep_is_fake_breakout():
    frame = base_candles()
    frame.loc[len(frame) - 1, ["open", "high", "low", "close"]] = [100.7, 102.0, 100.0, 100.5]
    result = analyze_price_action(frame, last_swing_high=101.0)
    assert "BEARISH_FAKE_BREAKOUT" in result.patterns
    assert result.sell_score > 0
