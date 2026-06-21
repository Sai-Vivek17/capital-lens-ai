"""SQLite storage for watchlists and scan history."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.schemas.models import WatchlistAlert, WatchlistItem, WatchlistScanResult, model_to_dict
from app.tools.finance_tools import fetch_market_data, resolve_ticker


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_settings().database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY,
                company_name TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                scanned_at TEXT NOT NULL,
                price_change_pct REAL,
                risk_score INTEGER,
                momentum_score INTEGER,
                snapshot_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                status TEXT NOT NULL,
                detail TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


def add_watchlist_ticker(query: str, db_path: Path | None = None) -> WatchlistItem:
    init_db(db_path)
    ticker = resolve_ticker(query)
    company_name = None
    try:
        company_name = fetch_market_data(ticker).company_name
    except Exception:
        company_name = ticker
    created_at = datetime.now(UTC).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO watchlist (ticker, company_name, created_at) VALUES (?, ?, ?)",
            (ticker, company_name, created_at),
        )
    return WatchlistItem(ticker=ticker, company_name=company_name, created_at=created_at)


def remove_watchlist_ticker(query: str, db_path: Path | None = None) -> None:
    init_db(db_path)
    ticker = resolve_ticker(query)
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))


def list_watchlist(db_path: Path | None = None) -> list[WatchlistItem]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT ticker, company_name, created_at FROM watchlist ORDER BY created_at DESC").fetchall()
    return [WatchlistItem(ticker=row["ticker"], company_name=row["company_name"], created_at=row["created_at"]) for row in rows]


def save_scan_result(result: WatchlistScanResult, db_path: Path | None = None) -> None:
    init_db(db_path)
    snapshot_json = json.dumps(model_to_dict(result), default=str)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO scan_results (ticker, scanned_at, price_change_pct, risk_score, momentum_score, snapshot_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                result.ticker,
                result.scanned_at.isoformat(),
                result.price_change_pct,
                result.risk_score,
                result.momentum_score,
                snapshot_json,
            ),
        )
        for alert in result.alerts:
            conn.execute(
                """
                INSERT INTO alerts (ticker, severity, category, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (alert.ticker, alert.severity, alert.category, alert.message, alert.created_at.isoformat()),
            )


def get_latest_scan(ticker: str, db_path: Path | None = None) -> WatchlistScanResult | None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT snapshot_json FROM scan_results WHERE ticker = ? ORDER BY scanned_at DESC, id DESC LIMIT 1",
            (ticker,),
        ).fetchone()
    if not row:
        return None
    payload: dict[str, Any] = json.loads(row["snapshot_json"])
    payload["alerts"] = [WatchlistAlert(**alert) for alert in payload.get("alerts", [])]
    return WatchlistScanResult(**payload)


def list_recent_alerts(limit: int = 25, db_path: Path | None = None) -> list[WatchlistAlert]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT ticker, severity, category, message, created_at FROM alerts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        WatchlistAlert(
            ticker=row["ticker"],
            severity=row["severity"],
            category=row["category"],
            message=row["message"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        for row in rows
    ]


def create_agent_run(run_id: str, query: str, mode: str, db_path: Path | None = None) -> None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO agent_runs (run_id, query, mode, status, started_at, completed_at, error)
            VALUES (?, ?, ?, ?, ?, NULL, NULL)
            """,
            (run_id, query, mode, "running", datetime.now(UTC).isoformat()),
        )


def record_agent_event(
    run_id: str,
    agent_name: str,
    attempt: int,
    status: str,
    detail: str,
    error: str | None = None,
    db_path: Path | None = None,
) -> None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO agent_events (run_id, agent_name, attempt, status, detail, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, agent_name, attempt, status, detail, error, datetime.now(UTC).isoformat()),
        )


def complete_agent_run(run_id: str, status: str, error: str | None = None, db_path: Path | None = None) -> None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE agent_runs
            SET status = ?, completed_at = ?, error = ?
            WHERE run_id = ?
            """,
            (status, datetime.now(UTC).isoformat(), error, run_id),
        )


def get_agent_events(run_id: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT run_id, agent_name, attempt, status, detail, error, created_at
            FROM agent_events
            WHERE run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]
