"""
utils/data_fetcher.py
Centralised data access layer — yfinance (primary) + Finnhub (optional).
All results are cached with TTL=60s to respect rate limits.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time

# ── Helpers ────────────────────────────────────────────────────────────────────

def _finnhub_headers():
    key = st.session_state.get("finnhub_key", "")
    return {"X-Finnhub-Token": key} if key else {}

def _has_finnhub():
    return bool(st.session_state.get("finnhub_key", "").strip())

# ── Price / Quote ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def get_quote(ticker: str) -> dict:
    """Return a lightweight quote dict for a single ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        hist = t.history(period="2d", interval="1m", auto_adjust=True)
        if hist.empty:
            hist = t.history(period="5d", interval="1d", auto_adjust=True)

        price = float(getattr(info, "last_price", 0) or 0)
        prev_close = float(getattr(info, "previous_close", price) or price)
        change = price - prev_close
        pct    = (change / prev_close * 100) if prev_close else 0.0
        volume = int(getattr(info, "three_month_average_volume", 0) or 0)

        return {
            "ticker":     ticker,
            "price":      price,
            "prev_close": prev_close,
            "change":     change,
            "pct":        pct,
            "volume":     volume,
            "high":       float(getattr(info, "year_high", 0) or 0),
            "low":        float(getattr(info, "year_low",  0) or 0),
            "market_cap": float(getattr(info, "market_cap", 0) or 0),
            "timestamp":  datetime.utcnow(),
        }
    except Exception as e:
        return {"ticker": ticker, "price": 0, "change": 0, "pct": 0, "error": str(e)}


