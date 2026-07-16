from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class SMCSignal:
    direction: str
    buy_score: float
    sell_score: float
    confidence: float
    evidence: list[str]
    liquidity: dict[str, Any]
    order_blocks: list[dict[str, Any]]
    fair_value_gaps: list[dict[str, Any]]
    dealing_range: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _average_range(frame: pd.DataFrame, period: int = 20) -> float:
    ranges = (frame["high"] - frame["low"]).tail(period)
    return max(float(ranges.mean()), 1e-12)


def _find_equal_levels(
    frame: pd.DataFrame,
    swing_indices: list[int],
    column: str,
    tolerance: float,
) -> list[dict[str, Any]]:
    levels: list[dict[str, Any]] = []
    recent = swing_indices[-8:]
    for pos, first in enumerate(recent):
        first_price = float(frame.at[first, column])
        for second in recent[pos + 1 :]:
            second_price = float(frame.at[second, column])
            if abs(first_price - second_price) <= tolerance:
                levels.append(
                    {
                        "price": round((first_price + second_price) / 2, 6),
                        "first_index": int(first),
                        "second_index": int(second),
                        "distance": round(abs(first_price - second_price), 6),
                    }
                )
    return levels[-3:]


def _liquidity(
    frame: pd.DataFrame,
    swing_highs: list[int],
    swing_lows: list[int],
    tolerance: float,
) -> tuple[dict[str, Any], float, float, list[str]]:
    current = frame.iloc[-1]
    eqh = _find_equal_levels(frame, swing_highs, "high", tolerance)
    eql = _find_equal_levels(frame, swing_lows, "low", tolerance)
    buy = sell = 0.0
    evidence: list[str] = []
    sweeps: list[dict[str, Any]] = []

    high_candidates = [x["price"] for x in eqh]
    if swing_highs:
        high_candidates.append(float(frame.at[swing_highs[-1], "high"]))
    low_candidates = [x["price"] for x in eql]
    if swing_lows:
        low_candidates.append(float(frame.at[swing_lows[-1], "low"]))

    for level in high_candidates:
        if float(current["high"]) > level + tolerance * 0.1 and float(current["close"]) < level:
            sell += 24
            sweeps.append({"type": "BUY_SIDE_SWEEP", "level": round(level, 6)})
            evidence.append("Buy-side liquidity was swept and price closed back below the level")
            break

    for level in low_candidates:
        if float(current["low"]) < level - tolerance * 0.1 and float(current["close"]) > level:
            buy += 24
            sweeps.append({"type": "SELL_SIDE_SWEEP", "level": round(level, 6)})
            evidence.append("Sell-side liquidity was swept and price closed back above the level")
            break

    if eqh:
        evidence.append("Equal highs form a potential buy-side liquidity pool")
    if eql:
        evidence.append("Equal lows form a potential sell-side liquidity pool")

    return {"equal_highs": eqh, "equal_lows": eql, "sweeps": sweeps}, buy, sell, evidence


def _fvg(frame: pd.DataFrame, lookback: int = 80) -> tuple[list[dict[str, Any]], float, float, list[str]]:
    gaps: list[dict[str, Any]] = []
    start = max(2, len(frame) - lookback)
    latest_close = float(frame.iloc[-1]["close"])
    buy = sell = 0.0
    evidence: list[str] = []

    for i in range(start, len(frame)):
        left = frame.iloc[i - 2]
        right = frame.iloc[i]
        if float(right["low"]) > float(left["high"]):
            low = float(left["high"])
            high = float(right["low"])
            filled = bool((frame["low"].iloc[i + 1 :] <= low).any()) if i + 1 < len(frame) else False
            gaps.append({
                "type": "BULLISH_FVG",
                "low": round(low, 6),
                "high": round(high, 6),
                "origin_index": i,
                "filled": filled,
            })
        elif float(right["high"]) < float(left["low"]):
            low = float(right["high"])
            high = float(left["low"])
            filled = bool((frame["high"].iloc[i + 1 :] >= high).any()) if i + 1 < len(frame) else False
            gaps.append({
                "type": "BEARISH_FVG",
                "low": round(low, 6),
                "high": round(high, 6),
                "origin_index": i,
                "filled": filled,
            })

    active = [gap for gap in gaps if not gap["filled"]][-5:]
    for gap in reversed(active):
        if gap["type"] == "BULLISH_FVG" and latest_close >= gap["low"]:
            buy += 12
            evidence.append("An unfilled bullish fair value gap remains active")
            break
        if gap["type"] == "BEARISH_FVG" and latest_close <= gap["high"]:
            sell += 12
            evidence.append("An unfilled bearish fair value gap remains active")
            break
    return active, buy, sell, evidence


