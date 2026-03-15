"""pages/signals_page.py — BUY / SELL / HOLD Signal Engine"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.data_fetcher import get_ohlcv
from utils.signals import compute_composite_signal, STRATEGY_WEIGHTS
from utils.charts import signal_gauge


def render():
    st.markdown("## ⚡ Technical Signals — BUY / SELL / HOLD")

    # ── Controls ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        ticker = st.text_input("Ticker", value=st.session_state.get("active_ticker", "AAPL"))
    with c2:
        timeframe = st.selectbox("Analysis timeframe",
                                 ["1 day (recommended)","1 hour","15 min","1 week"])
    with c3:
        if st.button("🔄 Analyse"):
            st.cache_data.clear()

    tf_map = {"1 day (recommended)": ("6mo","1d"),
              "1 hour": ("3mo","60m"),
              "15 min": ("1mo","15m"),
              "1 week": ("2y","1wk")}
    period, interval = tf_map.get(timeframe, ("6mo","1d"))

    # ── Weight customisation ───────────────────────────────────────────────────
    with st.expander("⚙️ Customise strategy weights"):
        st.caption("Adjust how much each strategy influences the composite score.")
        weights = {}
        wc = st.columns(3)
        items = list(STRATEGY_WEIGHTS.items())
        for i, (name, default) in enumerate(items):
            with wc[i % 3]:
                weights[name] = st.slider(name, 0.0, 5.0, float(default), 0.1)

    # ── Fetch & compute ────────────────────────────────────────────────────────
    if not ticker:
        st.info("Enter a ticker to analyse.")
        return

    ticker = ticker.upper().strip()
    st.session_state.active_ticker = ticker

    with st.spinner(f"Running signal engine for {ticker}…"):
        df = get_ohlcv(ticker, period=period, interval=interval)

    if df is None or df.empty:
        st.error(f"No data for {ticker}")
        return

    result = compute_composite_signal(df, weights=weights)

    # ── Main Signal Display ───────────────────────────────────────────────────
    st.markdown(f"### Signal Analysis · {ticker}")
    g1, g2, g3 = st.columns([2, 1, 2])

    with g1:
        fig = signal_gauge(result["score"], result["label"])
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        st.markdown(f"""
        <div class="{result['css_class']}" style="margin-top:40px">
            {result['label']}
        </div>
        <div style="text-align:center;margin-top:12px">
            <div style="color:#6b6b8a;font-size:0.75rem;font-family:'IBM Plex Mono'">CONFIDENCE</div>
            <div style="color:#ffd700;font-size:1.2rem;font-weight:700;font-family:'IBM Plex Mono'">{result['confidence']}</div>
        </div>
        <div style="text-align:center;margin-top:12px">
            <div style="color:#6b6b8a;font-size:0.75rem;font-family:'IBM Plex Mono'">SCORE</div>
            <div style="color:#e8e8f0;font-size:1.4rem;font-weight:700;font-family:'IBM Plex Mono'">{result['score']}/100</div>
        </div>
        """, unsafe_allow_html=True)

    with g3:
        # Score bar for each strategy
        st.markdown("**Strategy breakdown:**")
        for s in result["strategies"]:
            score = s["score"]
            name  = s["name"]
            color = "#00d084" if score >= 60 else ("#ff3b5c" if score <= 40 else "#f59e0b")
            lbl   = "BUY" if score >= 60 else ("SELL" if score <= 40 else "HOLD")
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin:4px 0">
                <div style="width:90px;font-family:'IBM Plex Mono';font-size:0.7rem;color:#6b6b8a">{name}</div>
                <div style="flex:1;background:#1e1e32;border-radius:3px;height:12px">
                    <div style="width:{score}%;background:{color};height:12px;border-radius:3px"></div>
                </div>
                <div style="width:40px;font-family:'IBM Plex Mono';font-size:0.75rem;color:{color};font-weight:700">{lbl}</div>
                <div style="width:32px;font-family:'IBM Plex Mono';font-size:0.7rem;color:#6b6b8a">{score:.0f}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── Detailed Reasons ──────────────────────────────────────────────────────
    st.markdown("### 📋 Signal Explanations")
    tabs = st.tabs([s["name"] for s in result["strategies"]])
    for i, s in enumerate(result["strategies"]):
        with tabs[i]:
            sc = s["score"]
            color = "#00d084" if sc >= 60 else ("#ff3b5c" if sc <= 40 else "#f59e0b")
            lbl   = "BUY" if sc >= 60 else ("SELL" if sc <= 40 else "HOLD")
            st.markdown(f"**Score: <span style='color:{color}'>{sc:.1f}/100 — {lbl}</span>**",
                        unsafe_allow_html=True)
            for reason in s.get("signals", []):
                icon = "📈" if "BUY" in reason.upper() or "bullish" in reason.lower() else \
                       ("📉" if "SELL" in reason.upper() or "bearish" in reason.lower() else "➡️")
                st.markdown(f"{icon} {reason}")

    st.divider()

    # ── Multi-ticker quick scan ───────────────────────────────────────────────
    st.markdown("### 🔍 Quick Signal Scan — Watchlist")
    if st.button("▶️ Scan Watchlist"):
        scan_tickers = st.session_state.watchlist[:10]
        results = []
        prog = st.progress(0)
        for i, t in enumerate(scan_tickers):
            prog.progress((i + 1) / len(scan_tickers))
            df_t = get_ohlcv(t, period="3mo", interval="1d")
            if df_t is not None and not df_t.empty:
                r = compute_composite_signal(df_t)
                results.append({
                    "Ticker": t,
                    "Signal": r["label"],
                    "Score":  r["score"],
                    "Confidence": r["confidence"],
                })
        prog.empty()
        if results:
            rdf = pd.DataFrame(results).sort_values("Score", ascending=False)
            def color_signal(val):
                if val == "BUY":  return "color: #00d084; font-weight: bold"
                if val == "SELL": return "color: #ff3b5c; font-weight: bold"
                return "color: #f59e0b; font-weight: bold"
            st.dataframe(rdf.style.applymap(color_signal, subset=["Signal"]),
                         use_container_width=True, hide_index=True)
