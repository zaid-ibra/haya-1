from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from tradingagents.advanced_analysis.price_action import analyze_price_action
from tradingagents.advanced_analysis.smc import analyze_smc
from tradingagents.advanced_analysis.fibonacci_supply_demand import analyze_fibonacci_supply_demand
from tradingagents.advanced_analysis.volume_profile import analyze_volume_profile
from tradingagents.advanced_analysis.ict import analyze_ict
from tradingagents.advanced_analysis.wyckoff import analyze_wyckoff
from tradingagents.advanced_analysis.elliott import analyze_elliott
from tradingagents.advanced_analysis.decision import make_decision

REQUIRED_COLUMNS = {"open", "high", "low", "close"}


@dataclass(frozen=True)
class TechnicalSignal:
    direction: str
    confidence: float
    buy_score: float
    sell_score: float
    market_regime: str
    latest_price: float
    evidence: list[str]
    levels: dict[str, Any]
    indicators: dict[str, float]
    price_action: dict[str, Any]
    smc: dict[str, Any]
    fibonacci_supply_demand: dict[str, Any]
    volume_profile: dict[str, Any]
    ict: dict[str, Any]
    wyckoff: dict[str, Any]
    elliott_wave: dict[str, Any]
    decision: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    if "volume" not in frame.columns and "tick_volume" in frame.columns:
        frame["volume"] = frame["tick_volume"]
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Missing OHLC columns: {', '.join(sorted(missing))}")
    for column in REQUIRED_COLUMNS | ({"volume"} if "volume" in frame.columns else set()):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=sorted(REQUIRED_COLUMNS)).reset_index(drop=True)
    if len(frame) < 60:
        raise ValueError("At least 60 candles are required for reliable analysis")
    return frame


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    safe_loss = loss.mask(loss == 0)
    rs = gain / safe_loss
    return (100 - (100 / (1 + rs))).astype(float).fillna(50.0)


def _swings(frame: pd.DataFrame, window: int = 3) -> tuple[list[int], list[int]]:
    highs: list[int] = []
    lows: list[int] = []
    for i in range(window, len(frame) - window):
        high_slice = frame["high"].iloc[i - window : i + window + 1]
        low_slice = frame["low"].iloc[i - window : i + window + 1]
        if frame.at[i, "high"] == high_slice.max() and (high_slice == frame.at[i, "high"]).sum() == 1:
            highs.append(i)
        if frame.at[i, "low"] == low_slice.min() and (low_slice == frame.at[i, "low"]).sum() == 1:
            lows.append(i)
    return highs, lows


def _divergence(frame: pd.DataFrame, highs: list[int], lows: list[int]) -> str | None:
    if len(lows) >= 2:
        a, b = lows[-2], lows[-1]
        if frame.at[b, "low"] < frame.at[a, "low"] and frame.at[b, "rsi"] > frame.at[a, "rsi"]:
            return "REGULAR_BULLISH"
        if frame.at[b, "low"] > frame.at[a, "low"] and frame.at[b, "rsi"] < frame.at[a, "rsi"]:
            return "HIDDEN_BULLISH"
    if len(highs) >= 2:
        a, b = highs[-2], highs[-1]
        if frame.at[b, "high"] > frame.at[a, "high"] and frame.at[b, "rsi"] < frame.at[a, "rsi"]:
            return "REGULAR_BEARISH"
        if frame.at[b, "high"] < frame.at[a, "high"] and frame.at[b, "rsi"] > frame.at[a, "rsi"]:
            return "HIDDEN_BEARISH"
    return None


