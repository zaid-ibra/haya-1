from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class DecisionResult:
    action:str; confidence:float; approved:bool; reasons:list[str]; thresholds:dict[str,Any]
    def to_dict(self): return asdict(self)

def make_decision(*, buy_score:float, sell_score:float, evidence:list[str], min_score:float=60.0, min_confidence:float=65.0, min_edge:float=15.0) -> DecisionResult:
    total=buy_score+sell_score
    if total<=0: return DecisionResult("HOLD",0.0,False,["No directional evidence"],{"min_score":min_score,"min_confidence":min_confidence,"min_edge":min_edge})
    action="BUY" if buy_score>sell_score else "SELL" if sell_score>buy_score else "HOLD"
    leading=max(buy_score,sell_score); edge=abs(buy_score-sell_score); confidence=round(100*leading/total,2)
    approved=action!="HOLD" and leading>=min_score and confidence>=min_confidence and edge>=min_edge
    reasons=list(evidence[-12:])
    if not approved: reasons.append("Signal did not pass final score, confidence, or edge thresholds")
    return DecisionResult(action if approved else "HOLD",confidence,approved,reasons,{"min_score":min_score,"min_confidence":min_confidence,"min_edge":min_edge,"leading_score":leading,"edge":edge})
