from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
import pandas as pd

@dataclass(frozen=True)
class ElliottSignal:
    direction:str; buy_score:float; sell_score:float; confidence:float; evidence:list[str]; pattern:str; pivots:list[dict[str,Any]]
    def to_dict(self): return asdict(self)

def analyze_elliott(frame:pd.DataFrame, *, swing_highs:list[int], swing_lows:list[int]) -> ElliottSignal:
    piv=sorted([(i,"H",float(frame.at[i,"high"])) for i in swing_highs[-4:]]+[(i,"L",float(frame.at[i,"low"])) for i in swing_lows[-4:]])
    pivots=[{"index":i,"type":t,"price":round(p,6)} for i,t,p in piv]
    buy=sell=0.0; evidence=[]; pattern="UNCONFIRMED"
    vals=[p for _,_,p in piv]
    if len(vals)>=5:
        last=vals[-5:]
        if last[0]<last[1] and last[2]>last[0] and last[3]>last[1] and last[4]>last[2]:
            buy+=6; pattern="BULLISH_IMPULSE_CANDIDATE"; evidence.append("Swing sequence resembles a bullish Elliott impulse candidate")
        elif last[0]>last[1] and last[2]<last[0] and last[3]<last[1] and last[4]<last[2]:
            sell+=6; pattern="BEARISH_IMPULSE_CANDIDATE"; evidence.append("Swing sequence resembles a bearish Elliott impulse candidate")
    total=buy+sell
    direction="NEUTRAL" if total==0 or buy==sell else ("BUY" if buy>sell else "SELL")
    conf=0.0 if total==0 else 100.0
    return ElliottSignal(direction,buy,sell,conf,evidence,pattern,pivots)