@st.cache_data(ttl=60, show_spinner=False)
def get_bulk_quotes(tickers: list) -> pd.DataFrame:
    """Download quotes for multiple tickers in one call."""
    if not tickers:
        return pd.DataFrame()
    try:
        raw = yf.download(tickers, period="2d", interval="1d",
                          auto_adjust=True, group_by="ticker",
                          progress=False, threads=True)
        rows = []
        for t in tickers:
            try:
                if len(tickers) == 1:
                    closes = raw["Close"]
                else:
                    closes = raw["Close"][t]
                closes = closes.dropna()
                if len(closes) < 2:
                    continue
                price = float(closes.iloc[-1])
                prev  = float(closes.iloc[-2])
                chg   = price - prev
                pct   = chg / prev * 100 if prev else 0
                rows.append({"Ticker": t, "Price": price, "Change": chg, "%Chg": pct})
            except Exception:
                continue
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Bulk quote error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_ohlcv(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch OHLCV bars.
    Interval options: 1m 2m 5m 15m 30m 60m 90m 1h 1d 5d 1wk 1mo 3mo
    """
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df.empty:
            return df
        df.index = pd.to_datetime(df.index)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df[["Open","High","Low","Close","Volume"]].dropna()
        return df
    except Exception as e:
        st.error(f"OHLCV error ({ticker}): {e}")
        return pd.DataFrame()


# ── Fundamentals ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_fundamentals(ticker: str) -> dict:
    """Return key fundamental metrics from yfinance."""
    try:
        t = yf.Ticker(ticker)
        i = t.info
        return {
            "name":            i.get("longName", ticker),
            "sector":          i.get("sector", "N/A"),
            "industry":        i.get("industry", "N/A"),
            "country":         i.get("country", "N/A"),
            "pe":              i.get("trailingPE"),
            "fwd_pe":          i.get("forwardPE"),
            "eps":             i.get("trailingEps"),
            "revenue":         i.get("totalRevenue"),
            "net_income":      i.get("netIncomeToCommon"),
            "gross_margin":    i.get("grossMargins"),
            "profit_margin":   i.get("profitMargins"),
            "debt_equity":     i.get("debtToEquity"),
            "current_ratio":   i.get("currentRatio"),
            "roe":             i.get("returnOnEquity"),
            "roa":             i.get("returnOnAssets"),
            "market_cap":      i.get("marketCap"),
            "enterprise_val":  i.get("enterpriseValue"),
            "pb":              i.get("priceToBook"),
            "ps":              i.get("priceToSalesTrailing12Months"),
            "dividend_yield":  i.get("dividendYield"),
            "payout_ratio":    i.get("payoutRatio"),
            "beta":            i.get("beta"),
            "52w_high":        i.get("fiftyTwoWeekHigh"),
            "52w_low":         i.get("fiftyTwoWeekLow"),
            "avg_volume":      i.get("averageVolume"),
            "shares_out":      i.get("sharesOutstanding"),
            "float_shares":    i.get("floatShares"),
            "short_ratio":     i.get("shortRatio"),
            "description":     i.get("longBusinessSummary", ""),
            "website":         i.get("website", ""),
            "employees":       i.get("fullTimeEmployees"),
        }
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def get_financials(ticker: str):
    """Return income statement, balance sheet, cash flow as DataFrames."""
    t = yf.Ticker(ticker)
    try:
        income  = t.quarterly_income_stmt
        balance = t.quarterly_balance_sheet
        cashflow= t.quarterly_cashflow
        return income, balance, cashflow
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def get_earnings(ticker: str) -> pd.DataFrame:
    """Return earnings history."""
    try:
        t = yf.Ticker(ticker)
        cal = t.calendar
        hist = t.earnings_history
        return hist if hist is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# ── News ───────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_news(ticker: str, limit: int = 20) -> list:
    """Fetch news from yfinance, optionally supplement with Finnhub."""
    articles = []

    # yfinance news
    try:
        t = yf.Ticker(ticker)
        raw = t.news or []
        for n in raw[:limit]:
            ct = n.get("content", {})
            articles.append({
                "title":     ct.get("title", n.get("title", "")),
                "summary":   ct.get("summary", ""),
                "url":       ct.get("canonicalUrl", {}).get("url", n.get("link", "")),
                "published": ct.get("pubDate", n.get("providerPublishTime", "")),
                "source":    ct.get("provider", {}).get("displayName", n.get("publisher", "yfinance")),
            })
    except Exception:
        pass

    # Finnhub supplement
    if _has_finnhub() and len(articles) < limit:
        try:
            end   = datetime.now()
            start = end - timedelta(days=7)
            url   = (f"https://finnhub.io/api/v1/company-news?symbol={ticker}"
                     f"&from={start.strftime('%Y-%m-%d')}&to={end.strftime('%Y-%m-%d')}")
            resp  = requests.get(url, headers=_finnhub_headers(), timeout=5)
            if resp.status_code == 200:
                for n in resp.json():
                    articles.append({
                        "title":     n.get("headline", ""),
                        "summary":   n.get("summary", ""),
                        "url":       n.get("url", ""),
                        "published": datetime.fromtimestamp(n.get("datetime", 0)).strftime("%Y-%m-%d %H:%M"),
                        "source":    n.get("source", "Finnhub"),
                    })
        except Exception:
            pass

    return articles[:limit]


# ── Market overview ────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def get_market_overview() -> pd.DataFrame:
    """Fetch major indices and assets."""
    tickers = {
        "S&P 500":   "^GSPC",
        "Nasdaq":    "^IXIC",
        "Dow Jones": "^DJI",
        "VIX":       "^VIX",
        "Bitcoin":   "BTC-USD",
        "Gold":      "GC=F",
        "Oil (WTI)": "CL=F",
        "EUR/USD":   "EURUSD=X",
        "10Y Bond":  "^TNX",
    }
    rows = []
    for name, sym in tickers.items():
        q = get_quote(sym)
        rows.append({
            "Asset":  name,
            "Symbol": sym,
            "Price":  q.get("price", 0),
            "Change": q.get("change", 0),
            "%Chg":   q.get("pct", 0),
        })
    return pd.DataFrame(rows)


# ── Screener ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_sp500_tickers() -> list:
    """Representative S&P 500 universe — no external dependencies."""
    return [
        "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","BRK-B","UNH","JPM",
        "JNJ","V","PG","XOM","MA","HD","CVX","MRK","ABBV","PEP","KO","AVGO",
        "BAC","PFE","LLY","COST","WMT","TMO","ABT","ACN","MCD","CRM","DHR",
        "NKE","TXN","LIN","PM","AMGN","ORCL","IBM","GS","CAT","HON","MS",
        "BA","RTX","GE","SBUX","INTU","SPGI","AXP","BLK","MDLZ","ELV","DE",
        "CI","ISRG","GILD","NOW","REGN","MO","LRCX","ADI","BKNG","CSX",
        "MMC","SYK","VRTX","ZTS","PYPL","PANW","SNPS","CDNS","KLAC","AMD",
        "NFLX","INTC","QCOM","MU","AMAT","ADBE","COP","SLB","EOG","PSX",
    ]


@st.cache_data(ttl=300, show_spinner=False)
def get_screener_data(tickers: list) -> pd.DataFrame:
    """Fetch key screener metrics for a list of tickers."""
    rows = []
    for ticker in tickers:
        try:
            t   = yf.Ticker(ticker)
            i   = t.info
            rows.append({
                "Ticker":         ticker,
                "Name":           i.get("shortName", ticker),
                "Sector":         i.get("sector", "N/A"),
                "Price":          i.get("currentPrice") or i.get("regularMarketPrice", 0),
                "Mkt Cap ($B)":   round((i.get("marketCap") or 0) / 1e9, 2),
                "PE":             i.get("trailingPE"),
                "Fwd PE":         i.get("forwardPE"),
                "EPS":            i.get("trailingEps"),
                "Div Yield%":     round((i.get("dividendYield") or 0) * 100, 2),
                "Beta":           i.get("beta"),
                "Volume (M)":     round((i.get("averageVolume") or 0) / 1e6, 2),
                "52W High":       i.get("fiftyTwoWeekHigh"),
                "52W Low":        i.get("fiftyTwoWeekLow"),
            })
            time.sleep(0.05)  # gentle rate limit
        except Exception:
            continue
    return pd.DataFrame(rows)


# ── Economic calendar ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_economic_calendar() -> pd.DataFrame:
    """Fetch economic calendar from Finnhub if key available, else mock data."""
    if _has_finnhub():
        try:
            end   = datetime.now() + timedelta(days=14)
            start = datetime.now() - timedelta(days=3)
            url   = (f"https://finnhub.io/api/v1/calendar/economic"
                     f"?from={start.strftime('%Y-%m-%d')}&to={end.strftime('%Y-%m-%d')}")
            resp  = requests.get(url, headers=_finnhub_headers(), timeout=8)
            if resp.status_code == 200:
                events = resp.json().get("economicCalendar", [])
                df = pd.DataFrame(events)
                if not df.empty:
                    df = df[["time","event","country","impact","actual","estimate","prev"]].rename(
                        columns={"time":"Date","event":"Event","country":"Country",
                                 "impact":"Impact","actual":"Actual","estimate":"Estimate","prev":"Previous"})
                    return df.sort_values("Date")
        except Exception:
            pass

    # Fallback: representative static calendar
    today = datetime.now()
    events = [
        (today + timedelta(days=d), ev, c, imp)
        for d, ev, c, imp in [
            (-1,"GDP Growth Rate Q4","US","HIGH"),
            (0, "Fed Interest Rate Decision","US","HIGH"),
            (1, "CPI (YoY)","US","HIGH"),
            (2, "Non-Farm Payrolls","US","HIGH"),
            (2, "Unemployment Rate","US","MEDIUM"),
            (3, "PPI (MoM)","US","MEDIUM"),
            (4, "Retail Sales (MoM)","US","MEDIUM"),
            (5, "ECB Interest Rate Decision","EU","HIGH"),
            (6, "Consumer Confidence","US","LOW"),
            (7, "PCE Price Index","US","HIGH"),
            (8, "Industrial Production","US","MEDIUM"),
            (9, "Trade Balance","US","MEDIUM"),
            (10,"FOMC Minutes","US","HIGH"),
            (11,"Jobless Claims","US","MEDIUM"),
            (12,"Michigan Consumer Sentiment","US","MEDIUM"),
        ]
    ]
    rows = [{"Date":d.strftime("%Y-%m-%d"), "Event":e, "Country":c,
             "Impact":i, "Actual":"--", "Estimate":"--", "Previous":"--"}
            for d,e,c,i in events]
    return pd.DataFrame(rows)


# ── Top movers ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def get_top_movers(n: int = 5):
    """Return top gainers and losers from a representative universe."""
    universe = [
        "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","NFLX","AMD","INTC",
        "BA","GS","JPM","BAC","WFC","XOM","CVX","PFE","MRK","JNJ",
        "DIS","UBER","LYFT","SNAP","TWTR","RBLX","COIN","SHOP","SQ","PYPL",
    ]
    df = get_bulk_quotes(universe)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    gainers = df.nlargest(n, "%Chg")
    losers  = df.nsmallest(n, "%Chg")
    return gainers, losers
