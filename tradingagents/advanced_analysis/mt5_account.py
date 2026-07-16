from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SymbolTradingSpec:
    symbol: str
    point: float
    digits: int
    tick_size: float
    tick_value: float
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level_points: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_mt5_symbol_spec(symbol: str) -> SymbolTradingSpec:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 package is not installed") from exc
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Symbol is unavailable in MT5: {symbol}")
        if not info.visible and not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Unable to select symbol in Market Watch: {symbol}")
        return SymbolTradingSpec(
            symbol=symbol, point=float(info.point), digits=int(info.digits),
            tick_size=float(info.trade_tick_size or info.point),
            tick_value=float(info.trade_tick_value or info.trade_tick_value_profit or 0.0),
            volume_min=float(info.volume_min), volume_max=float(info.volume_max),
            volume_step=float(info.volume_step), stops_level_points=int(info.trade_stops_level),
        )
    finally:
        mt5.shutdown()
