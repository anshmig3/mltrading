import numpy as np
import pandas as pd


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all BRD-specified features from OHLCV candle dataframe.

    Input df must have columns: open_price, high_price, low_price, close_price, volume, begins_at.
    Returns df with feature columns appended; rows with NaN features are dropped.
    """
    df = df.copy().sort_values("begins_at").reset_index(drop=True)

    close = df["close_price"]
    high = df["high_price"]
    low = df["low_price"]
    open_ = df["open_price"]
    volume = df["volume"]

    # --- Momentum ---
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, min_periods=14).mean()
    avg_loss = loss.ewm(com=13, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    df["macd_hist"] = macd_line - signal_line
    crossover = (
        (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1)) |
        (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
    )
    df["macd_crossover"] = crossover.rolling(3).max().fillna(0).astype(int)

    # --- Volatility ---
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    df["bb_position"] = (close - bb_lower) / bb_range

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = tr.ewm(com=13, min_periods=14).mean()
    df["atr_pct"] = df["atr_14"].rolling(90 * 78).rank(pct=True)

    # --- Volume ---
    vol_mean = volume.rolling(20).mean().replace(0, np.nan)
    df["volume_ratio"] = volume / vol_mean
    vol_slope = volume.rolling(5).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 5 else np.nan,
        raw=True,
    )
    df["volume_trend"] = vol_slope

    # --- Price action ---
    df["return_1c"] = close.pct_change(1)
    df["return_3c"] = close.pct_change(3)
    df["return_5c"] = close.pct_change(5)
    candle_range = (high - low).replace(0, np.nan)
    df["candle_body_ratio"] = (close - open_).abs() / candle_range
    df["upper_wick_ratio"] = (high - pd.concat([open_, close], axis=1).max(axis=1)) / candle_range
    df["lower_wick_ratio"] = (pd.concat([open_, close], axis=1).min(axis=1) - low) / candle_range

    # --- Time ---
    ts = pd.to_datetime(df["begins_at"])
    df["hour_of_day"] = ts.dt.hour
    df["minute_of_hour"] = ts.dt.minute
    df["day_of_week"] = ts.dt.dayofweek

    # --- Context: 52-week high/low ---
    window_52w = min(len(df), 52 * 5 * 78)
    high_52w = high.rolling(window_52w, min_periods=1).max()
    low_52w = low.rolling(window_52w, min_periods=1).min()
    df["dist_52w_high"] = (close - high_52w) / high_52w.replace(0, np.nan)
    df["dist_52w_low"] = (close - low_52w) / low_52w.replace(0, np.nan)

    return df


FEATURE_COLS = [
    "rsi_14", "macd_hist", "macd_crossover",
    "bb_position", "atr_14", "atr_pct",
    "volume_ratio", "volume_trend",
    "return_1c", "return_3c", "return_5c",
    "candle_body_ratio", "upper_wick_ratio", "lower_wick_ratio",
    "hour_of_day", "minute_of_hour", "day_of_week",
    "dist_52w_high", "dist_52w_low",
]
