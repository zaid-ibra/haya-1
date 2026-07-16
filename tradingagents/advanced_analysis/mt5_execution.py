from __future__ import annotations
from typing import Any

from tradingagents.branding import MT5_COMMENT


def execute_mt5_order(
    plan: dict[str, Any], *, symbol: str = "XAUUSD", deviation: int = 20,
    magic: int = 260715, dry_run: bool = True, prevent_duplicate: bool = True,
    max_spread_points: float | None = None,
) -> dict[str, Any]:
    if not plan.get("valid"):
        return {"success": False, "executed": False, "reason": "Risk plan is invalid"}
    request = {
        "symbol": symbol, "volume": plan["volume"], "price": plan["entry"],
        "sl": plan["stop_loss"], "tp": plan["take_profit"], "deviation": deviation, "magic": magic,
    }
    if dry_run:
        return {"success": True, "executed": False, "dry_run": True, "request": request}
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        return {"success": False, "executed": False, "reason": f"MetaTrader5 package unavailable: {exc}"}
    if not mt5.initialize():
        return {"success": False, "executed": False, "reason": str(mt5.last_error())}
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return {"success": False, "executed": False, "reason": "Symbol information unavailable"}
        if not info.visible and not mt5.symbol_select(symbol, True):
            return {"success": False, "executed": False, "reason": "Unable to select symbol"}
        positions = mt5.positions_get(symbol=symbol) or []
        if prevent_duplicate and any(int(getattr(p, "magic", 0)) == magic for p in positions):
            return {"success": False, "executed": False, "reason": "An HAYA-ZAID position is already open for this symbol"}
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "executed": False, "reason": "No symbol tick available"}
        spread_points = (float(tick.ask) - float(tick.bid)) / max(float(info.point), 1e-12)
        if max_spread_points is not None and spread_points > max_spread_points:
            return {"success": False, "executed": False, "reason": f"Spread too high: {spread_points:.1f} points"}
        action = plan.get("action")
        request.update({
            "action": mt5.TRADE_ACTION_DEAL,
            "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": tick.ask if action == "BUY" else tick.bid,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "comment": MT5_COMMENT,
        })
        result = mt5.order_send(request)
        return {
            "success": bool(result and result.retcode == mt5.TRADE_RETCODE_DONE),
            "executed": True,
            "spread_points": round(spread_points, 2),
            "result": None if result is None else result._asdict(),
            "request": request,
        }
    finally:
        mt5.shutdown()
