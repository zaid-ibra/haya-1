# HAYA-ZAID AI Trading System — V1 Complete

This release completes the safe core workflow for XAUUSD M5:

- deterministic multi-layer technical analysis;
- broker-aware risk sizing using MT5 tick size, tick value and volume constraints;
- duplicate-position and spread safeguards in live execution;
- SQLite audit journal for every analysis and execution attempt;
- ATR/R-based break-even, trailing-stop and partial-close planning;
- walk-forward backtesting with SL/TP path simulation, profit factor, drawdown, expectancy and Sharpe-like metric;
- safe dry-run execution by default.

## Commands

```bash
python run_haya_zaid.py cycle --balance 10000
python run_haya_zaid.py backtest data/XAUUSD_M5.csv
python run_haya_zaid.py journal
```

Real execution requires the explicit `--live` flag. Use it only after broker calibration, historical testing and sustained demo validation.

## Important limitation

SMC, ICT, Wyckoff and Elliott labels are deterministic approximations of discretionary concepts. They are analysis features, not proof of institutional order flow and not a guarantee of profitability.
