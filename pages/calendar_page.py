"""pages/calendar_page.py — Economic Calendar"""

import streamlit as st
import pandas as pd
from utils.data_fetcher import get_economic_calendar
import plotly.graph_objects as go


IMPACT_COLOR = {"HIGH": "#ff3b5c", "MEDIUM": "#f59e0b", "LOW": "#6b6b8a"}
IMPACT_ICON  = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}


def render():
    st.markdown("## 📅 Economic Calendar")

    if not st.session_state.get("finnhub_key"):
        st.info("💡 Enter a free [Finnhub API key](https://finnhub.io) in the sidebar for live economic calendar data. "
                "Showing representative upcoming events instead.")

    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("Loading economic calendar…"):
        df = get_economic_calendar()

    if df is None or df.empty:
        st.warning("No calendar data available.")
        return

    # ── Filters ────────────────────────────────────────────────────────────────
    fc = st.columns(3)
    with fc[0]:
        countries = ["All"] + sorted(df["Country"].dropna().unique().tolist())
        sel_country = st.selectbox("Country", countries)
    with fc[1]:
        impacts = ["All", "HIGH", "MEDIUM", "LOW"]
        sel_impact = st.selectbox("Impact", impacts)
    with fc[2]:
        if "Date" in df.columns:
            try:
                dates = sorted(df["Date"].dropna().unique())
                sel_date = st.selectbox("Date", ["All"] + list(dates))
            except Exception:
                sel_date = "All"
        else:
            sel_date = "All"

    filtered = df.copy()
    if sel_country != "All":
        filtered = filtered[filtered["Country"] == sel_country]
    if sel_impact != "All":
        filtered = filtered[filtered["Impact"] == sel_impact]
    if sel_date != "All":
        filtered = filtered[filtered["Date"] == sel_date]

    st.markdown(f"**{len(filtered)} events** matching filters")

    # ── Calendar view ──────────────────────────────────────────────────────────
    today_str = pd.Timestamp.now().strftime("%Y-%m-%d")

    for _, row in filtered.iterrows():
        date_str = str(row.get("Date", ""))
        impact   = str(row.get("Impact", "LOW")).upper()
        color    = IMPACT_COLOR.get(impact, "#6b6b8a")
        icon     = IMPACT_ICON.get(impact, "🟢")
        is_today = date_str == today_str

        border = "2px solid #0ea5e9" if is_today else "1px solid #1e1e32"
        bg     = "#13131e" if not is_today else "#0f1a2e"

        actual   = row.get("Actual", "--")   or "--"
        estimate = row.get("Estimate", "--") or "--"
        previous = row.get("Previous", "--") or "--"

        st.markdown(f"""
        <div style="background:{bg};border:{border};border-radius:8px;padding:10px 14px;
                    margin-bottom:6px;display:flex;align-items:center;gap:12px">
            <div style="min-width:90px;font-family:'IBM Plex Mono';font-size:0.75rem;color:#6b6b8a">
                {date_str}
            </div>
            <div style="min-width:24px;font-size:1rem">{icon}</div>
            <div style="flex:1">
                <div style="font-weight:600;font-size:0.9rem;color:#e8e8f0">{row.get('Event','')}</div>
                <div style="font-size:0.7rem;color:#6b6b8a;font-family:'IBM Plex Mono'">
                    {row.get('Country','')} · Impact: <span style="color:{color};font-weight:700">{impact}</span>
                </div>
            </div>
            <div style="display:flex;gap:16px;text-align:center">
                <div>
                    <div style="font-size:0.65rem;color:#6b6b8a;font-family:'IBM Plex Mono'">ACTUAL</div>
                    <div style="font-family:'IBM Plex Mono';font-weight:700;color:#00d084">{actual}</div>
                </div>
                <div>
                    <div style="font-size:0.65rem;color:#6b6b8a;font-family:'IBM Plex Mono'">ESTIMATE</div>
                    <div style="font-family:'IBM Plex Mono';color:#e8e8f0">{estimate}</div>
                </div>
                <div>
                    <div style="font-size:0.65rem;color:#6b6b8a;font-family:'IBM Plex Mono'">PREVIOUS</div>
                    <div style="font-family:'IBM Plex Mono';color:#6b6b8a">{previous}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Impact breakdown chart ─────────────────────────────────────────────────
    if not filtered.empty and "Impact" in filtered.columns:
        st.markdown("### 📊 Events by Impact")
        imp_counts = filtered["Impact"].value_counts()
        fig = go.Figure(go.Bar(
            x=imp_counts.index,
            y=imp_counts.values,
            marker_color=[IMPACT_COLOR.get(i, "#6b6b8a") for i in imp_counts.index],
            text=imp_counts.values,
            textposition="outside",
            textfont=dict(family="IBM Plex Mono", color="#e8e8f0"),
        ))
        fig.update_layout(
            paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a0f",
            font=dict(family="IBM Plex Mono", color="#e8e8f0"),
            height=220, margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(gridcolor="#1e1e32"), yaxis=dict(gridcolor="#1e1e32"),
        )
        st.plotly_chart(fig, use_container_width=True)
