from datetime import datetime, timedelta, timezone

import pandas as pd

from config import (
    MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE,
    MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE,
    OPENING_SUPPRESS_MINUTES,
)
from data.db import db


def build_context(inference_result: dict) -> dict:
    symbol = inference_result["symbol"]
    candle_ts = inference_result["candle_ts"]

    with db() as conn:
        recent_rows = conn.execute(
            """SELECT candle_ts, ml_signal, final_signal, outcome_at_4c
               FROM signals WHERE symbol = ?
               ORDER BY candle_ts DESC LIMIT 10""",
            (symbol,),
        ).fetchall()

        cutoff_20d = (datetime.utcnow() - timedelta(days=20)).isoformat()
        precision_rows = conn.execute(
            """SELECT ml_signal, final_signal, outcome_at_4c
               FROM signals
               WHERE symbol = ? AND candle_ts >= ? AND outcome_at_4c IS NOT NULL""",
            (symbol, cutoff_20d),
        ).fetchall()

    recent_signals = [dict(r) for r in reversed(recent_rows)]

    up_correct = up_total = down_correct = down_total = 0
    for r in precision_rows:
        if r["ml_signal"] == "ML_GREEN":
            up_total += 1
            if r["outcome_at_4c"] == "UP":
                up_correct += 1
        elif r["ml_signal"] == "ML_RED":
            down_total += 1
            if r["outcome_at_4c"] == "DOWN":
                down_correct += 1

    up_precision = round(up_correct / up_total, 3) if up_total > 0 else None
    down_precision = round(down_correct / down_total, 3) if down_total > 0 else None

    streak_count = 0
    streak_direction = None
    if recent_signals:
        last_signal = recent_signals[-1]["ml_signal"]
        streak_direction = last_signal
        for s in reversed(recent_signals):
            if s["ml_signal"] == last_signal:
                streak_count += 1
            else:
                break

    ts = pd.to_datetime(candle_ts)
    now_hour = ts.hour
    now_minute = ts.minute
    open_minutes = now_hour * 60 + now_minute
    market_open_minutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
    market_close_minutes = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE

    is_opening_15min = open_minutes < market_open_minutes + OPENING_SUPPRESS_MINUTES
    is_closing_30min = open_minutes >= market_close_minutes - 30

    ctx = {
        **inference_result,
        "recent_signals": recent_signals,
        "up_precision": up_precision,
        "down_precision": down_precision,
        "streak_count": streak_count,
        "streak_direction": streak_direction,
        "is_opening_15min": is_opening_15min,
        "is_closing_30min": is_closing_30min,
    }
    return ctx
