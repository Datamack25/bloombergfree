"""
utils/sentiment.py
News sentiment analysis using VADER (free, no API needed).
Falls back to TextBlob if VADER is unavailable.
"""

import re
import streamlit as st
import pandas as pd

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
    HAS_VADER = True
except ImportError:
    HAS_VADER = False

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False


def analyze_text(text: str) -> float:
    """Return compound sentiment score in [-1, +1]."""
    if not text or not text.strip():
        return 0.0
    clean = re.sub(r"http\S+|www\S+", "", text)
    clean = re.sub(r"[^\w\s.,!?]", " ", clean).strip()

    if HAS_VADER:
        return _vader.polarity_scores(clean)["compound"]
    if HAS_TEXTBLOB:
        return TextBlob(clean).sentiment.polarity
    # Very naive keyword fallback
    pos_words = {"surge","gain","rally","beat","record","strong","buy","bullish","profit","growth","upgrade","positive"}
    neg_words = {"crash","drop","fall","miss","weak","sell","bearish","loss","decline","downgrade","negative","risk","warn"}
    words = set(clean.lower().split())
    pos   = len(words & pos_words)
    neg   = len(words & neg_words)
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / (pos + neg)


def score_label(score: float) -> tuple[str, str]:
    """(label, color) for a sentiment score."""
    if score >=  0.2: return "Bullish 📈",  "#00d084"
    if score <= -0.2: return "Bearish 📉",  "#ff3b5c"
    return "Neutral ➡️", "#f59e0b"


def analyze_news(articles: list) -> pd.DataFrame:
    """
    Accept list of dicts with 'title' + optional 'summary'.
    Return DataFrame with sentiment scores.
    """
    rows = []
    for art in articles:
        text = (art.get("title", "") + " " + art.get("summary", "")).strip()
        score = analyze_text(text)
        label, color = score_label(score)
        rows.append({
            "Title":     art.get("title", "")[:100],
            "Source":    art.get("source", ""),
            "Published": art.get("published", ""),
            "URL":       art.get("url", ""),
            "Score":     round(score, 3),
            "Sentiment": label,
            "_color":    color,
        })
    df = pd.DataFrame(rows)
    return df


def aggregate_sentiment(df: pd.DataFrame) -> dict:
    """Summarise sentiment across all articles."""
    if df.empty:
        return {"mean": 0, "bullish": 0, "bearish": 0, "neutral": 0, "label": "Neutral", "color": "#f59e0b"}
    mean  = df["Score"].mean()
    bull  = (df["Score"] >=  0.2).sum()
    bear  = (df["Score"] <= -0.2).sum()
    neut  = len(df) - bull - bear
    label, color = score_label(mean)
    return {
        "mean":    round(mean, 3),
        "bullish": int(bull),
        "bearish": int(bear),
        "neutral": int(neut),
        "label":   label,
        "color":   color,
    }
