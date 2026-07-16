from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VolumeProfileSignal:
    direction: str
    buy_score: float
    sell_score: float
    confidence: float
    evidence: list[str]
    profile: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _empty_profile(reason: str) -> VolumeProfileSignal:
    return VolumeProfileSignal(
        direction="NEUTRAL",
        buy_score=0.0,
        sell_score=0.0,
        confidence=0.0,
        evidence=[reason],
        profile={
            "available": False,
            "reason": reason,
            "poc": None,
            "vah": None,
            "val": None,
            "hvn": [],
            "lvn": [],
            "value_area_percent": 70.0,
        },
    )


def _value_area(volumes: np.ndarray, poc_index: int, target_fraction: float = 0.70) -> tuple[int, int]:
    total = float(volumes.sum())
    if total <= 0:
        return poc_index, poc_index

    selected = float(volumes[poc_index])
    low = high = poc_index
    while selected / total < target_fraction and (low > 0 or high < len(volumes) - 1):
        left_volume = float(volumes[low - 1]) if low > 0 else -1.0
        right_volume = float(volumes[high + 1]) if high < len(volumes) - 1 else -1.0
        if right_volume > left_volume:
            high += 1
            selected += float(volumes[high])
        else:
            low -= 1
            selected += float(volumes[low])
    return low, high


def analyze_volume_profile(
    frame: pd.DataFrame,
    *,
    lookback: int = 200,
    bins: int = 24,
    value_area_percent: float = 70.0,
) -> VolumeProfileSignal:
    """Build an approximate volume profile from candle volume.

    For MT5 forex/gold feeds this normally uses ``tick_volume`` mapped to
    ``volume`` by the main engine. Tick volume measures activity, not centralized
    exchange volume, so the module is intentionally a low-weight confluence.
    """
    if "volume" not in frame.columns:
        return _empty_profile("Volume Profile unavailable because no volume or tick_volume column was supplied")

    sample = frame.tail(max(30, lookback)).copy()
    sample["volume"] = pd.to_numeric(sample["volume"], errors="coerce").fillna(0.0).clip(lower=0.0)
    if float(sample["volume"].sum()) <= 0:
        return _empty_profile("Volume Profile unavailable because all volume values are zero")

    low_price = float(sample["low"].min())
    high_price = float(sample["high"].max())
    price_range = high_price - low_price
    if price_range <= 0:
        return _empty_profile("Volume Profile unavailable because the analyzed price range is zero")

    bins = max(8, min(int(bins), 100))
    edges = np.linspace(low_price, high_price, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    profile = np.zeros(bins, dtype=float)

    # Distribute each candle's volume across every price bin intersecting its
    # high-low range. This is more stable than assigning all volume to close.
    for row in sample.itertuples(index=False):
        candle_low = float(row.low)
        candle_high = float(row.high)
        candle_volume = float(row.volume)
        if candle_volume <= 0:
            continue
        start = int(np.searchsorted(edges, candle_low, side="right") - 1)
        end = int(np.searchsorted(edges, candle_high, side="left"))
        start = max(0, min(start, bins - 1))
        end = max(start, min(end, bins - 1))
        count = end - start + 1
        profile[start : end + 1] += candle_volume / count

    if float(profile.sum()) <= 0:
        return _empty_profile("Volume Profile could not allocate volume to price bins")

    poc_index = int(np.argmax(profile))
    target = max(0.5, min(float(value_area_percent) / 100.0, 0.95))
    val_index, vah_index = _value_area(profile, poc_index, target)

    nonzero = profile[profile > 0]
    high_threshold = float(np.quantile(nonzero, 0.80))
    low_threshold = float(np.quantile(nonzero, 0.20))
    hvn_indices = [int(i) for i, value in enumerate(profile) if value >= high_threshold]
    lvn_indices = [int(i) for i, value in enumerate(profile) if 0 < value <= low_threshold]

    poc = float(centers[poc_index])
    val = float(edges[val_index])
    vah = float(edges[vah_index + 1])
    latest = float(sample.iloc[-1]["close"])
    bin_width = price_range / bins

    buy = sell = 0.0
    evidence: list[str] = []
    location = "VALUE_AREA"

    if latest > vah:
        location = "ABOVE_VALUE_AREA"
        buy += 8
        evidence.append("Price is accepted above the Volume Profile value area high")
    elif latest < val:
        location = "BELOW_VALUE_AREA"
        sell += 8
        evidence.append("Price is accepted below the Volume Profile value area low")
    elif latest > poc:
        buy += 4
        evidence.append("Price is trading above the Volume Profile point of control")
    elif latest < poc:
        sell += 4
        evidence.append("Price is trading below the Volume Profile point of control")

    if abs(latest - poc) <= bin_width * 0.6:
        evidence.append("Price is near the Volume Profile point of control; balance or rotation risk is elevated")
        buy = max(0.0, buy - 2.0)
        sell = max(0.0, sell - 2.0)

    total = buy + sell
    if total == 0:
        direction, confidence = "NEUTRAL", 0.0
    elif buy > sell:
        direction, confidence = "BUY", round(100 * buy / total, 2)
    elif sell > buy:
        direction, confidence = "SELL", round(100 * sell / total, 2)
    else:
        direction, confidence = "NEUTRAL", 50.0

    ranked_hvn = sorted(hvn_indices, key=lambda i: profile[i], reverse=True)[:5]
    ranked_lvn = sorted(lvn_indices, key=lambda i: profile[i])[:5]
    return VolumeProfileSignal(
        direction=direction,
        buy_score=buy,
        sell_score=sell,
        confidence=confidence,
        evidence=evidence,
        profile={
            "available": True,
            "source": "tick_volume_or_volume",
            "lookback_candles": int(len(sample)),
            "bins": bins,
            "value_area_percent": round(target * 100.0, 2),
            "range_low": round(low_price, 6),
            "range_high": round(high_price, 6),
            "poc": round(poc, 6),
            "vah": round(vah, 6),
            "val": round(val, 6),
            "latest_location": location,
            "hvn": [
                {"price": round(float(centers[i]), 6), "relative_volume": round(float(profile[i] / profile.sum()), 6)}
                for i in ranked_hvn
            ],
            "lvn": [
                {"price": round(float(centers[i]), 6), "relative_volume": round(float(profile[i] / profile.sum()), 6)}
                for i in ranked_lvn
            ],
        },
    )