def _order_blocks(frame: pd.DataFrame, average_range: float, lookback: int = 60) -> tuple[list[dict[str, Any]], float, float, list[str]]:
    blocks: list[dict[str, Any]] = []
    buy = sell = 0.0
    evidence: list[str] = []
    start = max(1, len(frame) - lookback)

    for i in range(start, len(frame) - 1):
        candle = frame.iloc[i]
        nxt = frame.iloc[i + 1]
        next_body = abs(float(nxt["close"]) - float(nxt["open"]))
        displacement = next_body >= average_range * 0.8
        if not displacement:
            continue

        if float(candle["close"]) < float(candle["open"]) and float(nxt["close"]) > float(candle["high"]):
            low, high = float(candle["low"]), float(candle["high"])
            mitigated = bool((frame["low"].iloc[i + 2 :] <= high).any()) if i + 2 < len(frame) else False
            invalidated = bool((frame["close"].iloc[i + 2 :] < low).any()) if i + 2 < len(frame) else False
            blocks.append({"type": "BULLISH_ORDER_BLOCK", "low": round(low, 6), "high": round(high, 6), "origin_index": i, "mitigated": mitigated, "invalidated": invalidated})
        elif float(candle["close"]) > float(candle["open"]) and float(nxt["close"]) < float(candle["low"]):
            low, high = float(candle["low"]), float(candle["high"])
            mitigated = bool((frame["high"].iloc[i + 2 :] >= low).any()) if i + 2 < len(frame) else False
            invalidated = bool((frame["close"].iloc[i + 2 :] > high).any()) if i + 2 < len(frame) else False
            blocks.append({"type": "BEARISH_ORDER_BLOCK", "low": round(low, 6), "high": round(high, 6), "origin_index": i, "mitigated": mitigated, "invalidated": invalidated})

    valid = [block for block in blocks if not block["invalidated"]][-5:]
    latest = frame.iloc[-1]
    for block in reversed(valid):
        overlaps = float(latest["low"]) <= block["high"] and float(latest["high"]) >= block["low"]
        if not overlaps:
            continue
        if block["type"] == "BULLISH_ORDER_BLOCK":
            buy += 18 if not block["mitigated"] else 10
            evidence.append("Price is interacting with a valid bullish order-block zone")
        else:
            sell += 18 if not block["mitigated"] else 10
            evidence.append("Price is interacting with a valid bearish order-block zone")
        break
    return valid, buy, sell, evidence


def _dealing_range(frame: pd.DataFrame, swing_highs: list[int], swing_lows: list[int]) -> tuple[dict[str, Any], float, float, list[str]]:
    if not swing_highs or not swing_lows:
        return {"position": "UNKNOWN"}, 0.0, 0.0, []
    high = float(frame.at[swing_highs[-1], "high"])
    low = float(frame.at[swing_lows[-1], "low"])
    if high <= low:
        high = float(frame["high"].tail(60).max())
        low = float(frame["low"].tail(60).min())
    equilibrium = (high + low) / 2
    latest = float(frame.iloc[-1]["close"])
    span = max(high - low, 1e-12)
    relative = (latest - low) / span
    buy = sell = 0.0
    evidence: list[str] = []
    if relative < 0.45:
        position = "DISCOUNT"
        buy += 8
        evidence.append("Price is trading in the discount half of the active dealing range")
    elif relative > 0.55:
        position = "PREMIUM"
        sell += 8
        evidence.append("Price is trading in the premium half of the active dealing range")
    else:
        position = "EQUILIBRIUM"
    return {
        "low": round(low, 6),
        "high": round(high, 6),
        "equilibrium": round(equilibrium, 6),
        "relative_position": round(relative, 4),
        "position": position,
    }, buy, sell, evidence


def analyze_smc(
    frame: pd.DataFrame,
    *,
    swing_highs: list[int],
    swing_lows: list[int],
    tolerance_multiplier: float = 0.2,
) -> SMCSignal:
    """Return deterministic SMC-style confirmations from normalized OHLC data.

    These rules are heuristic approximations intended for testing and confluence,
    not authoritative labels or standalone trading instructions.
    """
    average_range = _average_range(frame)
    tolerance = average_range * tolerance_multiplier

    liquidity, liq_buy, liq_sell, liq_evidence = _liquidity(frame, swing_highs, swing_lows, tolerance)
    fvgs, fvg_buy, fvg_sell, fvg_evidence = _fvg(frame)
    blocks, ob_buy, ob_sell, ob_evidence = _order_blocks(frame, average_range)
    dealing_range, range_buy, range_sell, range_evidence = _dealing_range(frame, swing_highs, swing_lows)

    buy = liq_buy + fvg_buy + ob_buy + range_buy
    sell = liq_sell + fvg_sell + ob_sell + range_sell
    evidence = liq_evidence + fvg_evidence + ob_evidence + range_evidence
    total = buy + sell
    if total == 0:
        direction, confidence = "NEUTRAL", 0.0
    elif buy > sell:
        direction, confidence = "BUY", round(100 * buy / total, 2)
    elif sell > buy:
        direction, confidence = "SELL", round(100 * sell / total, 2)
    else:
        direction, confidence = "NEUTRAL", 50.0

    return SMCSignal(
        direction=direction,
        buy_score=buy,
        sell_score=sell,
        confidence=confidence,
        evidence=evidence,
        liquidity=liquidity,
        order_blocks=blocks,
        fair_value_gaps=fvgs,
        dealing_range=dealing_range,
    )
