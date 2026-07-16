"""Safe command-line entry point for HAYA-ZAID AI Trading System."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

from tradingagents.branding import banner
from tradingagents.advanced_analysis.gold_mt5_pipeline import run_gold_cycle
from tradingagents.advanced_analysis.backtest import run_walk_forward_backtest
from tradingagents.advanced_analysis.storage import TradingJournal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HAYA-ZAID analysis, backtest and journal tools.")
    sub = parser.add_subparsers(dest="command")

    cycle = sub.add_parser("cycle", help="Run one MT5 analysis cycle (default).")
    cycle.add_argument("--balance", type=float, required=True)
    cycle.add_argument("--symbol", default="XAUUSD")
    cycle.add_argument("--timeframe", default="M5")
    cycle.add_argument("--bars", type=int, default=500)
    cycle.add_argument("--risk-percent", type=float, default=1.0)
    cycle.add_argument("--point-value-per-lot", type=float, default=1.0)
    cycle.add_argument("--journal", default="data/haya_zaid_journal.sqlite3")
    cycle.add_argument("--live", action="store_true", help="Allow a real MT5 order; dry-run is the default.")

    backtest = sub.add_parser("backtest", help="Backtest a CSV file containing OHLC data.")
    backtest.add_argument("csv")
    backtest.add_argument("--warmup", type=int, default=220)
    backtest.add_argument("--horizon", type=int, default=12)
    backtest.add_argument("--min-confidence", type=float, default=65.0)
    backtest.add_argument("--rr", type=float, default=2.0)
    backtest.add_argument("--spread", type=float, default=0.0)

    journal = sub.add_parser("journal", help="Show SQLite journal summary.")
    journal.add_argument("--path", default="data/haya_zaid_journal.sqlite3")
    journal.add_argument("--symbol", default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    print(banner())
    command = args.command or "cycle"
    if command == "cycle":
        if not hasattr(args, "balance"):
            parser.error("cycle requires --balance")
        result = run_gold_cycle(
            balance=args.balance, symbol=args.symbol, timeframe_name=args.timeframe,
            bars=args.bars, risk_percent=args.risk_percent,
            point_value_per_lot=args.point_value_per_lot,
            dry_run=not args.live, journal_path=args.journal,
        )
    elif command == "backtest":
        path = Path(args.csv)
        if not path.exists():
            parser.error(f"CSV file not found: {path}")
        frame = pd.read_csv(path)
        result = run_walk_forward_backtest(
            frame, warmup=args.warmup, horizon=args.horizon,
            min_confidence=args.min_confidence, min_rr=args.rr, spread=args.spread,
        ).to_dict()
    else:
        result = TradingJournal(args.path).summary(args.symbol)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
