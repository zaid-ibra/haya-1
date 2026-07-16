# HAYA-ZAID AI Trading System

HAYA-ZAID is the branded gold-trading distribution built on top of the original TradingAgents framework. The original open-source license and attribution remain included in `LICENSE` and the upstream `README.md`.

## Safe first run

Install the project in a Python 3.10–3.12 virtual environment, install the MetaTrader5 package, open and log in to the MT5 terminal, then run:

```bash
python run_haya_zaid.py --balance 10000
```

This uses **dry-run mode by default**. It analyzes XAUUSD M5 and prepares an order request without sending it.

A real order is only permitted when `--live` is explicitly supplied:

```bash
python run_haya_zaid.py --balance 10000 --live
```

Do not use live mode until symbol specifications, point value, lot step, minimum stop distance, spread limits, and historical performance have been validated for the connected broker.

## Brand identity

- Product: HAYA-ZAID
- Full name: HAYA-ZAID AI Trading System
- MT5 order comment: HAYA-ZAID AI
- Version: 1.0.0

## Architecture

The internal Python package remains named `tradingagents` for compatibility with the upstream framework and existing imports. User-facing branding, CLI entry points, documentation, and MT5 comments use HAYA-ZAID.
