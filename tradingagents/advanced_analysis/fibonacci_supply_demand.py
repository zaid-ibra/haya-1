from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class FibonacciSupplyDemandSignal:
    direction: str
    buy_score: float
    sell_score: float
    confidence: float
    evidence: list[str]
    fibonacci: dict[str, Any]
    demand_zones: list[dict[str, Any]]
    supply_zones: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _atr(frame: pd.DataFrame, period: int = 14) -> float:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    value = float(true_range.tail(period).mean())
    return max(value, 1e-12)


def _active_swing(frame: pd.DataFrame, swing_highs: list[int], swing_lows: list[int]) -> tuple[int, int, str] | None:
    if not swing_highs or not swing_lows:
        return None
    high_index = swing_highs[-1]
    low_index = swing_lows[-1]
    if low_index < high_index:
        return low_index, high_index, "BULLISH"
    return high_index, low_index, "BEARISH"


def _fibonacci(
    frame: pd.DataFrame,
    swing_highs: list[int],
    swing_lows: list[int],
    atr: float,
) -> tuple[dict[str, Any], float, float, list[str]]:
    swing = _active_swing(frame, swing_highs, swing_lows)
    if swing is None:
        return {"direction": "UNKNOWN", "levels": {}}, 0.0, 0.0, []

    first, second, direction = swing
    high = float(max(frame.at[first, "high"], frame.at[second, "high"]))
    low = float(min(frame.at[first, "low"], frame.at[second, "low"]))
    span = high - low
    if span <= 0:
        return {"direction": "UNKNOWN", "levels": {}}, 0.0, 0.0, []

    ratios = (0.236, 0.382, 0.5, 0.618, 0.705, 0.786)
    if direction == "BULLISH":
        levels = {str(ratio): high - span * ratio for ratio in ratios}
        extensions = {"1.272": high + span * 0.272, "1.618": high + span * 0.618}
    else:
        levels = {str(ratio): low + span * ratio for ratio in ratios}
        extensions = {"1.272": low - span * 0.272, "1.618": low - span * 0.618}

    latest = float(frame.iloc[-1]["close"])
    golden_low = min(levels["0.618"], levels["0.705"])
    golden_high = max(levels["0.618"], levels["0.705"])
    tolerance = atr * 0.2
    in_golden_zone = golden_low - tolerance <= latest <= golden_high + tolerance
    buy = sell = 0.0
    evidence: list[str] = []

    if in_golden_zone and direction == "BULLISH":
        buy += 10
        evidence.append("Price is retracing into the bullish Fibonacci 0.618-0.705 golden zone")
    elif in_golden_zone and direction == "BEARISH":
        sell += 10
        evidence.append("Price is retracing into the bearish Fibonacci 0.618-0.705 golden zone")

    return {
        "direction": direction,
        "swing_start_index": int(first),
        "swing_end_index": int(second),
        "low": round(low, 6),
        "high": round(high, 6),
        "levels": {key: round(value, 6) for key, value in levels.items()},
        "extensions": {key: round(value, 6) for key, value in extensions.items()},
        "golden_zone": {"low": round(golden_low, 6), "high": round(golden_high, 6)},
        "in_golden_zone": in_golden_zone,
    }, buy, sell, evidence


