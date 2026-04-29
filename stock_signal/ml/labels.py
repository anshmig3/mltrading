import pandas as pd

from config import LABEL_HORIZON_CANDLES, LABEL_PCT_THRESHOLD


def generate_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'label' column: UP=0, DOWN=1, NEUTRAL=2."""
    df = df.copy()
    close = df["close_price"]
    labels = []

    for i in range(len(df)):
        future = close.iloc[i + 1: i + 1 + LABEL_HORIZON_CANDLES]
        if future.empty:
            labels.append(None)
            continue
        c = close.iloc[i]
        if future.max() >= c * (1 + LABEL_PCT_THRESHOLD):
            labels.append(0)  # UP
        elif future.min() <= c * (1 - LABEL_PCT_THRESHOLD):
            labels.append(1)  # DOWN
        else:
            labels.append(2)  # NEUTRAL

    df["label"] = labels
    return df.dropna(subset=["label"]).astype({"label": int})
