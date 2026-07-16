from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PositionManagementPlan:
    ticket: int | None
    action: str
    update_stop: bool
    new_stop_loss: float | None
    partial_close_volume: float
    close_position: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_position_management_plan(
    *,
    position: dict[str, Any],
    current_price: float,
    atr: float,
    break_even_at_r: float = 1.0,
    trailing_at_r: float = 1.5,
    trailing_atr_multiple: float = 1.5,
    partial_at_r: float = 2.0,
    partial_fraction: float = 0.5,
) -> PositionManagementPlan:
    side = str(position.get("action") or position.get("type") or "").upper()
    if side in {"0", "BUY"}: side = "BUY"
    elif side in {"1", "SELL"}: side = "SELL"
    else:
        return PositionManagementPlan(position.get("ticket"), "NONE", False, None, 0.0, False, "Unknown position side")

    entry = float(position.get("entry") or position.get("price_open") or 0.0)
    stop = float(position.get("stop_loss") or position.get("sl") or 0.0)
    volume = float(position.get("volume") or 0.0)
    if entry <= 0 or atr <= 0:
        return PositionManagementPlan(position.get("ticket"), side, False, None, 0.0, False, "Invalid entry or ATR")

    initial_risk = abs(entry - stop) if stop > 0 else atr * 2.0
    favorable_move = current_price - entry if side == "BUY" else entry - current_price
    current_r = favorable_move / max(initial_risk, 1e-12)

    candidate_stop: float | None = None
    reasons: list[str] = []
    if current_r >= break_even_at_r:
        candidate_stop = entry
        reasons.append("Break-even threshold reached")
    if current_r >= trailing_at_r:
        trailing = current_price - atr * trailing_atr_multiple if side == "BUY" else current_price + atr * trailing_atr_multiple
        if candidate_stop is None or (side == "BUY" and trailing > candidate_stop) or (side == "SELL" and trailing < candidate_stop):
            candidate_stop = trailing
        reasons.append("ATR trailing threshold reached")

    improves = candidate_stop is not None and (
        stop == 0 or (side == "BUY" and candidate_stop > stop) or (side == "SELL" and candidate_stop < stop)
    )
    partial = round(volume * partial_fraction, 2) if current_r >= partial_at_r and volume > 0.01 else 0.0
    if partial:
        reasons.append("Partial-profit threshold reached")

    return PositionManagementPlan(
        ticket=position.get("ticket"), action=side, update_stop=improves,
        new_stop_loss=round(candidate_stop, 6) if improves and candidate_stop is not None else None,
        partial_close_volume=partial, close_position=False,
        reason="; ".join(reasons) if reasons else f"No management action; current R={current_r:.2f}",
    )
