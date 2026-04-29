import logging
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config import BASE_DIR, DEFAULT_DOWN_THRESHOLD, DEFAULT_UP_THRESHOLD
from data.db import db
from ml.features import FEATURE_COLS, compute_features

logger = logging.getLogger(__name__)

MODELS_DIR = BASE_DIR / "ml" / "models"


def get_current_model_version(symbol: str) -> Optional[str]:
    with db() as conn:
        row = conn.execute(
            "SELECT version FROM model_meta WHERE symbol = ? AND is_current = 1",
            (symbol,),
        ).fetchone()
    return row["version"] if row else None


def load_model(symbol: str, version: str):
    path = MODELS_DIR / f"{symbol}_{version}.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}")
    with open(path, "rb") as f:
        return pickle.load(f)


_model_cache: dict = {}


def get_model(symbol: str):
    version = get_current_model_version(symbol)
    if version is None:
        return None, None
    key = f"{symbol}_{version}"
    if key not in _model_cache:
        _model_cache.clear()
        _model_cache[key] = load_model(symbol, version)
    return _model_cache[key], version


def score_candle(symbol: str, candles_df: pd.DataFrame) -> Optional[dict]:
    model, version = get_model(symbol)
    if model is None:
        logger.warning("No model available for %s", symbol)
        return None

    df = compute_features(candles_df)
    df = df.dropna(subset=FEATURE_COLS)
    if df.empty:
        return None

    row = df.iloc[[-1]]
    X = row[FEATURE_COLS].values
    proba = model.predict_proba(X)[0]

    p_up, p_down, p_neutral = float(proba[0]), float(proba[1]), float(proba[2])

    with db() as conn:
        thresholds = conn.execute(
            "SELECT up_threshold, down_threshold FROM tickers WHERE symbol = ?",
            (symbol,),
        ).fetchone()

    up_thr = thresholds["up_threshold"] if thresholds else DEFAULT_UP_THRESHOLD
    down_thr = thresholds["down_threshold"] if thresholds else DEFAULT_DOWN_THRESHOLD

    if p_up > up_thr:
        ml_signal = "ML_GREEN"
    elif p_down > down_thr:
        ml_signal = "ML_RED"
    else:
        ml_signal = "ML_GRAY"

    candle_ts = str(row["begins_at"].iloc[0])

    return {
        "symbol": symbol,
        "candle_ts": candle_ts,
        "p_up": p_up,
        "p_down": p_down,
        "p_neutral": p_neutral,
        "ml_signal": ml_signal,
        "model_version": version,
        "close_price": float(row["close_price"].iloc[0]),
        "open_price": float(row["open_price"].iloc[0]),
        "high_price": float(row["high_price"].iloc[0]),
        "low_price": float(row["low_price"].iloc[0]),
        "volume": int(row["volume"].iloc[0]),
        "atr_pct": float(row["atr_pct"].iloc[0]) if not pd.isna(row["atr_pct"].iloc[0]) else 0.5,
    }


def run_inference_for_all() -> list:
    with db() as conn:
        tickers = [
            r["symbol"]
            for r in conn.execute("SELECT symbol FROM tickers WHERE active = 1").fetchall()
        ]

    results = []
    for symbol in tickers:
        with db() as conn:
            rows = conn.execute(
                """SELECT * FROM candles WHERE symbol = ?
                   ORDER BY begins_at DESC LIMIT 200""",
                (symbol,),
            ).fetchall()

        if not rows:
            continue

        candles_df = pd.DataFrame([dict(r) for r in reversed(rows)])
        result = score_candle(symbol, candles_df)
        if result:
            results.append(result)

    return results
