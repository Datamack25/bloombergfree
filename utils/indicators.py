"""
utils/indicators.py
Technical indicators using the 'ta' library (pip install ta).
Falls back to manual pandas calculations if ta is unavailable.
"""

import pandas as pd
import numpy as np

try:
    import ta
    HAS_TA = True
except ImportError:
    HAS_TA = False


# ── Moving Averages ────────────────────────────────────────────────────────────

def add_sma(df: pd.DataFrame, periods=(9, 20, 50, 200)) -> pd.DataFrame:
    for p in periods:
        df[f"SMA_{p}"] = df["Close"].rolling(p).mean()
    return df


def add_ema(df: pd.DataFrame, periods=(9, 20, 50, 200)) -> pd.DataFrame:
    for p in periods:
        df[f"EMA_{p}"] = df["Close"].ewm(span=p, adjust=False).mean()
    return df


# ── Bollinger Bands ───────────────────────────────────────────────────────────

def add_bollinger(df: pd.DataFrame, period=20, std=2) -> pd.DataFrame:
    if HAS_TA:
        ind = ta.volatility.BollingerBands(df["Close"], window=period, window_dev=std)
        df["BB_upper"] = ind.bollinger_hband()
        df["BB_mid"]   = ind.bollinger_mavg()
        df["BB_lower"] = ind.bollinger_lband()
    else:
        mid   = df["Close"].rolling(period).mean()
        sigma = df["Close"].rolling(period).std()
        df["BB_upper"] = mid + std * sigma
        df["BB_mid"]   = mid
        df["BB_lower"] = mid - std * sigma
    df["BB_width"] = (df["BB_upper"] - df["BB_lower"]) / (df["BB_mid"] + 1e-9)
    return df


# ── RSI ───────────────────────────────────────────────────────────────────────

def add_rsi(df: pd.DataFrame, period=14) -> pd.DataFrame:
    if HAS_TA:
        df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=period).rsi()
    else:
        delta = df["Close"].diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss.replace(0, np.nan)
        df["RSI"] = 100 - (100 / (1 + rs))
    return df


# ── MACD ──────────────────────────────────────────────────────────────────────

def add_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    if HAS_TA:
        ind = ta.trend.MACD(df["Close"], window_fast=fast, window_slow=slow, window_sign=signal)
        df["MACD"]        = ind.macd()
        df["MACD_signal"] = ind.macd_signal()
        df["MACD_hist"]   = ind.macd_diff()
    else:
        ema_fast    = df["Close"].ewm(span=fast,   adjust=False).mean()
        ema_slow    = df["Close"].ewm(span=slow,   adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        df["MACD"]        = macd_line
        df["MACD_signal"] = signal_line
        df["MACD_hist"]   = macd_line - signal_line
    return df


# ── Stochastic ────────────────────────────────────────────────────────────────

def add_stochastic(df: pd.DataFrame, k=14, d=3, smooth=3) -> pd.DataFrame:
    if HAS_TA:
        ind = ta.momentum.StochasticOscillator(
            df["High"], df["Low"], df["Close"], window=k, smooth_window=d)
        df["STOCH_K"] = ind.stoch()
        df["STOCH_D"] = ind.stoch_signal()
    else:
        low_min  = df["Low"].rolling(k).min()
        high_max = df["High"].rolling(k).max()
        k_pct    = 100 * (df["Close"] - low_min) / (high_max - low_min + 1e-9)
        df["STOCH_K"] = k_pct.rolling(smooth).mean()
        df["STOCH_D"] = df["STOCH_K"].rolling(d).mean()
    return df


# ── ATR ───────────────────────────────────────────────────────────────────────

def add_atr(df: pd.DataFrame, period=14) -> pd.DataFrame:
    if HAS_TA:
        df["ATR"] = ta.volatility.AverageTrueRange(
            df["High"], df["Low"], df["Close"], window=period).average_true_range()
    else:
        prev_close = df["Close"].shift(1)
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"]  - prev_close).abs(),
        ], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(period).mean()
    return df


# ── Ichimoku ──────────────────────────────────────────────────────────────────

def add_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    """Pure-pandas Ichimoku (no external dependency)."""
    def mid(high, low, p):
        return (high.rolling(p).max() + low.rolling(p).min()) / 2

    df["ICH_tenkan"] = mid(df["High"], df["Low"], 9)
    df["ICH_kijun"]  = mid(df["High"], df["Low"], 26)
    df["ICH_spana"]  = ((df["ICH_tenkan"] + df["ICH_kijun"]) / 2).shift(26)
    df["ICH_spanb"]  = mid(df["High"], df["Low"], 52).shift(26)
    df["ICH_chikou"] = df["Close"].shift(-26)
    return df


# ── OBV ───────────────────────────────────────────────────────────────────────

def add_obv(df: pd.DataFrame) -> pd.DataFrame:
    if HAS_TA:
        df["OBV"] = ta.volume.OnBalanceVolumeIndicator(
            df["Close"], df["Volume"]).on_balance_volume()
    else:
        direction = np.sign(df["Close"].diff())
        df["OBV"] = (direction * df["Volume"]).fillna(0).cumsum()
    return df


# ── VWAP ──────────────────────────────────────────────────────────────────────

def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    typical     = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"]  = (typical * df["Volume"]).cumsum() / df["Volume"].cumsum()
    return df


# ── Fibonacci ─────────────────────────────────────────────────────────────────

def fibonacci_levels(df: pd.DataFrame, lookback=100) -> dict:
    recent = df["Close"].iloc[-lookback:]
    high   = recent.max()
    low    = recent.min()
    diff   = high - low
    return {
        "0.0%":  high,
        "23.6%": high - 0.236 * diff,
        "38.2%": high - 0.382 * diff,
        "50.0%": high - 0.500 * diff,
        "61.8%": high - 0.618 * diff,
        "78.6%": high - 0.786 * diff,
        "100%":  low,
    }


# ── Full pipeline ─────────────────────────────────────────────────────────────

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or len(df) < 20:
        return df
    df = df.copy()
    df = add_sma(df)
    df = add_ema(df)
    df = add_bollinger(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_stochastic(df)
    df = add_atr(df)
    df = add_obv(df)
    df = add_vwap(df)
    if len(df) > 52:
        df = add_ichimoku(df)
    return df
