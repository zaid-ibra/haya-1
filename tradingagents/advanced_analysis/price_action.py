from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class PriceActionSignal:
    direction: str
    buy_score: float
    sell_score: float
    confidence: float
    patterns: list[str]
    evidence: list[str]
    candle_context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _metrics(row: pd.Series) -> dict[str, float]:
    open_ = float(row["open"])
    high = float(row["high"])
    low = float(row["low"])
    close = float(row["close"])
    candle_range = max(high - low, 1e-12)
    body = abs(close - open_)
    return {
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "range": candle_range,
        "body": body,
        "body_ratio": body / candle_range,
        "upper_wick": high - max(open_, close),
        "lower_wick": min(open_, close) - low,
        "bullish": float(close > open_),
        "bearish": float(close < open_),
    }


def _is_bullish_engulfing(prev: dict[str, float], cur: dict[str, float]) -> bool:
    return bool(
        prev["bearish"]
        and cur["bullish"]
        and cur["open"] <= prev["close"]
        and cur["close"] >= prev["open"]
        and cur["body"] > prev["body"]
    )


def _is_bearish_engulfing(prev: dict[str, float], cur: dict[str, float]) -> bool:
    return bool(
        prev["bullish"]
        and cur["bearish"]
        and cur["open"] >= prev["close"]
        and cur["close"] <= prev["open"]
        and cur["body"] > prev["body"]
    )


def _is_bullish_pin_bar(cur: dict[str, float]) -> bool:
    return bool(
        cur["lower_wick"] >= max(cur["body"] * 2.0, cur["range"] * 0.5)
        and cur["upper_wick"] <= cur["range"] * 0.25
        and cur["close"] >= cur["low"] + cur["range"] * 0.55
    )


def _is_bearish_pin_bar(cur: dict[str, float]) -> bool:
    return bool(
        cur["upper_wick"] >= max(cur["body"] * 2.0, cur["range"] * 0.5)
        and cur["lower_wick"] <= cur["range"] * 0.25
        and cur["close"] <= cur["low"] + cur["range"] * 0.45
    )


def _is_inside_bar(prev: dict[str, float], cur: dict[str, float]) -> bool:
    return cur["high"] < prev["high"] and cur["low"] > prev["low"]


def _is_outside_bar(prev: dict[str, float], cur: dict[str, float]) -> bool:
    return cur["high"] > prev["high"] and cur["low"] < prev["low"]


def analyze_price_action(
    frame: pd.DataFrame,
    *,
    last_swing_high: float | None = None,
    last_swing_low: float | None = None,
    average_range_period: int = 20,
    level_tolerance: float = 0.0015,
) -> PriceActionSignal:
    """Analyze the latest closed candles using deterministic price-action rules.

    The function expects a normalized OHLC DataFrame. Scores are intentionally
    bounded and should be treated as confirmation, not as a standalone trade trigger.
    """
    if len(frame) < max(average_range_period + 2, 5):
        raise ValueError("Not enough candles for price-action analysis")

    previous = _metrics(frame.iloc[-2])
    current = _metrics(frame.iloc[-1])
    third = _metrics(frame.iloc[-3])
    ranges = (frame["high"] - frame["low"]).tail(average_range_period)
    average_range = max(float(ranges.mean()), 1e-12)

    buy = sell = 0.0
    patterns: list[str] = []
    evidence: list[str] = []

    if _is_bullish_engulfing(previous, current):
        buy += 18
        patterns.append("BULLISH_ENGULFING")
        evidence.append("Bullish engulfing candle closed over the prior real body")
    elif _is_bearish_engulfing(previous, current):
        sell += 18
        patterns.append("BEARISH_ENGULFING")
        evidence.append("Bearish engulfing candle closed under the prior real body")

    if _is_bullish_pin_bar(current):
        buy += 15
        patterns.append("BULLISH_PIN_BAR")
        evidence.append("Long lower-wick rejection on the latest candle")
    elif _is_bearish_pin_bar(current):
        sell += 15
        patterns.append("BEARISH_PIN_BAR")
        evidence.append("Long upper-wick rejection on the latest candle")

    if _is_inside_bar(previous, current):
        patterns.append("INSIDE_BAR")
        evidence.append("Latest candle is contained inside the previous candle")
    if _is_outside_bar(previous, current):
        patterns.append("OUTSIDE_BAR")
        if current["bullish"]:
            buy += 10
        elif current["bearish"]:
            sell += 10
        evidence.append("Latest candle expanded beyond both sides of the previous candle")

    if current["range"] >= average_range * 1.5 and current["body_ratio"] >= 0.65:
        if current["bullish"]:
            buy += 12
            patterns.append("BULLISH_MOMENTUM_CANDLE")
            evidence.append("Bullish expansion candle has a large body and above-average range")
        elif current["bearish"]:
            sell += 12
            patterns.append("BEARISH_MOMENTUM_CANDLE")
            evidence.append("Bearish expansion candle has a large body and above-average range")
    elif current["body_ratio"] <= 0.2:
        patterns.append("INDECISION_CANDLE")
        evidence.append("Latest candle has a small real body relative to its range")

    # Breakout and fake-breakout logic uses the most recent confirmed swing levels.
    if last_swing_high is not None:
        high_level = float(last_swing_high)
        if current["close"] > high_level and previous["close"] <= high_level:
            buy += 20
            patterns.append("BULLISH_BREAKOUT")
            evidence.append("Latest candle closed above the confirmed swing high")
        elif current["high"] > high_level and current["close"] < high_level:
            sell += 16
            patterns.append("BEARISH_FAKE_BREAKOUT")
            evidence.append("Price swept the swing high but closed back below it")

        tolerance = max(abs(high_level) * level_tolerance, average_range * 0.15)
        if (
            third["close"] > high_level
            and previous["low"] <= high_level + tolerance
            and current["close"] > high_level
        ):
            buy += 12
            patterns.append("BULLISH_RETEST")
            evidence.append("Broken swing high was retested and held as support")

    if last_swing_low is not None:
        low_level = float(last_swing_low)
        if current["close"] < low_level and previous["close"] >= low_level:
            sell += 20
            patterns.append("BEARISH_BREAKOUT")
            evidence.append("Latest candle closed below the confirmed swing low")
        elif current["low"] < low_level and current["close"] > low_level:
            buy += 16
            patterns.append("BULLISH_FAKE_BREAKOUT")
            evidence.append("Price swept the swing low but closed back above it")

        tolerance = max(abs(low_level) * level_tolerance, average_range * 0.15)
        if (
            third["close"] < low_level
            and previous["high"] >= low_level - tolerance
            and current["close"] < low_level
        ):
            sell += 12
            patterns.append("BEARISH_RETEST")
            evidence.append("Broken swing low was retested and held as resistance")

    total = buy + sell
    if total == 0:
        direction, confidence = "NEUTRAL", 0.0
    elif buy > sell:
        direction, confidence = "BUY", round(100 * buy / total, 2)
    elif sell > buy:
        direction, confidence = "SELL", round(100 * sell / total, 2)
    else:
        direction, confidence = "NEUTRAL", 50.0

    return PriceActionSignal(
        direction=direction,
        buy_score=buy,
        sell_score=sell,
        confidence=confidence,
        patterns=patterns,
        evidence=evidence,
        candle_context={
            "average_range": round(average_range, 6),
            "latest_range": round(current["range"], 6),
            "latest_body_ratio": round(current["body_ratio"], 4),
            "latest_upper_wick": round(current["upper_wick"], 6),
            "latest_lower_wick": round(current["lower_wick"], 6),
        },
    )
