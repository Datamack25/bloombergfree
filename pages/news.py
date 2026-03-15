"""pages/news.py — News & Sentiment Analysis"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.data_fetcher import get_news
from utils.sentiment import analyze_news, aggregate_sentiment


def render():
    st.markdown("## 📰 News & Sentiment Analysis")

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        ticker = st.text_input("Ticker", value=st.session_state.get("active_ticker", "AAPL"))
    with c2:
        limit = st.selectbox("Max articles", [10, 20, 30, 50], index=1)
    with c3:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()

    if not ticker:
        return
    ticker = ticker.upper().strip()
    st.session_state.active_ticker = ticker

    with st.spinner(f"Fetching news for {ticker}…"):
        articles = get_news(ticker, limit=limit)

    if not articles:
        st.warning("No news articles found. Try another ticker or check your connection.")
        return

    # Analyse sentiment
    df = analyze_news(articles)
    agg = aggregate_sentiment(df)

    # ── Sentiment Overview ────────────────────────────────────────────────────
    st.markdown(f"### Sentiment Overview — {ticker}")
    ov1, ov2, ov3, ov4, ov5 = st.columns(5)
    ov1.metric("Articles", len(df))
    ov2.metric("Avg Score", f"{agg['mean']:+.3f}")
    ov3.metric("📈 Bullish", agg["bullish"])
    ov4.metric("📉 Bearish", agg["bearish"])
    ov5.metric("➡️ Neutral", agg["neutral"])

    # Big sentiment badge
    st.markdown(f"""
    <div style="text-align:center;margin:16px 0">
        <div style="background:#13131e;border:2px solid {agg['color']};border-radius:12px;
                    padding:16px 32px;display:inline-block">
            <div style="font-family:'IBM Plex Mono';font-size:0.7rem;color:#6b6b8a;letter-spacing:2px">
                OVERALL MARKET SENTIMENT
            </div>
            <div style="color:{agg['color']};font-family:'IBM Plex Mono';font-size:2rem;font-weight:700;
                        margin-top:4px">
                {agg['label']}
            </div>
            <div style="color:#6b6b8a;font-size:0.8rem;margin-top:4px">
                Score: {agg['mean']:+.3f} (range −1 to +1)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sentiment distribution chart ──────────────────────────────────────────
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df["Score"],
            nbinsx=20,
            marker_color="#0ea5e9",
            opacity=0.8,
            name="Score distribution",
        ))
        fig.add_vline(x=0,    line_dash="dash", line_color="#6b6b8a", opacity=0.5)
        fig.add_vline(x=0.2,  line_dash="dot",  line_color="#00d084", opacity=0.5)
        fig.add_vline(x=-0.2, line_dash="dot",  line_color="#ff3b5c", opacity=0.5)
        fig.update_layout(
            paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a0f",
            font=dict(family="IBM Plex Mono", color="#e8e8f0"),
            height=220,
            margin=dict(l=40, r=20, t=40, b=20),
            title=dict(text="Sentiment Score Distribution", font=dict(color="#ffd700")),
            xaxis=dict(gridcolor="#1e1e32", title="Score"),
            yaxis=dict(gridcolor="#1e1e32", title="Count"),
            bargap=0.05,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Sentiment timeline ────────────────────────────────────────────────────
    if not df.empty and "Published" in df.columns:
        df_sorted = df.copy()
        try:
            df_sorted["pub_dt"] = pd.to_datetime(df_sorted["Published"], utc=True, errors="coerce")
            df_sorted = df_sorted.dropna(subset=["pub_dt"]).sort_values("pub_dt")
            if len(df_sorted) > 3:
                colors = ["#00d084" if s >= 0.2 else ("#ff3b5c" if s <= -0.2 else "#f59e0b")
                          for s in df_sorted["Score"]]
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=df_sorted["pub_dt"], y=df_sorted["Score"],
                    mode="markers+lines",
                    marker=dict(color=colors, size=8),
                    line=dict(color="#1e1e32", width=1),
                    name="Sentiment over time",
                    hovertext=df_sorted["Title"],
                ))
                fig2.add_hline(y=0.2,  line_dash="dot", line_color="#00d084", opacity=0.4)
                fig2.add_hline(y=-0.2, line_dash="dot", line_color="#ff3b5c", opacity=0.4)
                fig2.add_hline(y=0,    line_dash="dash", line_color="#6b6b8a", opacity=0.3)
                fig2.update_layout(
                    paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a0f",
                    font=dict(family="IBM Plex Mono", color="#e8e8f0"),
                    height=220, margin=dict(l=40, r=20, t=40, b=20),
                    title=dict(text="Sentiment Timeline", font=dict(color="#ffd700")),
                    xaxis=dict(gridcolor="#1e1e32"), yaxis=dict(gridcolor="#1e1e32"),
                )
                st.plotly_chart(fig2, use_container_width=True)
        except Exception:
            pass

    st.divider()

    # ── Articles list ──────────────────────────────────────────────────────────
    st.markdown("### 📄 Articles")
    for _, row in df.iterrows():
        score = row["Score"]
        color = "#00d084" if score >= 0.2 else ("#ff3b5c" if score <= -0.2 else "#f59e0b")
        bar_w = int(abs(score) * 100)
        url   = row.get("URL", "#") or "#"
        title_link = f'<a href="{url}" target="_blank" style="color:#e8e8f0;text-decoration:none">{row["Title"]}</a>' if url != "#" else row["Title"]
        st.markdown(f"""
        <div class="bf-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
                <div style="flex:1">
                    <div style="font-size:0.9rem;line-height:1.4">{title_link}</div>
                    <div style="color:#6b6b8a;font-size:0.7rem;font-family:'IBM Plex Mono';margin-top:4px">
                        {row.get('Source','')} · {row.get('Published','')[:16]}
                    </div>
                </div>
                <div style="text-align:right;min-width:100px">
                    <div style="color:{color};font-family:'IBM Plex Mono';font-weight:700;font-size:0.85rem">
                        {row['Sentiment']}
                    </div>
                    <div style="color:#6b6b8a;font-family:'IBM Plex Mono';font-size:0.75rem">
                        {score:+.3f}
                    </div>
                    <div style="background:#1e1e32;border-radius:2px;height:4px;margin-top:4px">
                        <div style="width:{bar_w}%;background:{color};height:4px;border-radius:2px"></div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Export ────────────────────────────────────────────────────────────────
    import io
    buf = io.StringIO()
    df.drop(columns=["_color"], errors="ignore").to_csv(buf, index=False)
    st.download_button("⬇️ Export Sentiment CSV", buf.getvalue(),
                       f"{ticker}_sentiment.csv", "text/csv")
