"""
utils/signals.py
Composite BUY / SELL / HOLD signal engine.
Each strategy returns a score (0-100) + direction + explanation list.
The composite score is a weighted average of all active strategies.
"""

import pandas as pd
import numpy as np
from utils.indicators import enrich

# ── Score → Label ──────────────────────────────────────────────────────────────

def score_to_label(score: float) -> tuple[str, str]:
    """Convert 0-100 score to (label, css_class)."""
    if score >= 60:
        return "BUY",  "gauge-buy"
    if score <= 40:
        return "SELL", "gauge-sell"
    return "HOLD", "gauge-hold"


def score_to_confidence(score: float) -> str:
    distance = abs(score - 50)
    if distance >= 30: return "HIGH"
    if distance >= 15: return "MEDIUM"
    return "LOW"


# ── Individual Strategies ──────────────────────────────────────────────────────

def strategy_rsi(df: pd.DataFrame, oversold=30, overbought=70) -> dict:
    """RSI mean-reversion strategy."""
    signals, reasons = [], []
    if "RSI" not in df.columns:
        return {"name": "RSI", "score": 50, "signals": []}
    rsi = df["RSI"].iloc[-1]
    if pd.isna(rsi):
        return {"name": "RSI", "score": 50, "signals": []}

    if rsi < oversold:
        signals.append(100)
        reasons.append(f"RSI={rsi:.1f} — deeply oversold (< {oversold}) → BUY")
    elif rsi < 40:
        signals.append(70)
        reasons.append(f"RSI={rsi:.1f} — approaching oversold → Mild BUY")
    elif rsi > overbought:
        signals.append(0)
        reasons.append(f"RSI={rsi:.1f} — overbought (> {overbought}) → SELL")
    elif rsi > 60:
        signals.append(35)
        reasons.append(f"RSI={rsi:.1f} — approaching overbought → Mild SELL")
    else:
        signals.append(50)
        reasons.append(f"RSI={rsi:.1f} — neutral zone")

    return {"name": "RSI", "score": np.mean(signals), "signals": reasons}


def strategy_macd(df: pd.DataFrame) -> dict:
    """MACD crossover strategy."""
    if not all(c in df.columns for c in ["MACD", "MACD_signal", "MACD_hist"]):
        return {"name": "MACD", "score": 50, "signals": []}
    reasons = []
    scores  = []

    macd   = df["MACD"].iloc[-1]
    sig    = df["MACD_signal"].iloc[-1]
    hist   = df["MACD_hist"].iloc[-1]
    prev_h = df["MACD_hist"].iloc[-2] if len(df) > 1 else 0

    if pd.isna(macd) or pd.isna(sig):
        return {"name": "MACD", "score": 50, "signals": []}

    # Crossover
    if macd > sig and df["MACD"].iloc[-2] <= df["MACD_signal"].iloc[-2]:
        scores.append(85)
        reasons.append("MACD bullish crossover (MACD crossed above Signal) → BUY")
    elif macd < sig and df["MACD"].iloc[-2] >= df["MACD_signal"].iloc[-2]:
        scores.append(15)
        reasons.append("MACD bearish crossover (MACD crossed below Signal) → SELL")
    elif macd > sig:
        scores.append(65)
        reasons.append(f"MACD above Signal ({macd:.4f} > {sig:.4f}) → Bullish")
    else:
        scores.append(35)
        reasons.append(f"MACD below Signal ({macd:.4f} < {sig:.4f}) → Bearish")

    # Histogram momentum
    if hist > 0 and hist > prev_h:
        scores.append(70); reasons.append("MACD histogram expanding → Bullish momentum")
    elif hist < 0 and hist < prev_h:
        scores.append(30); reasons.append("MACD histogram contracting → Bearish momentum")

    # Zero-line
    if macd > 0:
        scores.append(60); reasons.append("MACD above zero-line → Overall uptrend")
    else:
        scores.append(40); reasons.append("MACD below zero-line → Overall downtrend")

    return {"name": "MACD", "score": np.mean(scores), "signals": reasons}


