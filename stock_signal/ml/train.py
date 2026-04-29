import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, precision_recall_fscore_support
from xgboost import XGBClassifier

from config import BASE_DIR, MIN_TRAINING_SAMPLES
from data.db import db
from ml.features import FEATURE_COLS, compute_features
from ml.labels import generate_labels

logger = logging.getLogger(__name__)

MODELS_DIR = BASE_DIR / "ml" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def load_candles(symbol: str) -> pd.DataFrame:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM candles WHERE symbol = ? ORDER BY begins_at",
            (symbol,),
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def train_ticker(symbol: str) -> dict | None:
    df = load_candles(symbol)
    if df.empty:
        logger.warning("No candles for %s", symbol)
        return None

    df = compute_features(df)
    df = generate_labels(df)
    df = df.dropna(subset=FEATURE_COLS)

    cutoff = datetime.utcnow() - timedelta(days=20)
    df["begins_at"] = pd.to_datetime(df["begins_at"])
    train_df = df[df["begins_at"] < cutoff]
    val_df = df[df["begins_at"] >= cutoff]

    if len(train_df) < MIN_TRAINING_SAMPLES:
        logger.warning(
            "Insufficient data for %s: %d samples (need %d)",
            symbol, len(train_df), MIN_TRAINING_SAMPLES,
        )
        with db() as conn:
            conn.execute(
                "UPDATE tickers SET active = 1 WHERE symbol = ?", (symbol,)
            )
        return None

    X_train = train_df[FEATURE_COLS].values
    y_train = train_df["label"].values
    X_val = val_df[FEATURE_COLS].values if not val_df.empty else None
    y_val = val_df["label"].values if not val_df.empty else None

    classes, counts = np.unique(y_train, return_counts=True)
    class_dist = dict(zip(classes.tolist(), counts.tolist()))
    majority = max(counts)
    minority_up = counts[classes == 0][0] if 0 in classes else 1
    scale_pos_weight = majority / minority_up

    eval_set = [(X_val, y_val)] if X_val is not None and len(X_val) > 0 else None

    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="mlogloss",
        use_label_encoder=False,
        early_stopping_rounds=20 if eval_set else None,
        num_class=3,
        objective="multi:softprob",
        random_state=42,
        verbosity=0,
    )

    model.fit(
        X_train, y_train,
        eval_set=eval_set,
        verbose=False,
    )

    metrics = {}
    if y_val is not None and len(y_val) > 0:
        y_pred = model.predict(X_val)
        report = classification_report(y_val, y_pred, output_dict=True, zero_division=0)
        metrics = {
            "precision_up": report.get("0", {}).get("precision", 0),
            "recall_up": report.get("0", {}).get("recall", 0),
            "f1_up": report.get("0", {}).get("f1-score", 0),
            "precision_down": report.get("1", {}).get("precision", 0),
            "recall_down": report.get("1", {}).get("recall", 0),
            "f1_down": report.get("1", {}).get("f1-score", 0),
            "accuracy": report.get("accuracy", 0),
            "abstention_rate": float((y_pred == 2).sum()) / len(y_pred),
        }
        logger.info("Metrics for %s: %s", symbol, metrics)

    version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    model_path = MODELS_DIR / f"{symbol}_{version}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    with db() as conn:
        conn.execute(
            "UPDATE model_meta SET is_current = 0 WHERE symbol = ?", (symbol,)
        )
        conn.execute(
            """INSERT INTO model_meta
               (symbol, version, sample_count, precision_up, recall_up, f1_up,
                precision_down, recall_down, f1_down, accuracy, abstention_rate, is_current)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                symbol, version, len(train_df),
                metrics.get("precision_up"), metrics.get("recall_up"), metrics.get("f1_up"),
                metrics.get("precision_down"), metrics.get("recall_down"), metrics.get("f1_down"),
                metrics.get("accuracy"), metrics.get("abstention_rate"),
            ),
        )

    logger.info("Trained model for %s → %s", symbol, model_path)
    return {"symbol": symbol, "version": version, "metrics": metrics}


def train_all() -> None:
    with db() as conn:
        tickers = [
            r["symbol"]
            for r in conn.execute("SELECT symbol FROM tickers WHERE active = 1").fetchall()
        ]
    for symbol in tickers:
        train_ticker(symbol)


def rollback_model(symbol: str) -> bool:
    with db() as conn:
        rows = conn.execute(
            "SELECT version FROM model_meta WHERE symbol = ? ORDER BY trained_at DESC LIMIT 2",
            (symbol,),
        ).fetchall()
    if len(rows) < 2:
        logger.warning("No prior model to roll back to for %s", symbol)
        return False
    prev_version = rows[1]["version"]
    with db() as conn:
        conn.execute("UPDATE model_meta SET is_current = 0 WHERE symbol = ?", (symbol,))
        conn.execute(
            "UPDATE model_meta SET is_current = 1 WHERE symbol = ? AND version = ?",
            (symbol, prev_version),
        )
    logger.info("Rolled back %s to version %s", symbol, prev_version)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_all()
