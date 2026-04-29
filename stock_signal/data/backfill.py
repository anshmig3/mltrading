import logging
from typing import List

import robin_stocks.robinhood as rh

from data.db import db

logger = logging.getLogger(__name__)


def backfill_ticker(symbol: str) -> int:
    logger.info("Backfilling %s (span=week)", symbol)
    try:
        data = rh.get_stock_historicals(
            [symbol], interval="5minute", span="week", bounds="regular"
        )
    except Exception as e:
        logger.error("Backfill failed for %s: %s", symbol, e)
        return 0

    rows = [
        (
            c["symbol"],
            c["begins_at"],
            float(c.get("open_price") or 0),
            float(c.get("high_price") or 0),
            float(c.get("low_price") or 0),
            float(c.get("close_price") or 0),
            int(c.get("volume") or 0),
        )
        for c in data
        if c and c.get("begins_at")
    ]

    if rows:
        with db() as conn:
            conn.executemany(
                """INSERT OR IGNORE INTO candles
                   (symbol, begins_at, open_price, high_price, low_price, close_price, volume)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
        logger.info("Backfilled %d candles for %s", len(rows), symbol)

    return len(rows)
