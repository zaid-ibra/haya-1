from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import pandas as pd
from tradingagents.advanced_analysis.engine import analyze_market


@dataclass(frozen=True)
class BacktestReport:
    trades: int
    wins: int
    losses: int
    win_rate: float
    net_r: float
    average_r: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float
    sharpe: float
    long_trades: int
    short_trades: int
    skipped: int

    def to_dict(self):
        return asdict(self)


def _trade_outcome(window: pd.DataFrame, *, action: str, entry: float, stop: float, target: float) -> float:
    for _, candle in window.iterrows():
        high, low = float(candle.high), float(candle.low)
        if action == "BUY":
            stop_hit, target_hit = low <= stop, high >= target
        else:
            stop_hit, target_hit = high >= stop, low <= target
        if stop_hit and target_hit:
            return -1.0  # conservative same-candle assumption
        if stop_hit:
            return -1.0
        if target_hit:
            return abs(target - entry) / max(abs(entry - stop), 1e-12)
    final = float(window.iloc[-1].close)
    move = final - entry if action == "BUY" else entry - final
    return move / max(abs(entry - stop), 1e-12)


def run_walk_forward_backtest(
    frame: pd.DataFrame, *, warmup: int = 220, horizon: int = 12,
    min_confidence: float = 65.0, min_rr: float = 2.0,
    spread: float = 0.0, step: int = 1,
) -> BacktestReport:
    if len(frame) < warmup + horizon + 1:
        raise ValueError("Not enough candles for backtest")
    outcomes: list[float] = []
    sides: list[str] = []
    skipped = 0
    for i in range(warmup, len(frame) - horizon, max(1, step)):
        signal = analyze_market(frame.iloc[:i].copy())
        action = signal.decision.get("action", "HOLD")
        if action == "HOLD" or not signal.decision.get("approved") or signal.decision.get("confidence", 0) < min_confidence:
            skipped += 1
            continue
        entry = float(frame.iloc[i].open)
        high = signal.levels.get("last_swing_high")
        low = signal.levels.get("last_swing_low")
        stop = low if action == "BUY" else high
        if stop is None or (action == "BUY" and stop >= entry) or (action == "SELL" and stop <= entry):
            skipped += 1
            continue
        entry += spread / 2 if action == "BUY" else -spread / 2
        risk = abs(entry - float(stop))
        target = entry + risk * min_rr if action == "BUY" else entry - risk * min_rr
        outcomes.append(_trade_outcome(frame.iloc[i:i+horizon], action=action, entry=entry, stop=float(stop), target=target))
        sides.append(action)

    wins = sum(x > 0 for x in outcomes)
    losses = sum(x <= 0 for x in outcomes)
    gross_win = sum(x for x in outcomes if x > 0)
    gross_loss = abs(sum(x for x in outcomes if x < 0))
    equity = peak = max_dd = 0.0
    for x in outcomes:
        equity += x; peak = max(peak, equity); max_dd = max(max_dd, peak - equity)
    trades = len(outcomes)
    mean = sum(outcomes) / trades if trades else 0.0
    variance = sum((x - mean) ** 2 for x in outcomes) / max(trades - 1, 1) if trades else 0.0
    sharpe = mean / math.sqrt(variance) * math.sqrt(trades) if variance > 0 else 0.0
    return BacktestReport(
        trades, wins, losses, round(100 * wins / trades, 2) if trades else 0.0,
        round(sum(outcomes), 4), round(mean, 4), round(mean, 4),
        round(gross_win / gross_loss, 4) if gross_loss else math.inf if gross_win else 0.0,
        round(max_dd, 4), round(sharpe, 4), sides.count("BUY"), sides.count("SELL"), skipped,
    )
