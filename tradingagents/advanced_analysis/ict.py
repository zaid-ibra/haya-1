from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import time
from typing import Any
import pandas as pd

@dataclass(frozen=True)
class ICTSignal:
    direction: str; buy_score: float; sell_score: float; confidence: float
    evidence: list[str]; kill_zone: str; ote: dict[str, Any]; judas_swing: dict[str, Any]
    def to_dict(self): return asdict(self)

def _kill_zone(frame: pd.DataFrame) -> str:
    if "time" not in frame.columns: return "UNKNOWN"
    ts = pd.to_datetime(frame.iloc[-1]["time"], errors="coerce", utc=True)
    if pd.isna(ts): return "UNKNOWN"
    t = ts.time()
    if time(7,0) <= t < time(10,0): return "LONDON"
    if time(12,0) <= t < time(15,0): return "NEW_YORK"
    if time(0,0) <= t < time(3,0): return "ASIA"
    return "OFF_SESSION"

def analyze_ict(frame: pd.DataFrame, *, swing_highs: list[int], swing_lows: list[int], smc: dict[str, Any]) -> ICTSignal:
    buy=sell=0.0; evidence=[]; kz=_kill_zone(frame)
    if kz in {"LONDON","NEW_YORK"}: evidence.append(f"Price is trading during the {kz.replace('_',' ').title()} kill zone")
    dr=smc.get("dealing_range", {})
    lo,hi=dr.get("low"),dr.get("high")
    ote={"available":False}
    if lo is not None and hi is not None and hi>lo:
        latest=float(frame.iloc[-1]["close"]); span=hi-lo
        bull_low=hi-0.79*span; bull_high=hi-0.62*span
        bear_low=lo+0.62*span; bear_high=lo+0.79*span
        ote={"available":True,"bullish_zone":[round(bull_low,6),round(bull_high,6)],"bearish_zone":[round(bear_low,6),round(bear_high,6)]}
        if bull_low <= latest <= bull_high: buy+=10; evidence.append("Price is inside the bullish ICT OTE zone")
        if bear_low <= latest <= bear_high: sell+=10; evidence.append("Price is inside the bearish ICT OTE zone")
    judas={"detected":False}
    sweeps=smc.get("liquidity",{}).get("sweeps",[])
    if sweeps and kz in {"LONDON","NEW_YORK"}:
        typ=sweeps[-1].get("type")
        if typ=="SELL_SIDE_SWEEP": buy+=10; judas={"detected":True,"direction":"BULLISH"}; evidence.append("Session liquidity sweep resembles a bullish Judas swing")
        elif typ=="BUY_SIDE_SWEEP": sell+=10; judas={"detected":True,"direction":"BEARISH"}; evidence.append("Session liquidity sweep resembles a bearish Judas swing")
    total=buy+sell
    if total==0: direction,conf="NEUTRAL",0.0
    elif buy>sell: direction,conf="BUY",round(100*buy/total,2)
    elif sell>buy: direction,conf="SELL",round(100*sell/total,2)
    else: direction,conf="NEUTRAL",50.0
    return ICTSignal(direction,buy,sell,conf,evidence,kz,ote,judas)