def analyze_market(df: pd.DataFrame, swing_window: int = 3) -> TechnicalSignal:
    frame = _prepare(df)
    close = frame["close"]
    for period in (20, 50, 200):
        frame[f"ema{period}"] = close.ewm(span=period, adjust=False).mean()
    frame["macd"] = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False).mean()
    frame["macd_hist"] = frame["macd"] - frame["macd_signal"]
    frame["rsi"] = _rsi(close)

    highs, lows = _swings(frame, swing_window)
    last = frame.iloc[-1]
    prev = frame.iloc[-2]
    buy = sell = 0.0
    evidence: list[str] = []

    if last.ema20 > last.ema50 > last.ema200:
        buy += 25; evidence.append("EMA 20/50/200 bullish alignment")
        regime = "BULLISH"
    elif last.ema20 < last.ema50 < last.ema200:
        sell += 25; evidence.append("EMA 20/50/200 bearish alignment")
        regime = "BEARISH"
    else:
        regime = "RANGE"

    if prev.ema20 <= prev.ema50 and last.ema20 > last.ema50:
        buy += 15; evidence.append("Bullish EMA20/EMA50 cross")
    elif prev.ema20 >= prev.ema50 and last.ema20 < last.ema50:
        sell += 15; evidence.append("Bearish EMA20/EMA50 cross")

    if last.macd > last.macd_signal and last.macd_hist > prev.macd_hist:
        buy += 15; evidence.append("MACD bullish momentum")
    elif last.macd < last.macd_signal and last.macd_hist < prev.macd_hist:
        sell += 15; evidence.append("MACD bearish momentum")

    last_high = frame.at[highs[-1], "high"] if highs else None
    last_low = frame.at[lows[-1], "low"] if lows else None
    event = "NONE"
    if last_high is not None and last.close > last_high:
        if regime == "BEARISH":
            event = "BULLISH_CHOCH"; buy += 35
        else:
            event = "BULLISH_BOS"; buy += 30
        evidence.append(event.replace("_", " ").title())
    elif last_low is not None and last.close < last_low:
        if regime == "BULLISH":
            event = "BEARISH_CHOCH"; sell += 35
        else:
            event = "BEARISH_BOS"; sell += 30
        evidence.append(event.replace("_", " ").title())

    price_action = analyze_price_action(
        frame,
        last_swing_high=last_high,
        last_swing_low=last_low,
    )
    buy += price_action.buy_score
    sell += price_action.sell_score
    evidence.extend(price_action.evidence)

    smc = analyze_smc(frame, swing_highs=highs, swing_lows=lows)
    buy += smc.buy_score
    sell += smc.sell_score
    evidence.extend(smc.evidence)

    fib_sd = analyze_fibonacci_supply_demand(frame, swing_highs=highs, swing_lows=lows)
    buy += fib_sd.buy_score
    sell += fib_sd.sell_score
    evidence.extend(fib_sd.evidence)

    volume_profile = analyze_volume_profile(frame)
    buy += volume_profile.buy_score
    sell += volume_profile.sell_score
    evidence.extend(volume_profile.evidence)

    ict = analyze_ict(frame, swing_highs=highs, swing_lows=lows, smc=smc.to_dict())
    buy += ict.buy_score
    sell += ict.sell_score
    evidence.extend(ict.evidence)

    wyckoff = analyze_wyckoff(frame)
    buy += wyckoff.buy_score
    sell += wyckoff.sell_score
    evidence.extend(wyckoff.evidence)

    elliott = analyze_elliott(frame, swing_highs=highs, swing_lows=lows)
    buy += elliott.buy_score
    sell += elliott.sell_score
    evidence.extend(elliott.evidence)

    divergence = _divergence(frame, highs, lows)
    if divergence:
        if "BULLISH" in divergence:
            buy += 20
        else:
            sell += 20
        evidence.append(divergence.replace("_", " ").title())

    total = buy + sell
    if total == 0:
        direction, confidence = "HOLD", 0.0
    elif buy > sell:
        direction, confidence = "BUY", round(100 * buy / total, 2)
    elif sell > buy:
        direction, confidence = "SELL", round(100 * sell / total, 2)
    else:
        direction, confidence = "HOLD", 50.0

    decision = make_decision(buy_score=buy, sell_score=sell, evidence=evidence)

    return TechnicalSignal(
        direction=direction,
        confidence=confidence,
        buy_score=buy,
        sell_score=sell,
        market_regime=regime,
        latest_price=round(float(last.close), 6),
        evidence=evidence,
        levels={
            "last_swing_high": None if last_high is None else round(float(last_high), 6),
            "last_swing_low": None if last_low is None else round(float(last_low), 6),
            "structure_event": event,
            "rsi_divergence": divergence,
        },
        indicators={
            "ema20": round(float(last.ema20), 6),
            "ema50": round(float(last.ema50), 6),
            "ema200": round(float(last.ema200), 6),
            "macd": round(float(last.macd), 6),
            "macd_signal": round(float(last.macd_signal), 6),
            "macd_hist": round(float(last.macd_hist), 6),
            "rsi": round(float(last.rsi), 4),
        },
        price_action=price_action.to_dict(),
        smc=smc.to_dict(),
        fibonacci_supply_demand=fib_sd.to_dict(),
        volume_profile=volume_profile.to_dict(),
        ict=ict.to_dict(),
        wyckoff=wyckoff.to_dict(),
        elliott_wave=elliott.to_dict(),
        decision=decision.to_dict(),
    )
