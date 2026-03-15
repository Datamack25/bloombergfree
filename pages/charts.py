"""pages/charts.py — Interactive Chart Analysis"""

import streamlit as st
import pandas as pd
from utils.data_fetcher import get_ohlcv
from utils.indicators import enrich, fibonacci_levels
from utils.charts import candlestick_chart, line_chart


INTERVAL_MAP = {
    "1 min": ("1d", "1m"),
    "5 min": ("5d", "5m"),
    "15 min": ("1mo", "15m"),
    "30 min": ("1mo", "30m"),
    "1 hour": ("3mo", "60m"),
    "1 day": ("1y", "1d"),
    "1 week": ("5y", "1wk"),
}


def render():
    st.markdown("## 📊 Chart Analysis")

    # ── Controls ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        ticker = st.text_input("Ticker", value=st.session_state.get("active_ticker", "AAPL"))
        if ticker:
            st.session_state.active_ticker = ticker.upper().strip()
    with c2:
        timeframe = st.selectbox("Timeframe", list(INTERVAL_MAP.keys()), index=5)
    with c3:
        chart_type = st.selectbox("Chart", ["Candles", "Line", "Area"])

    period, interval = INTERVAL_MAP[timeframe]

    # ── Indicator toggles ──────────────────────────────────────────────────────
    with st.expander("⚙️ Indicators", expanded=True):
        cols = st.columns(6)
        show_sma  = cols[0].checkbox("SMA", True)
        show_ema  = cols[1].checkbox("EMA", True)
        show_bb   = cols[2].checkbox("Bollinger", True)
        show_ichi = cols[3].checkbox("Ichimoku", False)
        show_vwap = cols[4].checkbox("VWAP", False)
        show_fib  = cols[5].checkbox("Fibonacci", False)

        cols2 = st.columns(6)
        show_rsi  = cols2[0].checkbox("RSI", True)
        show_macd = cols2[1].checkbox("MACD", True)
        show_stoch= cols2[2].checkbox("Stochastic", False)
        show_atr  = cols2[3].checkbox("ATR", False)
        show_obv  = cols2[4].checkbox("OBV", False)

        sma_periods = st.multiselect("SMA periods", [9,20,50,100,200], default=[20,50,200])
        ema_periods = st.multiselect("EMA periods", [9,20,50,100,200], default=[20,50])

    # ── Fetch & enrich ─────────────────────────────────────────────────────────
    with st.spinner(f"Loading {ticker} [{timeframe}]…"):
        df = get_ohlcv(ticker, period=period, interval=interval)

    if df is None or df.empty:
        st.error(f"No data for {ticker}. Check the ticker symbol.")
        return

    df = enrich(df)

    # Build overlay list
    overlays = []
    if show_sma:
        overlays += [f"SMA_{p}" for p in sma_periods if f"SMA_{p}" in df.columns]
    if show_ema:
        overlays += [f"EMA_{p}" for p in ema_periods if f"EMA_{p}" in df.columns]
    if show_bb:
        overlays += [c for c in ["BB_upper","BB_mid","BB_lower"] if c in df.columns]
    if show_ichi:
        overlays += [c for c in ["ICH_tenkan","ICH_kijun","ICH_spana","ICH_spanb"] if c in df.columns]
    if show_vwap and "VWAP" in df.columns:
        overlays.append("VWAP")

    # Override RSI/MACD presence in chart based on toggles
    df_plot = df.copy()
    if not show_rsi   and "RSI"  in df_plot.columns: df_plot.drop(columns=["RSI"], inplace=True)
    if not show_macd  and "MACD" in df_plot.columns: df_plot.drop(columns=["MACD","MACD_signal","MACD_hist"], inplace=True)

    # ── Main chart ─────────────────────────────────────────────────────────────
    fig = candlestick_chart(df_plot, ticker, overlays=overlays)
    st.plotly_chart(fig, use_container_width=True)

    # ── Fibonacci ─────────────────────────────────────────────────────────────
    if show_fib and len(df) > 20:
        st.markdown("### 📐 Fibonacci Retracement Levels")
        fibs = fibonacci_levels(df)
        price = df["Close"].iloc[-1]
        fc1, fc2 = st.columns(2)
        with fc1:
            for lvl, val in fibs.items():
                color = "#00d084" if price > val else "#ff3b5c"
                diff  = (price - val) / val * 100
                st.markdown(
                    f'<div class="bf-card">'
                    f'<span style="color:#6b6b8a;font-family:\'IBM Plex Mono\';font-size:0.8rem">{lvl}</span> '
                    f'<span style="color:{color};font-family:\'IBM Plex Mono\';font-weight:700">${val:,.2f}</span> '
                    f'<span style="color:#6b6b8a;font-size:0.75rem">({diff:+.1f}% from price)</span>'
                    f'</div>', unsafe_allow_html=True)

    # ── Stochastic sub-chart ──────────────────────────────────────────────────
    if show_stoch and "STOCH_K" in df.columns:
        import plotly.graph_objects as go
        fig_s = go.Figure()
        fig_s.add_trace(go.Scatter(x=df.index, y=df["STOCH_K"], name="%K",
                                    line=dict(color="#0ea5e9", width=1.5)))
        fig_s.add_trace(go.Scatter(x=df.index, y=df["STOCH_D"], name="%D",
                                    line=dict(color="#f59e0b", width=1.2, dash="dash")))
        fig_s.add_hline(y=80, line_dash="dot", line_color="#ff3b5c", opacity=0.5)
        fig_s.add_hline(y=20, line_dash="dot", line_color="#00d084", opacity=0.5)
        fig_s.update_layout(paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a0f",
                             font=dict(family="IBM Plex Mono", color="#e8e8f0"),
                             height=200, margin=dict(l=40, r=20, t=30, b=10),
                             title=dict(text="Stochastic", font=dict(color="#ffd700")),
                             xaxis=dict(gridcolor="#1e1e32"), yaxis=dict(gridcolor="#1e1e32"))
        st.plotly_chart(fig_s, use_container_width=True)

    # ── ATR & OBV ────────────────────────────────────────────────────────────
    if show_atr and "ATR" in df.columns:
        st.plotly_chart(line_chart(df, "ATR", "Average True Range (ATR)", "#a78bfa"),
                        use_container_width=True)
    if show_obv and "OBV" in df.columns:
        st.plotly_chart(line_chart(df, "OBV", "On-Balance Volume (OBV)", "#0ea5e9"),
                        use_container_width=True)

    # ── Stats panel ────────────────────────────────────────────────────────────
    st.markdown("### 📋 Price Statistics")
    latest = df["Close"].iloc[-1]
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Last Close", f"${latest:,.4f}")
    s2.metric("Period High", f"${df['High'].max():,.4f}")
    s3.metric("Period Low",  f"${df['Low'].min():,.4f}")
    s4.metric("Avg Volume",  f"{df['Volume'].mean():,.0f}" if "Volume" in df.columns else "N/A")
    chg = (latest - df["Close"].iloc[0]) / df["Close"].iloc[0] * 100
    s5.metric("Period Return", f"{chg:+.2f}%", delta=f"{chg:+.2f}%")

    # ── Export ────────────────────────────────────────────────────────────────
    import io
    buf = io.BytesIO()
    df.to_csv(buf, index=True)
    st.download_button("⬇️ Export OHLCV + Indicators CSV", buf.getvalue(),
                       f"{ticker}_{interval}_data.csv", "text/csv")
