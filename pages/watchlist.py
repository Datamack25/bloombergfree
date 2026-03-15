"""pages/watchlist.py — Live Watchlist"""

import streamlit as st
import pandas as pd
import time
import io
from utils.data_fetcher import get_bulk_quotes


def render():
    st.markdown("## ⭐ Watchlist")

    # ── Controls ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    with c1:
        new_ticker = st.text_input("Add Ticker", placeholder="e.g. AMZN, ETH-USD, EURUSD=X")
    with c2:
        if st.button("➕ Add") and new_ticker:
            sym = new_ticker.upper().strip()
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                st.success(f"Added {sym}")
                st.rerun()
    with c3:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
    with c4:
        remove_ticker = st.selectbox("Remove", [""] + st.session_state.watchlist, key="rm_ticker")
        if st.button("➖ Remove") and remove_ticker:
            st.session_state.watchlist.remove(remove_ticker)
            st.rerun()

    # ── Import / Export CSV ────────────────────────────────────────────────────
    with st.expander("📁 Import / Export CSV"):
        ec1, ec2 = st.columns(2)
        with ec1:
            uploaded = st.file_uploader("Import watchlist CSV", type="csv")
            if uploaded:
                df_import = pd.read_csv(uploaded)
                if "Ticker" in df_import.columns:
                    imported = [t.upper() for t in df_import["Ticker"].tolist()]
                    added = [t for t in imported if t not in st.session_state.watchlist]
                    st.session_state.watchlist.extend(added)
                    st.success(f"Imported {len(added)} tickers")
                    st.rerun()
        with ec2:
            if st.session_state.watchlist:
                csv_buf = io.StringIO()
                pd.DataFrame({"Ticker": st.session_state.watchlist}).to_csv(csv_buf, index=False)
                st.download_button("⬇️ Export CSV", csv_buf.getvalue(),
                                   "watchlist.csv", "text/csv")

    # ── Live Quotes ────────────────────────────────────────────────────────────
    if not st.session_state.watchlist:
        st.info("Your watchlist is empty. Add tickers above.")
        return

    st.caption(f"🕐 {pd.Timestamp.now().strftime('%H:%M:%S UTC')} · {len(st.session_state.watchlist)} tickers")

    with st.spinner("Fetching quotes…"):
        df = get_bulk_quotes(st.session_state.watchlist)

    if df.empty:
        st.warning("Could not fetch quotes. Check ticker symbols.")
        return

    # Color formatting
    def color_pct(val):
        if isinstance(val, float):
            return f"color: {'#00d084' if val >= 0 else '#ff3b5c'}; font-weight: 600"
        return ""

    st.dataframe(
        df.style
            .format({"Price": "${:,.4f}", "Change": "{:+.4f}", "%Chg": "{:+.2f}%"})
            .applymap(color_pct, subset=["%Chg", "Change"])
            .set_properties(**{"font-family": "IBM Plex Mono", "font-size": "13px"}),
        use_container_width=True,
        hide_index=True,
        height=min(600, 50 + len(df) * 38),
    )

    # ── Spark view ─────────────────────────────────────────────────────────────
    st.markdown("### 📈 Quick Spark Charts")
    tickers_to_show = st.session_state.watchlist[:8]  # limit for perf
    from utils.data_fetcher import get_ohlcv
    import plotly.graph_objects as go

    cols = st.columns(4)
    for i, ticker in enumerate(tickers_to_show):
        with cols[i % 4]:
            spark = get_ohlcv(ticker, period="1mo", interval="1d")
            if spark.empty:
                continue
            pct_total = (spark["Close"].iloc[-1] - spark["Close"].iloc[0]) / spark["Close"].iloc[0] * 100
            color = "#00d084" if pct_total >= 0 else "#ff3b5c"
            fig = go.Figure(go.Scatter(
                x=spark.index, y=spark["Close"],
                fill="tozeroy",
                line=dict(color=color, width=1.5),
                fillcolor=f"{'rgba(0,208,132,0.1)' if pct_total >= 0 else 'rgba(255,59,92,0.1)'}",
            ))
            fig.update_layout(
                paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a0f",
                margin=dict(l=0, r=0, t=30, b=0),
                height=120,
                title=dict(text=f"<b>{ticker}</b> {pct_total:+.1f}%",
                           font=dict(color=color, size=12, family="IBM Plex Mono")),
                showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Alerts ─────────────────────────────────────────────────────────────────
    st.markdown("### 🔔 Price Alerts")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        alert_ticker = st.selectbox("Ticker", st.session_state.watchlist, key="alert_ticker_sel")
    with ac2:
        alert_price  = st.number_input("Price threshold", min_value=0.0, step=0.01)
    with ac3:
        alert_dir    = st.selectbox("Direction", ["Above", "Below"])
    if st.button("Add Alert ➕"):
        alert_str = f"Alert: {alert_ticker} {alert_dir} ${alert_price:.2f}"
        st.session_state.alerts.append(alert_str)
        st.success(f"Alert set: {alert_str}")

    if st.session_state.alerts:
        st.markdown("**Active alerts:**")
        for a in st.session_state.alerts:
            sc1, sc2 = st.columns([5, 1])
            with sc1: st.warning(a)
            with sc2:
                if st.button("❌", key=f"del_{a}"):
                    st.session_state.alerts.remove(a)
                    st.rerun()
