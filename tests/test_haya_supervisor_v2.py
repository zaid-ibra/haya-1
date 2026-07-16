from tradingagents.advanced_analysis.decision import make_decision


def test_supervisor_approves_broad_bullish_trend_agreement():
    result = make_decision(
        buy_score=92,
        sell_score=18,
        evidence=[
            "EMA 20/50/200 bullish alignment",
            "MACD bullish momentum",
            "Bullish BOS",
            "Bullish engulfing candle closed over the prior real body",
            "Sell-side liquidity sweep",
            "Price is interacting with a valid bullish order block",
        ],
    )
    assert result.approved is True
    assert result.action == "BUY"
    assert result.thresholds["supervisor_version"] == "2.0"
    assert result.thresholds["agreement"] >= 2


def test_supervisor_rejects_range_signal_with_low_confidence():
    result = make_decision(
        buy_score=47,
        sell_score=30,
        evidence=[
            "MACD bullish momentum",
            "Price is inside the bullish ICT OTE zone",
            "Price is trading below the Volume Profile point of control",
        ],
    )
    assert result.approved is False
    assert result.action == "HOLD"
    assert result.thresholds["regime"] == "RANGE"


def test_supervisor_rejects_strong_core_conflict():
    result = make_decision(
        buy_score=90,
        sell_score=25,
        evidence=[
            "EMA 20/50/200 bullish alignment",
            "MACD bullish momentum",
            "Bearish BOS",
            "Bearish engulfing candle closed under the prior real body",
            "Price is interacting with a valid bearish order block",
        ],
    )
    assert result.approved is False
    assert result.action == "HOLD"
    assert result.thresholds["strong_core_opposition"] is True
