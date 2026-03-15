"""pages/fundamentals.py — Fundamental Analysis"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.data_fetcher import get_fundamentals, get_financials, get_earnings


def _fmt(val, fmt="{:,.2f}", prefix="", suffix="", billions=False):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    if billions and isinstance(val, (int, float)):
        return f"{prefix}{val/1e9:,.2f}B{suffix}"
    return f"{prefix}{fmt.format(val)}{suffix}"


def _metric_card(title, value, color="#e8e8f0"):
    st.markdown(
        f'<div class="bf-card"><div style="color:#6b6b8a;font-size:0.7rem;font-family:\'IBM Plex Mono\';'
        f'letter-spacing:1px;text-transform:uppercase">{title}</div>'
        f'<div style="color:{color};font-family:\'IBM Plex Mono\';font-size:1.1rem;font-weight:700;margin-top:4px">'
        f'{value}</div></div>',
        unsafe_allow_html=True,
    )


def render():
    st.markdown("## 🏢 Fundamental Analysis")

    c1, c2 = st.columns([3, 1])
    with c1:
        ticker = st.text_input("Ticker", value=st.session_state.get("active_ticker", "AAPL"))
    with c2:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()

    if not ticker:
        return
    ticker = ticker.upper().strip()
    st.session_state.active_ticker = ticker

    with st.spinner(f"Loading fundamentals for {ticker}…"):
        info = get_fundamentals(ticker)

    if "error" in info:
        st.error(f"Error: {info['error']}")
        return

    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown(f"### {info.get('name', ticker)}")
    h1, h2, h3 = st.columns(3)
    h1.markdown(f"**Sector:** {info.get('sector','N/A')} · **Industry:** {info.get('industry','N/A')}")
    h2.markdown(f"**Country:** {info.get('country','N/A')} · **Employees:** {info.get('employees','N/A'):,}" if isinstance(info.get('employees'), int) else f"**Country:** {info.get('country','N/A')}")
    h3.markdown(f"[🌐 Website]({info.get('website','#')})" if info.get('website') else "")

    st.divider()

    # ── Valuation ─────────────────────────────────────────────────────────────
    st.markdown("#### 💰 Valuation")
    vc = st.columns(5)
    with vc[0]: _metric_card("P/E Ratio",  _fmt(info.get("pe"),    "{:.2f}x"))
    with vc[1]: _metric_card("Fwd P/E",    _fmt(info.get("fwd_pe"),"{:.2f}x"))
    with vc[2]: _metric_card("P/B Ratio",  _fmt(info.get("pb"),    "{:.2f}x"))
    with vc[3]: _metric_card("P/S Ratio",  _fmt(info.get("ps"),    "{:.2f}x"))
    with vc[4]: _metric_card("EV",         _fmt(info.get("enterprise_val"), billions=True, prefix="$"))

    st.markdown("#### 📊 Per Share")
    pc = st.columns(4)
    with pc[0]: _metric_card("EPS (TTM)",  _fmt(info.get("eps"), prefix="$"))
    with pc[1]: _metric_card("Div Yield",  _fmt((info.get("dividend_yield") or 0)*100, "{:.2f}%"))
    with pc[2]: _metric_card("Payout",     _fmt((info.get("payout_ratio") or 0)*100, "{:.1f}%"))
    with pc[3]: _metric_card("Beta",       _fmt(info.get("beta"), "{:.2f}"))

    st.markdown("#### 📈 Financials (TTM)")
    fc = st.columns(5)
    with fc[0]: _metric_card("Revenue",      _fmt(info.get("revenue"),   billions=True, prefix="$"))
    with fc[1]: _metric_card("Net Income",   _fmt(info.get("net_income"),billions=True, prefix="$"))
    with fc[2]: _metric_card("Gross Margin", _fmt((info.get("gross_margin") or 0)*100, "{:.1f}%"))
    with fc[3]: _metric_card("Profit Margin",_fmt((info.get("profit_margin") or 0)*100, "{:.1f}%"))
    with fc[4]: _metric_card("Mkt Cap",      _fmt(info.get("market_cap"), billions=True, prefix="$"))

    st.markdown("#### 🔩 Balance Sheet")
    bc = st.columns(4)
    with bc[0]: _metric_card("D/E Ratio",     _fmt(info.get("debt_equity"), "{:.2f}x"))
    with bc[1]: _metric_card("Current Ratio", _fmt(info.get("current_ratio"), "{:.2f}x"))
    with bc[2]: _metric_card("ROE",           _fmt((info.get("roe") or 0)*100, "{:.1f}%"))
    with bc[3]: _metric_card("ROA",           _fmt((info.get("roa") or 0)*100, "{:.1f}%"))

    st.markdown("#### 📅 Price")
    prc = st.columns(4)
    with prc[0]: _metric_card("52W High", _fmt(info.get("52w_high"), prefix="$"))
    with prc[1]: _metric_card("52W Low",  _fmt(info.get("52w_low"),  prefix="$"))
    with prc[2]: _metric_card("Short Ratio", _fmt(info.get("short_ratio"), "{:.2f}"))
    with prc[3]: _metric_card("Avg Volume", f"{(info.get('avg_volume') or 0)/1e6:.1f}M")

    st.divider()

    # ── Quarterly Financials ──────────────────────────────────────────────────
    st.markdown("### 📋 Quarterly Financials")
    with st.spinner("Loading financials…"):
        income, balance, cashflow = get_financials(ticker)

    tabs = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
    for tab, df_fin, name in zip(tabs, [income, balance, cashflow],
                                  ["Income", "Balance", "Cash Flow"]):
        with tab:
            if df_fin is not None and not df_fin.empty:
                # Format large numbers
                def fmt_billions(x):
                    try:
                        v = float(x)
                        if abs(v) >= 1e9: return f"${v/1e9:.2f}B"
                        if abs(v) >= 1e6: return f"${v/1e6:.1f}M"
                        return f"${v:,.0f}"
                    except Exception:
                        return str(x)
                styled = df_fin.head(8).applymap(fmt_billions)
                st.dataframe(styled, use_container_width=True)
            else:
                st.info(f"No {name} data available.")

    st.divider()

    # ── Business description ──────────────────────────────────────────────────
    desc = info.get("description", "")
    if desc:
        st.markdown("### 📝 Business Description")
        with st.expander("Show full description"):
            st.write(desc)
