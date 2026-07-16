from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
import pandas as pd

@dataclass(frozen=True)
class WyckoffSignal:
    direction:str; buy_score:float; sell_score:float; confidence:float; evidence:list[str]; phase:str; events:list[dict[str,Any]]
    def to_dict(self): return asdict(self)

def analyze_wyckoff(frame: pd.DataFrame, lookback:int=80) -> WyckoffSignal:
    sample=frame.tail(max(40,lookback)); latest=sample.iloc[-1]
    rng=float(sample.high.max()-sample.low.min()); avg=max(float((sample.high-sample.low).mean()),1e-12)
    compression=rng/(avg*len(sample))
    buy=sell=0.0; evidence=[]; events=[]; phase="RANGE"
    vol=sample["volume"] if "volume" in sample.columns else pd.Series(1.0,index=sample.index)
    recent=sample.tail(20)
    low=float(recent.low.min()); high=float(recent.high.max())
    if float(latest.low)<low+avg*0.15 and float(latest.close)>low+avg*0.5:
        buy+=10; events.append({"type":"SPRING","level":round(low,6)}); evidence.append("Possible Wyckoff spring with rejection from range lows")
    if float(latest.high)>high-avg*0.15 and float(latest.close)<high-avg*0.5:
        sell+=10; events.append({"type":"UPTHRUST","level":round(high,6)}); evidence.append("Possible Wyckoff upthrust with rejection from range highs")
    if float(latest.close)>high: buy+=8; phase="MARKUP"; evidence.append("Price shows a possible Wyckoff sign of strength")
    elif float(latest.close)<low: sell+=8; phase="MARKDOWN"; evidence.append("Price shows a possible Wyckoff sign of weakness")
    elif compression<0.12: phase="ACCUMULATION_OR_DISTRIBUTION"
    total=buy+sell
    direction="NEUTRAL" if total==0 or buy==sell else ("BUY" if buy>sell else "SELL")
    conf=0.0 if total==0 else round(100*max(buy,sell)/total,2)
    return WyckoffSignal(direction,buy,sell,conf,evidence,phase,events)
