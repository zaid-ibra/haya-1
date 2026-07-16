from __future__ import annotations
from typing import Any
import pandas as pd
from tradingagents.advanced_analysis.engine import analyze_market
from tradingagents.advanced_analysis.risk import build_risk_plan
from tradingagents.advanced_analysis.mt5_execution import execute_mt5_order
from tradingagents.advanced_analysis.storage import TradingJournal


def fetch_mt5_candles(symbol: str = "XAUUSD", timeframe_name: str = "M5", bars: int = 500) -> pd.DataFrame:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("Install MetaTrader5 inside the active virtual environment") from exc
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        timeframe = getattr(mt5, f"TIMEFRAME_{timeframe_name.upper()}", None)
        if timeframe is None:
            raise ValueError(f"Unsupported MT5 timeframe: {timeframe_name}")
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Unable to select symbol: {symbol}")
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No MT5 candles returned for {symbol}")
        frame = pd.DataFrame(rates)
        frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        return frame
    finally:
        mt5.shutdown()


def _broker_spec(symbol: str) -> dict[str, float]:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {}
    if not mt5.initialize():
        return {}
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return {}
        return {
            "tick_size": float(info.trade_tick_size or info.point),
            "tick_value": float(info.trade_tick_value or info.trade_tick_value_profit or 0.0),
            "volume_min": float(info.volume_min), "volume_max": float(info.volume_max),
            "volume_step": float(info.volume_step),
            "min_stop_distance": float(info.trade_stops_level * info.point),
        }
    finally:
        mt5.shutdown()


def run_gold_cycle(
    *, balance: float, symbol: str = "XAUUSD", timeframe_name: str = "M5", bars: int = 500,
    risk_percent: float = 1.0, point_value_per_lot: float = 1.0, dry_run: bool = True,
    journal_path: str | None = "data/haya_zaid_journal.sqlite3",
) -> dict[str, Any]:
    frame = fetch_mt5_candles(symbol, timeframe_name, bars)
    signal = analyze_market(frame)
    decision = signal.decision
    spec = _broker_spec(symbol)
    plan = build_risk_plan(
        action=decision["action"], entry=signal.latest_price,
        swing_high=signal.levels.get("last_swing_high"), swing_low=signal.levels.get("last_swing_low"),
        balance=balance, risk_percent=risk_percent, point_value_per_lot=point_value_per_lot,
        tick_size=spec.get("tick_size"), tick_value=spec.get("tick_value"),
        min_volume=spec.get("volume_min", 0.01), max_volume=spec.get("volume_max", 1.0),
        volume_step=spec.get("volume_step", 0.01), min_stop_distance=spec.get("min_stop_distance", 0.0),
    )
    execution = execute_mt5_order(plan.to_dict(), symbol=symbol, dry_run=dry_run)
    result = {"signal": signal.to_dict(), "risk_plan": plan.to_dict(), "execution": execution, "broker_spec": spec}
    if journal_path:
        journal = TradingJournal(journal_path)
        result["journal_cycle_id"] = journal.log_cycle(symbol=symbol, timeframe=timeframe_name, result=result)
        result["journal_execution_id"] = journal.log_execution(symbol=symbol, action=decision["action"], execution=execution)
    return result
