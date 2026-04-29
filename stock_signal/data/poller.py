import logging
import time
from datetime import datetime, timezone
from typing import List

import robin_stocks.robinhood as rh

from config import (
    MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE,
    MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE,
    OUTSIDE_HOURS_CHECK_SECONDS, POLL_INTERVAL_SECONDS,
    RH_PASSWORD, RH_USERNAME,
)
from data.db import db, init_db

logger = logging.getLogger(__name__)


def login(attempt: int = 1) -> bool:
    try:
        rh.login(RH_USERNAME, RH_PASSWORD, store_session=True)
        logger.info("Robinhood login successful")
        return True
    except Exception as e:
        logger.error("Login attempt %d failed: %s", attempt, e)
        if attempt >= 3:
            logger.critical("Login failed 3 times — manual intervention required")
            return False
        time.sleep(2 ** attempt)
        return login(attempt + 1)


def is_market_open() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    open_time = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0)
    close_time = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0)
    return open_time <= now <= close_time


def get_active_tickers() -> List[str]:
    with db() as conn:
        rows = conn.execute(
            "SELECT symbol FROM tickers WHERE active = 1"
        ).fetchall()
    return [r["symbol"] for r in rows]


def fetch_and_store(symbols: List[str]) -> None:
    if not symbols:
        return
    try:
        data = rh.get_stock_historicals(
            symbols, interval="5minute", span="day", bounds="regular"
        )
    except Exception as e:
        logger.error("Failed to fetch historicals: %s", e)
        return

    rows = []
    for candle in data:
        if not candle or candle.get("begins_at") is None:
            continue
        rows.append((
            candle["symbol"],
            candle["begins_at"],
            float(candle.get("open_price") or 0),
            float(candle.get("high_price") or 0),
            float(candle.get("low_price") or 0),
            float(candle.get("close_price") or 0),
            int(candle.get("volume") or 0),
        ))

    if rows:
        with db() as conn:
            conn.executemany(
                """INSERT OR IGNORE INTO candles
                   (symbol, begins_at, open_price, high_price, low_price, close_price, volume)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
        logger.info("Stored %d candles for %s", len(rows), symbols)


def run_poller() -> None:
    init_db()
    if not login():
        return

    logger.info("Poller started")
    while True:
        if is_market_open():
            tickers = get_active_tickers()
            if tickers:
                fetch_and_store(tickers)
            else:
                logger.info("No active tickers")
            time.sleep(POLL_INTERVAL_SECONDS)
        else:
            logger.debug("Market closed — sleeping %ds", OUTSIDE_HOURS_CHECK_SECONDS)
            time.sleep(OUTSIDE_HOURS_CHECK_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_poller()
