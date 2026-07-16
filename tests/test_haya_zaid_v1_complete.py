import sqlite3
import numpy as np
import pandas as pd

from tradingagents.advanced_analysis.risk import build_risk_plan
from tradingagents.advanced_analysis.storage import TradingJournal
from tradingagents.advanced_analysis.trade_manager import build_position_management_plan
from tradingagents.advanced_analysis.backtest import run_walk_forward_backtest


def candles(n=280):
    x=np.arange(n,dtype=float); close=1900+x*0.22+np.sin(x/4)*2.2
    return pd.DataFrame({"time":pd.date_range("2026-01-01",periods=n,freq="5min",tz="UTC"),"open":close-0.2,"high":close+1.1,"low":close-1.1,"close":close,"tick_volume":100+(x%20)})


def test_broker_aware_risk_sizing():
    plan=build_risk_plan(action="BUY",entry=2000,swing_high=2010,swing_low=1995,balance=10000,risk_percent=1,tick_size=0.01,tick_value=1, min_volume=0.01,max_volume=10,volume_step=0.01)
    assert plan.valid
    assert plan.estimated_loss <= 100.01
    assert plan.take_profit > plan.entry


def test_position_manager_break_even_and_trailing():
    plan=build_position_management_plan(position={"ticket":1,"action":"BUY","entry":2000,"stop_loss":1995,"volume":0.1},current_price=2010,atr=2)
    assert plan.update_stop
    assert plan.new_stop_loss >= 2000
    assert plan.partial_close_volume > 0


def test_sqlite_journal(tmp_path):
    path=tmp_path/"journal.sqlite3"
    journal=TradingJournal(path)
    cycle={"signal":{"decision":{"action":"BUY","confidence":80,"approved":True}},"execution":{"success":True,"executed":False}}
    assert journal.log_cycle(symbol="XAUUSD",timeframe="M5",result=cycle)>0
    assert journal.log_execution(symbol="XAUUSD",action="BUY",execution=cycle["execution"])>0
    summary=journal.summary("XAUUSD")
    assert summary["cycles"]==1 and summary["execution_records"]==1
    with sqlite3.connect(path) as conn:
        assert conn.execute("select count(*) from analysis_cycles").fetchone()[0]==1


def test_backtest_report_has_advanced_metrics():
    report=run_walk_forward_backtest(candles(),warmup=220,horizon=6,step=10)
    data=report.to_dict()
    assert "sharpe" in data and "expectancy_r" in data and data["skipped"] >= 0
