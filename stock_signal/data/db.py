import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from config import DB_PATH

_local = threading.local()


def get_connection() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


@contextmanager
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tickers (
                symbol          TEXT PRIMARY KEY,
                active          INTEGER DEFAULT 1,
                added_at        DATETIME DEFAULT (datetime('now')),
                up_threshold    REAL DEFAULT 0.60,
                down_threshold  REAL DEFAULT 0.60
            );

            CREATE TABLE IF NOT EXISTS candles (
                symbol      TEXT NOT NULL,
                begins_at   DATETIME NOT NULL,
                open_price  REAL,
                high_price  REAL,
                low_price   REAL,
                close_price REAL,
                volume      INTEGER,
                PRIMARY KEY (symbol, begins_at)
            );

            CREATE INDEX IF NOT EXISTS idx_candles_symbol_ts
                ON candles (symbol, begins_at);

            CREATE TABLE IF NOT EXISTS signals (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol              TEXT NOT NULL,
                candle_ts           DATETIME NOT NULL,
                p_up                REAL,
                p_down              REAL,
                p_neutral           REAL,
                ml_signal           TEXT,
                final_signal        TEXT,
                confidence          REAL,
                ml_overridden       INTEGER DEFAULT 0,
                override_reason     TEXT,
                rationale           TEXT,
                flags               TEXT,
                model_version       TEXT,
                agent_prompt_version TEXT,
                outcome_at_4c       TEXT,
                created_at          DATETIME DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_signals_symbol_ts
                ON signals (symbol, candle_ts);

            CREATE TABLE IF NOT EXISTS agent_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id   INTEGER REFERENCES signals(id),
                prompt_sent TEXT,
                response_raw TEXT,
                latency_ms  INTEGER,
                error       TEXT,
                created_at  DATETIME DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS model_meta (
                symbol      TEXT NOT NULL,
                version     TEXT NOT NULL,
                trained_at  DATETIME DEFAULT (datetime('now')),
                sample_count INTEGER,
                precision_up REAL,
                recall_up   REAL,
                f1_up       REAL,
                precision_down REAL,
                recall_down REAL,
                f1_down     REAL,
                accuracy    REAL,
                abstention_rate REAL,
                is_current  INTEGER DEFAULT 1,
                PRIMARY KEY (symbol, version)
            );
        """)


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