def strategy_ema_trend(df: pd.DataFrame) -> dict:
    """EMA alignment trend strategy."""
    reasons = []
    scores  = []
    price   = df["Close"].iloc[-1]

    for period in [20, 50, 200]:
        col = f"EMA_{period}"
        if col not in df.columns or pd.isna(df[col].iloc[-1]):
            continue
        ema_val = df[col].iloc[-1]
        if price > ema_val:
            pct = (price - ema_val) / ema_val * 100
            s = min(80, 50 + pct * 5)
            scores.append(s)
            reasons.append(f"Price ${price:.2f} > EMA{period} ${ema_val:.2f} (+{pct:.1f}%) → Bullish")
        else:
            pct = (ema_val - price) / ema_val * 100
            s = max(20, 50 - pct * 5)
            scores.append(s)
            reasons.append(f"Price ${price:.2f} < EMA{period} ${ema_val:.2f} (-{pct:.1f}%) → Bearish")

    # Golden/Death cross
    if "EMA_50" in df.columns and "EMA_200" in df.columns:
        e50 = df["EMA_50"].iloc[-1]
        e200= df["EMA_200"].iloc[-1]
        if not pd.isna(e50) and not pd.isna(e200):
            if e50 > e200:
                scores.append(70)
                reasons.append(f"Golden Cross active: EMA50 > EMA200 → Strong BUY signal")
            else:
                scores.append(30)
                reasons.append(f"Death Cross active: EMA50 < EMA200 → Strong SELL signal")

    if not scores:
        return {"name": "EMA Trend", "score": 50, "signals": ["Insufficient data"]}
    return {"name": "EMA Trend", "score": np.mean(scores), "signals": reasons}


def strategy_bollinger(df: pd.DataFrame) -> dict:
    """Bollinger Bands mean-reversion + squeeze strategy."""
    if not all(c in df.columns for c in ["BB_upper","BB_mid","BB_lower"]):
        return {"name": "Bollinger", "score": 50, "signals": []}
    reasons = []
    scores  = []
    price   = df["Close"].iloc[-1]
    upper   = df["BB_upper"].iloc[-1]
    lower   = df["BB_lower"].iloc[-1]
    mid     = df["BB_mid"].iloc[-1]

    if pd.isna(upper) or pd.isna(lower):
        return {"name": "Bollinger", "score": 50, "signals": []}

    pct_b = (price - lower) / (upper - lower + 1e-9)

    if price <= lower:
        scores.append(90); reasons.append(f"Price at/below lower BB ${lower:.2f} → Oversold BUY")
    elif price >= upper:
        scores.append(10); reasons.append(f"Price at/above upper BB ${upper:.2f} → Overbought SELL")
    elif pct_b < 0.25:
        scores.append(65); reasons.append(f"Price in lower 25% of BB band → Mild BUY")
    elif pct_b > 0.75:
        scores.append(35); reasons.append(f"Price in upper 75% of BB band → Mild SELL")
    else:
        scores.append(50); reasons.append(f"Price mid-band (B%={pct_b:.2f}) → Neutral")

    # Squeeze detection
    if "BB_width" in df.columns:
        width_now = df["BB_width"].iloc[-1]
        width_avg = df["BB_width"].rolling(20).mean().iloc[-1]
        if width_now < width_avg * 0.5:
            reasons.append("⚡ BB Squeeze detected — breakout likely soon")

    return {"name": "Bollinger", "score": np.mean(scores), "signals": reasons}


