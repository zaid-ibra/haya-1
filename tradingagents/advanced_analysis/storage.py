from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL,
    approved INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    executed INTEGER NOT NULL,
    success INTEGER NOT NULL,
    ticket TEXT,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cycles_symbol_time ON analysis_cycles(symbol, created_at);
CREATE INDEX IF NOT EXISTS idx_exec_symbol_time ON executions(symbol, created_at);
"""


class TradingJournal:
    """Small SQLite journal for reproducible analysis and execution auditing."""

    def __init__(self, path: str | Path = "data/haya_zaid_journal.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def log_cycle(self, *, symbol: str, timeframe: str, result: dict[str, Any]) -> int:
        decision = result.get("signal", {}).get("decision", {})
        action = str(decision.get("action", "HOLD"))
        confidence = float(decision.get("confidence", 0.0))
        approved = bool(decision.get("approved", False))
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO analysis_cycles(created_at,symbol,timeframe,action,confidence,approved,payload_json) VALUES(?,?,?,?,?,?,?)",
                (self._now(), symbol, timeframe, action, confidence, int(approved), json.dumps(result, default=str)),
            )
            return int(cursor.lastrowid)

    def log_execution(self, *, symbol: str, action: str, execution: dict[str, Any]) -> int:
        payload = execution.get("result") or {}
        ticket = payload.get("order") or payload.get("deal") or payload.get("position")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO executions(created_at,symbol,action,executed,success,ticket,payload_json) VALUES(?,?,?,?,?,?,?)",
                (
                    self._now(), symbol, action, int(bool(execution.get("executed"))),
                    int(bool(execution.get("success"))), None if ticket is None else str(ticket),
                    json.dumps(execution, default=str),
                ),
            )
            return int(cursor.lastrowid)

    def summary(self, symbol: str | None = None) -> dict[str, Any]:
        where = " WHERE symbol=?" if symbol else ""
        params = (symbol,) if symbol else ()
        with self._connect() as conn:
            cycles = conn.execute(
                f"SELECT COUNT(*), SUM(approved), AVG(confidence) FROM analysis_cycles{where}", params
            ).fetchone()
            executions = conn.execute(
                f"SELECT COUNT(*), SUM(executed), SUM(success) FROM executions{where}", params
            ).fetchone()
        return {
            "cycles": int(cycles[0] or 0),
            "approved_cycles": int(cycles[1] or 0),
            "average_confidence": round(float(cycles[2] or 0.0), 2),
            "execution_records": int(executions[0] or 0),
            "executed": int(executions[1] or 0),
            "successful": int(executions[2] or 0),
        }
