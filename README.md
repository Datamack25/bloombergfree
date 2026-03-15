# 📈 BloombergFree Terminal

> **A professional-grade, 100% free market terminal built with Streamlit — rivalling Bloomberg in features, costing absolutely nothing.**

[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Deploy](https://img.shields.io/badge/Deploy-Streamlit%20Cloud-FF4B4B)](https://share.streamlit.io)

---

## ✨ Features

| Module | Description |
|---|---|
| 🌐 **Dashboard** | Live indices (S&P, Nasdaq, Dow, VIX, BTC, Gold, Oil, Forex), top gainers/losers, market status |
| ⭐ **Watchlist** | Add/remove tickers, live prices refreshed every 60s, spark charts, price alerts, CSV import/export |
| 📊 **Chart Analysis** | Full candlestick + SMA/EMA 9-20-50-200, Bollinger, RSI, MACD, Stochastic, ATR, OBV, VWAP, Ichimoku, Fibonacci. Multi-timeframe (1m → 1W) |
| ⚡ **Signals** | Composite BUY/SELL/HOLD score (0–100) from 6 strategies, customisable weights, watchlist scanner |
| 🏢 **Fundamentals** | P/E, EPS, Revenue, Margins, D/E, ROE, Dividends, quarterly income/balance/cashflow |
| 📰 **News & Sentiment** | Live news from yfinance + Finnhub, VADER sentiment scoring, timeline chart, export |
| 🔍 **Screener** | Filter S&P 500 by market cap, P/E, dividend yield, beta, volume, sector. Export CSV |
| 💼 **Portfolio** | P&L tracker, allocation pie, VaR 95%/99%, CVaR, annualised volatility, benchmark comparison |
| 📅 **Economic Calendar** | Upcoming macro events (Finnhub live or static fallback) with impact colour-coding |
| 🤖 **AI Advisor** | Composite AI recommendation combining technical + fundamental + sentiment scores with narrative |

---

## 🚀 Quick Start (Local)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/bloombergfree.git
cd bloombergfree
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note:** `pandas-ta` requires a recent pip. If you get install errors:
> ```bash
> pip install --upgrade pip setuptools wheel
> pip install pandas-ta --no-build-isolation
> ```

### 4. Run the app
```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) — the terminal loads instantly. No API key required.

---

## 🔑 Optional: Finnhub Free API Key

Finnhub unlocks **real-time WebSocket quotes** and a **live economic calendar**.

1. Go to [https://finnhub.io](https://finnhub.io) and click **"Get free API key"**
2. Sign up (email only, 30 seconds)
3. Copy your key from the dashboard
4. In the BloombergFree sidebar → **🔑 Finnhub API Key** → paste it in

> Free tier: **60 calls/min**, WebSocket for US stocks, news, economic calendar.
> Zero credit card required.

---

## ☁️ Deploy to Streamlit Community Cloud (Free, 5 minutes)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "feat: BloombergFree terminal v1.0"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/bloombergfree.git
git push -u origin main
```

### Step 2 — Deploy
1. Go to [https://share.streamlit.io](https://share.streamlit.io)
2. Click **"New app"**
3. Select your repo: `YOUR_USERNAME/bloombergfree`
4. Main file path: `app.py`
5. Python version: **3.11** (recommended)
6. Click **"Deploy!"**

Your app will be live at `https://bloombergfree.streamlit.app` in ~2 minutes. 🎉

### Optional: Set Finnhub key as a secret
In Streamlit Cloud → App settings → **Secrets**:
```toml
FINNHUB_KEY = "your_key_here"
```

Then in `utils/data_fetcher.py`, the app can also read from:
```python
import os
key = st.session_state.get("finnhub_key") or os.getenv("FINNHUB_KEY", "")
```

---

## 🏗️ Project Structure

```
bloombergfree/
├── app.py                          # Entry point, global CSS, navigation
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml                 # Dark Bloomberg theme
├── pages/
│   ├── __init__.py
│   ├── dashboard.py                # Market overview
│   ├── watchlist.py                # Live watchlist
│   ├── charts.py                   # Candlestick + indicators
│   ├── signals_page.py             # BUY/SELL/HOLD engine
│   ├── fundamentals.py             # Financial statements
│   ├── news.py                     # News + VADER sentiment
│   ├── screener.py                 # Stock screener
│   ├── portfolio.py                # Portfolio tracker + VaR
│   ├── calendar_page.py            # Economic calendar
│   └── ai_advisor.py               # AI recommendation engine
└── utils/
    ├── __init__.py
    ├── data_fetcher.py             # All data access (yfinance + Finnhub)
    ├── indicators.py               # Technical indicators (pandas_ta)
    ├── signals.py                  # Signal strategies + composite score
    ├── sentiment.py                # VADER / TextBlob sentiment
    └── charts.py                   # Plotly chart builders
```

---

## 🔧 Data Sources

| Source | What | Key required? | Cost |
|---|---|---|---|
| **yfinance** | Prices, OHLCV, fundamentals, news | ❌ None | Free |
| **Finnhub** | Real-time quotes, news, economic calendar | ✅ Optional free | Free tier |
| **Wikipedia** | S&P 500 ticker list | ❌ None | Free |
| **VADER** | Sentiment analysis (NLP) | ❌ None | Free |

---

## ⚙️ Configuration

### Refresh interval
Data is cached with `@st.cache_data(ttl=60)` — 60-second refresh by default.
Change in `utils/data_fetcher.py`:
```python
@st.cache_data(ttl=60)  # change to 30 for faster refresh
```

### Default watchlist
Edit `app.py`:
```python
st.session_state.watchlist = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "BTC-USD"]
```

### Custom signal weights
In `utils/signals.py`:
```python
STRATEGY_WEIGHTS = {
    "RSI":        1.5,
    "MACD":       2.0,
    "EMA Trend":  2.0,
    "Bollinger":  1.2,
    "Stochastic": 1.2,
    "Volume":     0.8,
}
```

---

## 🧩 Technical Indicators Available

| Indicator | Description |
|---|---|
| SMA 9/20/50/200 | Simple Moving Averages |
| EMA 9/20/50/200 | Exponential Moving Averages |
| Bollinger Bands | Upper/Mid/Lower + Width (squeeze detection) |
| RSI (14) | Relative Strength Index |
| MACD (12/26/9) | Moving Average Convergence Divergence |
| Stochastic (14/3) | Stochastic Oscillator %K/%D |
| ATR (14) | Average True Range |
| OBV | On-Balance Volume |
| VWAP | Volume Weighted Average Price |
| Ichimoku Cloud | Tenkan, Kijun, Span A/B, Chikou |
| Fibonacci | Retracement levels (23.6%, 38.2%, 50%, 61.8%, 78.6%) |

---

## 📊 Signal Engine

The composite score (0–100) is computed as a weighted average of 6 strategies:

```
Composite = Σ(strategy_score × weight) / Σ(weights)

Score ≥ 60  →  BUY  🟢
Score ≤ 40  →  SELL 🔴
Otherwise   →  HOLD 🟡
```

Confidence levels:
- **HIGH**: distance from 50 ≥ 20 points
- **MEDIUM**: distance ≥ 10 points
- **LOW**: distance < 10 points

---

## 🤖 AI Advisor Score Formula

| Horizon | Technical | Fundamental | Sentiment |
|---|---|---|---|
| Short-term | 60% | 15% | 25% |
| Medium-term | 45% | 30% | 25% |
| Long-term | 35% | 40% | 25% |

---

## 🛠️ Troubleshooting

### `pandas-ta` install error
```bash
pip install pandas-ta --no-build-isolation
# or use ta instead:
pip install ta
```

### `yfinance` rate limit (HTTP 429)
Add a small `time.sleep(0.1)` between batch requests, or reduce the screener batch size.

### `lxml` / Wikipedia scraping fails
The screener falls back to a hardcoded 70-ticker universe automatically.

### Streamlit Cloud memory limit
Reduce `max_tickers` in the screener to 20–30 to stay within the 1GB free tier limit.

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Credits

- [yfinance](https://github.com/ranaroussi/yfinance) — Yahoo Finance data
- [Finnhub](https://finnhub.io) — Real-time financial data
- [pandas-ta](https://github.com/twopirllc/pandas-ta) — Technical analysis
- [Plotly](https://plotly.com) — Interactive charts
- [Streamlit](https://streamlit.io) — App framework
- [VADER Sentiment](https://github.com/cjhutto/vaderSentiment) — NLP sentiment

---

> **BloombergFree** is an independent open-source project and has no affiliation with Bloomberg L.P.
> All data is provided "as-is" for informational purposes only.
> This is not financial advice. Always DYOR.