def strategy_stochastic(df: pd.DataFrame) -> dict:
    """Stochastic oscillator strategy."""
    if not all(c in df.columns for c in ["STOCH_K","STOCH_D"]):
        return {"name": "Stochastic", "score": 50, "signals": []}
    k = df["STOCH_K"].iloc[-1]
    d = df["STOCH_D"].iloc[-1]
    if pd.isna(k) or pd.isna(d):
        return {"name": "Stochastic", "score": 50, "signals": []}
    reasons = []
    scores  = []

    if k < 20 and d < 20:
        scores.append(85); reasons.append(f"Stoch K={k:.1f}, D={d:.1f} — both oversold → BUY")
    elif k > 80 and d > 80:
        scores.append(15); reasons.append(f"Stoch K={k:.1f}, D={d:.1f} — both overbought → SELL")
    elif k > d and df["STOCH_K"].iloc[-2] <= df["STOCH_D"].iloc[-2]:
        scores.append(75); reasons.append(f"Stoch K crossed above D → Bullish crossover")
    elif k < d and df["STOCH_K"].iloc[-2] >= df["STOCH_D"].iloc[-2]:
        scores.append(25); reasons.append(f"Stoch K crossed below D → Bearish crossover")
    else:
        s = 50 + (50 - k) * 0.3
        scores.append(s)
        reasons.append(f"Stoch K={k:.1f}, D={d:.1f} — neutral")

    return {"name": "Stochastic", "score": np.mean(scores), "signals": reasons}


def strategy_volume(df: pd.DataFrame) -> dict:
    """Volume confirmation strategy."""
    if "Volume" not in df.columns:
        return {"name": "Volume", "score": 50, "signals": []}
    reasons = []
    scores  = []
    vol_now = df["Volume"].iloc[-1]
    vol_avg = df["Volume"].rolling(20).mean().iloc[-1]
    price_chg = df["Close"].iloc[-1] - df["Close"].iloc[-2]

    if pd.isna(vol_avg) or vol_avg == 0:
        return {"name": "Volume", "score": 50, "signals": []}

    ratio = vol_now / vol_avg
    if ratio > 1.5 and price_chg > 0:
        scores.append(75); reasons.append(f"High volume ({ratio:.1f}x avg) on UP move → Confirmed bullish")
    elif ratio > 1.5 and price_chg < 0:
        scores.append(25); reasons.append(f"High volume ({ratio:.1f}x avg) on DOWN move → Confirmed bearish")
    elif ratio < 0.5:
        scores.append(50); reasons.append(f"Low volume ({ratio:.1f}x avg) — weak conviction")
    else:
        scores.append(50); reasons.append(f"Normal volume ({ratio:.1f}x avg) — no signal")

    return {"name": "Volume", "score": np.mean(scores), "signals": reasons}


# ── Composite Signal ───────────────────────────────────────────────────────────

STRATEGY_WEIGHTS = {
    "RSI":        1.5,
    "MACD":       2.0,
    "EMA Trend":  2.0,
    "Bollinger":  1.2,
    "Stochastic": 1.2,
    "Volume":     0.8,
}

def compute_composite_signal(df: pd.DataFrame, weights: dict = None) -> dict:
    """
    Run all strategies and return composite score + full analysis.
    Returns:
        score (float 0-100),
        label (BUY/SELL/HOLD),
        confidence (HIGH/MEDIUM/LOW),
        css_class,
        strategy_results (list of dicts),
        top_reasons (list of str)
    """
    if df is None or df.empty:
        return {"score": 50, "label": "HOLD", "confidence": "LOW",
                "css_class": "gauge-hold", "strategies": [], "reasons": ["No data"]}

    df = enrich(df)
    wts = weights or STRATEGY_WEIGHTS

    strategies = [
        strategy_rsi(df),
        strategy_macd(df),
        strategy_ema_trend(df),
        strategy_bollinger(df),
        strategy_stochastic(df),
        strategy_volume(df),
    ]

    total_weight = 0
    weighted_sum = 0
    for s in strategies:
        w = wts.get(s["name"], 1.0)
        weighted_sum += s["score"] * w
        total_weight += w

    score = weighted_sum / total_weight if total_weight > 0 else 50
    label, css = score_to_label(score)
    conf  = score_to_confidence(score)

    # Collect top reasons (bullish if BUY, bearish if SELL)
    all_reasons = []
    for s in strategies:
        all_reasons.extend(s.get("signals", []))

    return {
        "score":      round(score, 1),
        "label":      label,
        "confidence": conf,
        "css_class":  css,
        "strategies": strategies,
        "reasons":    all_reasons,
    }
