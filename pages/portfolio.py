"""pages/portfolio.py — Portfolio Tracker with P&L, VaR, Benchmark"""

import streamlit as st
import pandas as pd
import numpy as np
import io
from utils.data_fetcher import get_quote, get_bulk_quotes, get_ohlcv
from utils.charts import portfolio_pie


def render():
    st.markdown("## 💼 Portfolio Tracker")

    # ── Add position ───────────────────────────────────────────────────────────
    with st.expander("➕ Add Position", expanded=len(st.session_state.portfolio) == 0):
        c1, c2, c3, c4 = st.columns(4)
        with c1: pticker = st.text_input("Ticker", key="pt_ticker")
        with c2: pshares = st.number_input("Shares", 0.01, 1e7, 10.0, 1.0, key="pt_shares")
        with c3: pavg    = st.number_input("Avg Cost ($)", 0.01, 1e6, 100.0, 0.01, key="pt_cost")
        with c4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Add ➕") and pticker:
                st.session_state.portfolio.append({
                    "ticker": pticker.upper().strip(),
                    "shares": pshares,
                    "avg_cost": pavg,
                })
                st.success(f"Added {pticker.upper()}")
                st.rerun()

    if not st.session_state.portfolio:
        st.info("No positions yet. Add your first position above.")
        return

    # ── Fetch live prices ──────────────────────────────────────────────────────
    tickers_in = [p["ticker"] for p in st.session_state.portfolio]
    with st.spinner("Fetching live prices…"):
        quotes = get_bulk_quotes(tickers_in)

    price_map = {}
    if not quotes.empty:
        price_map = dict(zip(quotes["Ticker"], quotes["Price"]))

    # ── Build portfolio DataFrame ─────────────────────────────────────────────
    rows = []
    for pos in st.session_state.portfolio:
        t     = pos["ticker"]
        price = price_map.get(t, pos["avg_cost"])
        shares= pos["shares"]
        cost  = pos["avg_cost"]
        mkt_val = price * shares
        cost_tot= cost  * shares
        pnl     = mkt_val - cost_tot
        pnl_pct = pnl / cost_tot * 100 if cost_tot > 0 else 0
        rows.append({
            "Ticker":   t,
            "Shares":   shares,
            "Avg Cost": cost,
            "Price":    price,
            "Mkt Value":mkt_val,
            "P&L ($)":  pnl,
            "P&L (%)":  pnl_pct,
        })

    df = pd.DataFrame(rows)
    total_mkt   = df["Mkt Value"].sum()
    total_cost  = (df["Avg Cost"] * df["Shares"]).sum()
    total_pnl   = df["P&L ($)"].sum()
    total_pnl_p = total_pnl / total_cost * 100 if total_cost > 0 else 0

    # ── KPI row ────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Portfolio Value", f"${total_mkt:,.2f}")
    k2.metric("Total P&L ($)", f"${total_pnl:+,.2f}", delta=f"{total_pnl_p:+.2f}%")
    k3.metric("Cost Basis", f"${total_cost:,.2f}")
    k4.metric("Positions", len(df))

    st.divider()

    # ── Table ──────────────────────────────────────────────────────────────────
    st.markdown("### 📊 Positions")

    def color_pnl(val):
        if isinstance(val, float):
            return f"color: {'#00d084' if val >= 0 else '#ff3b5c'}; font-weight: 600"
        return ""

    delete_col, table_col = st.columns([1, 8])
    with table_col:
        styled = df.style \
            .format({
                "Shares": "{:.4f}", "Avg Cost": "${:.4f}", "Price": "${:.4f}",
                "Mkt Value": "${:,.2f}", "P&L ($)": "${:+,.2f}", "P&L (%)": "{:+.2f}%",
            }) \
            .applymap(color_pnl, subset=["P&L ($)", "P&L (%)"]) \
            .set_properties(**{"font-family": "IBM Plex Mono", "font-size": "13px"})
        st.dataframe(styled, use_container_width=True, hide_index=True)

    # Remove position
    rm = st.selectbox("Remove position", [""] + tickers_in)
    if st.button("➖ Remove Position") and rm:
        st.session_state.portfolio = [p for p in st.session_state.portfolio if p["ticker"] != rm]
        st.rerun()

    st.divider()

    # ── Allocation pie ────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🥧 Allocation")
        fig_pie = portfolio_pie(df["Ticker"].tolist(), df["Mkt Value"].tolist())
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        # ── P&L bar ────────────────────────────────────────────────────────────
        st.markdown("### 📊 P&L by Position")
        import plotly.graph_objects as go
        colors = ["#00d084" if v >= 0 else "#ff3b5c" for v in df["P&L ($)"]]
        fig_pnl = go.Figure(go.Bar(
            x=df["Ticker"], y=df["P&L ($)"],
            marker_color=colors,
            text=[f"${v:+,.0f}" for v in df["P&L ($)"]],
            textposition="outside",
            textfont=dict(family="IBM Plex Mono", color="#e8e8f0", size=11),
        ))
        fig_pnl.update_layout(
            paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a0f",
            font=dict(family="IBM Plex Mono", color="#e8e8f0"),
            height=320, margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(gridcolor="#1e1e32"), yaxis=dict(gridcolor="#1e1e32"),
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

    st.divider()

    # ── Risk Metrics — VaR ────────────────────────────────────────────────────
    st.markdown("### ⚠️ Risk Analysis")
    with st.spinner("Computing VaR…"):
        returns_list = []
        weights_list = []
        for pos in st.session_state.portfolio:
            hist = get_ohlcv(pos["ticker"], period="1y", interval="1d")
            if hist is not None and not hist.empty and len(hist) > 20:
                r = hist["Close"].pct_change().dropna()
                returns_list.append(r.values)
                weights_list.append(pos["shares"] * pos["avg_cost"])

        if returns_list:
            min_len = min(len(r) for r in returns_list)
            returns_mat = np.array([r[-min_len:] for r in returns_list])
            weights_arr = np.array(weights_list) / sum(weights_list)
            port_returns = (returns_mat.T @ weights_arr)

            var_95 = np.percentile(port_returns, 5)
            var_99 = np.percentile(port_returns, 1)
            cvar_95= port_returns[port_returns <= var_95].mean() if any(port_returns <= var_95) else var_95
            ann_vol = port_returns.std() * np.sqrt(252) * 100

            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("VaR 95% (1-day)", f"${total_mkt * abs(var_95):,.0f}",
                       delta=f"{var_95*100:.2f}%", delta_color="inverse")
            rc2.metric("VaR 99% (1-day)", f"${total_mkt * abs(var_99):,.0f}",
                       delta=f"{var_99*100:.2f}%", delta_color="inverse")
            rc3.metric("CVaR 95%", f"${total_mkt * abs(cvar_95):,.0f}",
                       delta=f"{cvar_95*100:.2f}%", delta_color="inverse")
            rc4.metric("Ann. Volatility", f"{ann_vol:.1f}%")

            # Returns distribution
            import plotly.graph_objects as go
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=port_returns * 100, nbinsx=50,
                marker_color="#0ea5e9", opacity=0.7, name="Daily Returns %"
            ))
            fig_hist.add_vline(x=var_95*100, line_dash="dash", line_color="#ff3b5c",
                                annotation_text=f"VaR 95%: {var_95*100:.2f}%")
            fig_hist.add_vline(x=var_99*100, line_dash="dash", line_color="#ff0000",
                                annotation_text=f"VaR 99%: {var_99*100:.2f}%")
            fig_hist.update_layout(
                paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a0f",
                font=dict(family="IBM Plex Mono", color="#e8e8f0"),
                height=250, margin=dict(l=40, r=20, t=30, b=20),
                title=dict(text="Portfolio Returns Distribution", font=dict(color="#ffd700")),
                xaxis=dict(gridcolor="#1e1e32", title="Daily Return %"),
                yaxis=dict(gridcolor="#1e1e32"),
            )
            st.plotly_chart(fig_hist, use_container_width=True)

    # ── Benchmark comparison ──────────────────────────────────────────────────
    st.markdown("### 📈 Performance vs Benchmark")
    benchmark = st.selectbox("Benchmark", ["^GSPC (S&P500)", "^IXIC (Nasdaq)", "^DJI (Dow)"])
    bench_sym = benchmark.split(" ")[0]
    with st.spinner("Loading benchmark…"):
        bench_df = get_ohlcv(bench_sym, period="1y", interval="1d")
    if bench_df is not None and not bench_df.empty:
        bench_ret = (bench_df["Close"] / bench_df["Close"].iloc[0] - 1) * 100
        # Use first ticker as proxy
        proxy_df = get_ohlcv(tickers_in[0], period="1y", interval="1d") if tickers_in else None
        import plotly.graph_objects as go
        fig_b = go.Figure()
        fig_b.add_trace(go.Scatter(x=bench_df.index, y=bench_ret,
                                    name=bench_sym, line=dict(color="#6b6b8a", width=1.5)))
        if proxy_df is not None and not proxy_df.empty:
            port_proxy = (proxy_df["Close"] / proxy_df["Close"].iloc[0] - 1) * 100
            fig_b.add_trace(go.Scatter(x=proxy_df.index, y=port_proxy,
                                        name=tickers_in[0], line=dict(color="#0ea5e9", width=2)))
        fig_b.add_hline(y=0, line_dash="dash", line_color="#6b6b8a", opacity=0.3)
        fig_b.update_layout(
            paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a0f",
            font=dict(family="IBM Plex Mono", color="#e8e8f0"),
            height=280, margin=dict(l=40, r=20, t=30, b=20),
            title=dict(text="1-Year Return %", font=dict(color="#ffd700")),
            xaxis=dict(gridcolor="#1e1e32"), yaxis=dict(gridcolor="#1e1e32"),
        )
        st.plotly_chart(fig_b, use_container_width=True)

    # ── Export ────────────────────────────────────────────────────────────────
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    st.download_button("⬇️ Export Portfolio CSV", buf.getvalue(), "portfolio.csv", "text/csv")
