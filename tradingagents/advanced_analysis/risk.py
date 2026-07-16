from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any


@dataclass(frozen=True)
class RiskPlan:
    action: str
    valid: bool
    volume: float
    entry: float
    stop_loss: float
    take_profit: float
    risk_amount: float
    reward_risk: float
    reason: str
    estimated_loss: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_volume(raw: float, minimum: float, maximum: float, step: float) -> float:
    if step <= 0:
        step = 0.01
    clipped = min(maximum, max(minimum, raw))
    steps = math.floor((clipped - minimum) / step + 1e-12)
    return round(minimum + steps * step, 8)


def build_risk_plan(
    *, action: str, entry: float, swing_high: float | None, swing_low: float | None,
    balance: float, risk_percent: float = 1.0, point_value_per_lot: float = 1.0,
    min_rr: float = 2.0, max_volume: float = 1.0, min_volume: float = 0.01,
    volume_step: float = 0.01, tick_size: float | None = None, tick_value: float | None = None,
    min_stop_distance: float = 0.0,
) -> RiskPlan:
    if balance <= 0 or not 0 < risk_percent <= 10:
        return RiskPlan(action, False, 0, entry, 0, 0, 0, 0, "Invalid balance or risk percentage")
    if action not in {"BUY", "SELL"}:
        return RiskPlan(action, False, 0, entry, 0, 0, 0, 0, "No approved directional trade")
    stop = swing_low if action == "BUY" else swing_high
    if stop is None or (action == "BUY" and stop >= entry) or (action == "SELL" and stop <= entry):
        return RiskPlan(action, False, 0, entry, 0, 0, 0, 0, "No valid structural stop level")
    distance = abs(entry - stop)
    if distance < min_stop_distance:
        stop = entry - min_stop_distance if action == "BUY" else entry + min_stop_distance
        distance = min_stop_distance
    risk_amount = balance * risk_percent / 100.0
    if distance <= 0:
        return RiskPlan(action, False, 0, entry, stop, 0, risk_amount, 0, "Invalid stop distance")

    if tick_size and tick_value and tick_size > 0 and tick_value > 0:
        money_per_lot = (distance / tick_size) * tick_value
    else:
        if point_value_per_lot <= 0:
            return RiskPlan(action, False, 0, entry, stop, 0, risk_amount, 0, "Invalid point/tick value")
        money_per_lot = distance * point_value_per_lot
    raw_volume = risk_amount / max(money_per_lot, 1e-12)
    if raw_volume < min_volume:
        return RiskPlan(action, False, 0, entry, stop, 0, risk_amount, 0, "Required volume is below broker minimum")
    volume = _normalize_volume(raw_volume, min_volume, max_volume, volume_step)
    estimated_loss = volume * money_per_lot
    tp = entry + distance * min_rr if action == "BUY" else entry - distance * min_rr
    return RiskPlan(
        action, True, volume, round(entry, 6), round(stop, 6), round(tp, 6),
        round(risk_amount, 2), min_rr, "Risk plan created from structural stop and broker sizing",
        round(estimated_loss, 2),
    )
