import numpy as np
import pandas as pd
from tradingagents.advanced_analysis.engine import analyze_market
from tradingagents.advanced_analysis.decision import make_decision
from tradingagents.advanced_analysis.risk import build_risk_plan
from tradingagents.advanced_analysis.mt5_execution import execute_mt5_order

def candles(n=260):
    x=np.arange(n,dtype=float); close=1900+x*0.25+np.sin(x/4)*2
    return pd.DataFrame({"time":pd.date_range("2026-01-01",periods=n,freq="5min",tz="UTC"),"open":close-0.2,"high":close+1,"low":close-1,"close":close,"tick_volume":100+(x%20)})

def test_new_layers_are_exposed():
    result=analyze_market(candles())
    assert result.ict["kill_zone"] in {"ASIA","LONDON","NEW_YORK","OFF_SESSION","UNKNOWN"}
    assert "phase" in result.wyckoff
    assert "pattern" in result.elliott_wave
    assert "approved" in result.decision

def test_decision_gate():
    d=make_decision(buy_score=100,sell_score=10,evidence=["x"])
    assert d.approved and d.action=="BUY"

def test_risk_and_dry_run_execution():
    p=build_risk_plan(action="BUY",entry=2000,swing_high=2010,swing_low=1995,balance=10000,point_value_per_lot=10)
    assert p.valid and p.take_profit>p.entry
    result=execute_mt5_order(p.to_dict(),dry_run=True)
    assert result["success"] and not result["executed"]
