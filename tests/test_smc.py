import pandas as pd

from tradingagents.advanced_analysis.smc import analyze_smc


def frame_from_rows(rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"])


def neutral_frame(n=70):
    rows=[]
    price=100.0
    for i in range(n):
        close=price + (0.15 if i % 4 < 2 else -0.1)
        rows.append([price, max(price, close)+0.35, min(price, close)-0.35, close, 100+i])
        price=close
    return frame_from_rows(rows)


def test_sell_side_liquidity_sweep_scores_buy():
    frame=neutral_frame()
    frame.loc[20, ["open","high","low","close"]]=[100.8,101.2,99.0,100.4]
    frame.loc[40, ["open","high","low","close"]]=[100.5,101.0,99.05,100.2]
    frame.loc[len(frame)-1, ["open","high","low","close"]]=[99.5,100.2,98.5,99.7]
    result=analyze_smc(frame, swing_highs=[10,30], swing_lows=[20,40])
    assert any(x["type"] == "SELL_SIDE_SWEEP" for x in result.liquidity["sweeps"])
    assert result.buy_score >= 24


def test_bullish_fvg_is_detected():
    frame=neutral_frame()
    i=len(frame)-3
    frame.loc[i, ["open","high","low","close"]]=[100.0,100.5,99.7,100.3]
    frame.loc[i+1, ["open","high","low","close"]]=[100.4,102.0,100.3,101.8]
    frame.loc[i+2, ["open","high","low","close"]]=[101.4,102.2,101.1,101.9]
    result=analyze_smc(frame, swing_highs=[15,35], swing_lows=[20,40])
    assert any(x["type"] == "BULLISH_FVG" for x in result.fair_value_gaps)


def test_dealing_range_labels_discount():
    frame=neutral_frame()
    frame.loc[10, "high"] = 110.0
    frame.loc[20, "low"] = 90.0
    frame.loc[len(frame)-1, ["open","high","low","close"]]=[93.0,94.0,92.0,93.0]
    result=analyze_smc(frame, swing_highs=[10], swing_lows=[20])
    assert result.dealing_range["position"] == "DISCOUNT"
    assert result.buy_score >= 8