def _zones(
    frame: pd.DataFrame,
    atr: float,
    lookback: int = 100,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float, float, list[str]]:
    demand: list[dict[str, Any]] = []
    supply: list[dict[str, Any]] = []
    start = max(1, len(frame) - lookback)

    for i in range(start, len(frame) - 2):
        base = frame.iloc[i]
        next_one = frame.iloc[i + 1]
        next_two = frame.iloc[i + 2]
        base_range = float(base["high"] - base["low"])
        if base_range > atr * 0.9:
            continue

        upward_displacement = float(next_two["close"] - base["high"])
        downward_displacement = float(base["low"] - next_two["close"])

        if upward_displacement >= atr * 0.8 and float(next_one["close"]) > float(next_one["open"]):
            low = float(base["low"])
            high = max(float(base["open"]), float(base["close"]))
            invalidated = bool((frame["close"].iloc[i + 3 :] < low).any()) if i + 3 < len(frame) else False
            touches = int(((frame["low"].iloc[i + 3 :] <= high) & (frame["high"].iloc[i + 3 :] >= low)).sum()) if i + 3 < len(frame) else 0
            demand.append({
                "type": "DEMAND",
                "low": round(low, 6),
                "high": round(high, 6),
                "origin_index": i,
                "touches": touches,
                "fresh": touches == 0,
                "invalidated": invalidated,
                "strength": round(min(100.0, 50 + upward_displacement / atr * 20), 2),
            })

        if downward_displacement >= atr * 0.8 and float(next_one["close"]) < float(next_one["open"]):
            low = min(float(base["open"]), float(base["close"]))
            high = float(base["high"])
            invalidated = bool((frame["close"].iloc[i + 3 :] > high).any()) if i + 3 < len(frame) else False
            touches = int(((frame["low"].iloc[i + 3 :] <= high) & (frame["high"].iloc[i + 3 :] >= low)).sum()) if i + 3 < len(frame) else 0
            supply.append({
                "type": "SUPPLY",
                "low": round(low, 6),
                "high": round(high, 6),
                "origin_index": i,
                "touches": touches,
                "fresh": touches == 0,
                "invalidated": invalidated,
                "strength": round(min(100.0, 50 + downward_displacement / atr * 20), 2),
            })

    active_demand = [zone for zone in demand if not zone["invalidated"]][-5:]
    active_supply = [zone for zone in supply if not zone["invalidated"]][-5:]
    latest = frame.iloc[-1]
    buy = sell = 0.0
    evidence: list[str] = []

    for zone in reversed(active_demand):
        overlaps = float(latest["low"]) <= zone["high"] and float(latest["high"]) >= zone["low"]
        if overlaps:
            buy += 12 if zone["fresh"] else 7
            evidence.append("Price is interacting with an active demand zone")
            break

    for zone in reversed(active_supply):
        overlaps = float(latest["low"]) <= zone["high"] and float(latest["high"]) >= zone["low"]
        if overlaps:
            sell += 12 if zone["fresh"] else 7
            evidence.append("Price is interacting with an active supply zone")
            break

    return active_demand, active_supply, buy, sell, evidence


def analyze_fibonacci_supply_demand(
    frame: pd.DataFrame,
    *,
    swing_highs: list[int],
    swing_lows: list[int],
) -> FibonacciSupplyDemandSignal:
    """Analyze Fibonacci retracement and algorithmic supply/demand confluence.

    Supply/demand zones are deterministic approximations based on consolidation
    followed by displacement. Their score is intentionally capped to avoid
    double-counting SMC order-block evidence.
    """
    atr = _atr(frame)
    fibonacci, fib_buy, fib_sell, fib_evidence = _fibonacci(frame, swing_highs, swing_lows, atr)
    demand, supply, zone_buy, zone_sell, zone_evidence = _zones(frame, atr)

    buy = fib_buy + zone_buy
    sell = fib_sell + zone_sell
    evidence = fib_evidence + zone_evidence
    total = buy + sell
    if total == 0:
        direction, confidence = "NEUTRAL", 0.0
    elif buy > sell:
        direction, confidence = "BUY", round(100 * buy / total, 2)
    elif sell > buy:
        direction, confidence = "SELL", round(100 * sell / total, 2)
    else:
        direction, confidence = "NEUTRAL", 50.0

    return FibonacciSupplyDemandSignal(
        direction=direction,
        buy_score=buy,
        sell_score=sell,
        confidence=confidence,
        evidence=evidence,
        fibonacci=fibonacci,
        demand_zones=demand,
        supply_zones=supply,
    )
