"""pages/ai_advisor.py — AI-Powered Investment Advisor"""

import streamlit as st
import pandas as pd
import numpy as np
from utils.data_fetcher import get_ohlcv, get_fundamentals, get_news, get_quote
from utils.signals import compute_composite_signal
from utils.sentiment import analyze_news, aggregate_sentiment
from utils.charts import signal_gauge


def _score_bar(label: str, score: float, max_score: float = 100):
    pct   = min(100, score / max_score * 100)
    color = "#00d084" if pct >= 60 else ("#ff3b5c" if pct <= 40 else "#f59e0b")
    return f"""
    <div style="margin:6px 0">
        <div style="display:flex;justify-content:space-between;margin-bottom:3px">
            <span style="font-family:'IBM Plex Mono';font-size:0.75rem;color:#6b6b8a">{label}</span>
            <span style="font-family:'IBM Plex Mono';font-size:0.75rem;color:{color};font-weight:700">{score:.0f}</span>
        </div>
        <div style="background:#1e1e32;border-radius:4px;height:8px">
            <div style="width:{pct:.0f}%;background:{color};height:8px;border-radius:4px;
                        transition:width 0.4s ease"></div>
        </div>
    </div>"""


def _fmt_val(val, fmt="{:.2f}", prefix="", suffix=""):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    return f"{prefix}{fmt.format(val)}{suffix}"


def render():
    st.markdown("## 🤖 AI Advisor — Full Analysis & Recommendation")
    st.caption("Combines technical signals, fundamentals, news sentiment and macro context "
               "into one clear actionable recommendation.")

    # ── Ticker input ───────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        ticker = st.text_input("Ticker to analyse", value=st.session_state.get("active_ticker", "AAPL"))
    with c2:
        horizon = st.selectbox("Investment horizon",
                               ["Short-term (days–weeks)", "Medium-term (weeks–months)",
                                "Long-term (months–years)"])
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("🚀 Analyse", type="primary")

    if not ticker:
        st.info("Enter a ticker above and click **Analyse**.")
        return

    ticker = ticker.upper().strip()
    st.session_state.active_ticker = ticker

    if not run and "ai_last_ticker" not in st.session_state:
        st.info(f"Ready to analyse **{ticker}**. Click **🚀 Analyse** to start.")
        return

    if run:
        st.session_state["ai_last_ticker"] = ticker
    elif st.session_state.get("ai_last_ticker") != ticker:
        st.info(f"Click **🚀 Analyse** to run analysis for **{ticker}**.")
        return

    # ── Data gathering ─────────────────────────────────────────────────────────
    progress = st.progress(0, text="Loading price data…")

    df_daily = get_ohlcv(ticker, period="1y",  interval="1d")
    df_weekly= get_ohlcv(ticker, period="3y",  interval="1wk")
    progress.progress(20, text="Computing technical signals…")

    sig_daily  = compute_composite_signal(df_daily)
    sig_weekly = compute_composite_signal(df_weekly)
    progress.progress(40, text="Loading fundamentals…")

    info = get_fundamentals(ticker)
    progress.progress(60, text="Analysing news & sentiment…")

    articles  = get_news(ticker, limit=20)
    sent_df   = analyze_news(articles)
    sent_agg  = aggregate_sentiment(sent_df)
    progress.progress(80, text="Generating recommendation…")

    quote = get_quote(ticker)
    progress.progress(100, text="Done!")
    progress.empty()

    # ── Score calculation ──────────────────────────────────────────────────────
    tech_score    = (sig_daily["score"] * 0.6 + sig_weekly["score"] * 0.4)
    sent_score    = (sent_agg["mean"] + 1) / 2 * 100        # −1..+1 → 0..100
    sent_score    = max(5, min(95, sent_score))

    # Fundamental score (heuristic)
    fund_score = 50.0
    pe  = info.get("pe")
    roe = info.get("roe")
    pm  = info.get("profit_margin")
    de  = info.get("debt_equity")
    if pe  is not None and not pd.isna(pe):
        if 0 < pe < 20:  fund_score += 10
        elif pe > 50:    fund_score -= 10
    if roe is not None and not pd.isna(roe):
        if roe > 0.15:   fund_score += 10
        elif roe < 0:    fund_score -= 15
    if pm  is not None and not pd.isna(pm):
        if pm  > 0.15:   fund_score += 8
        elif pm < 0:     fund_score -= 10
    if de  is not None and not pd.isna(de):
        if de  < 1:      fund_score += 5
        elif de > 3:     fund_score -= 8
    fund_score = max(5, min(95, fund_score))

    # Horizon weight: long-term → fundamentals matter more
    if "Long" in horizon:
        composite = tech_score * 0.35 + fund_score * 0.40 + sent_score * 0.25
    elif "Medium" in horizon:
        composite = tech_score * 0.45 + fund_score * 0.30 + sent_score * 0.25
    else:
        composite = tech_score * 0.60 + fund_score * 0.15 + sent_score * 0.25

    composite = round(composite, 1)

    if composite >= 62:
        verdict     = "BUY"
        verdict_css = "gauge-buy"
        verdict_icon= "📈"
    elif composite <= 38:
        verdict     = "SELL"
        verdict_css = "gauge-sell"
        verdict_icon= "📉"
    else:
        verdict     = "HOLD"
        verdict_css = "gauge-hold"
        verdict_icon= "➡️"

    confidence_dist = abs(composite - 50)
    confidence = "HIGH" if confidence_dist >= 20 else ("MEDIUM" if confidence_dist >= 10 else "LOW")

    # ── Header card ────────────────────────────────────────────────────────────
    st.markdown(f"### {verdict_icon} {info.get('name', ticker)} — {ticker}")
    price     = quote.get("price", 0)
    price_pct = quote.get("pct", 0)
    price_color = "#00d084" if price_pct >= 0 else "#ff3b5c"

    st.markdown(f"""
    <div class="bf-card" style="border-color:#0ea5e9">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px">
            <div>
                <div style="font-family:'IBM Plex Mono';font-size:2.2rem;font-weight:700;color:#e8e8f0">
                    ${price:,.4f}
                </div>
                <div style="font-family:'IBM Plex Mono';font-size:1rem;color:{price_color}">
                    {'▲' if price_pct >= 0 else '▼'} {abs(price_pct):.2f}% today
                </div>
            </div>
            <div style="text-align:center">
                <div class="{verdict_css}" style="font-size:2rem;padding:1rem 2.5rem;letter-spacing:4px">
                    {verdict}
                </div>
                <div style="margin-top:8px;color:#6b6b8a;font-family:'IBM Plex Mono';font-size:0.7rem">
                    COMPOSITE SCORE
                </div>
                <div style="font-family:'IBM Plex Mono';font-size:1.6rem;font-weight:700;
                            color:{'#00d084' if composite>=60 else ('#ff3b5c' if composite<=40 else '#f59e0b')}">
                    {composite}/100
                </div>
            </div>
            <div style="text-align:center">
                <div style="color:#6b6b8a;font-family:'IBM Plex Mono';font-size:0.7rem;letter-spacing:2px">CONFIDENCE</div>
                <div style="font-family:'IBM Plex Mono';font-size:1.5rem;font-weight:700;color:#ffd700">{confidence}</div>
                <div style="color:#6b6b8a;font-family:'IBM Plex Mono';font-size:0.7rem;margin-top:4px">
                    {horizon.split('(')[0].strip()}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Score breakdown ────────────────────────────────────────────────────────
    col_g, col_b = st.columns([1, 1])
    with col_g:
        fig = signal_gauge(composite, f"{ticker} — AI Score")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("**Score breakdown:**")
        st.markdown(
            _score_bar("Technical (Daily)", sig_daily["score"]) +
            _score_bar("Technical (Weekly)", sig_weekly["score"]) +
            _score_bar("Fundamental", fund_score) +
            _score_bar("News Sentiment", sent_score),
            unsafe_allow_html=True,
        )
        st.markdown(f"""
        <div style="margin-top:12px;padding:8px 12px;background:#1a1a2e;border-radius:6px;
                    border-left:3px solid #0ea5e9">
            <div style="font-family:'IBM Plex Mono';font-size:0.7rem;color:#6b6b8a">WEIGHTS ({horizon.split('(')[0].strip()})</div>
            <div style="font-size:0.8rem;color:#e8e8f0;margin-top:4px">
                Technical {'60%' if 'Short' in horizon else '45%' if 'Medium' in horizon else '35%'} ·
                Fundamental {'15%' if 'Short' in horizon else '30%' if 'Medium' in horizon else '40%'} ·
                Sentiment 25%
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Technical deep-dive ────────────────────────────────────────────────────
    st.markdown("### ⚡ Technical Analysis")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown(f"**Daily signal: `{sig_daily['label']}` ({sig_daily['score']:.0f}/100)**")
        for s in sig_daily.get("strategies", []):
            sc    = s["score"]
            color = "#00d084" if sc >= 60 else ("#ff3b5c" if sc <= 40 else "#f59e0b")
            lbl   = "BUY" if sc >= 60 else ("SELL" if sc <= 40 else "HOLD")
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:3px 0;'
                f'border-bottom:1px solid #1e1e32">'
                f'<span style="font-family:\'IBM Plex Mono\';font-size:0.75rem;color:#6b6b8a">{s["name"]}</span>'
                f'<span style="font-family:\'IBM Plex Mono\';font-size:0.75rem;color:{color};font-weight:700">'
                f'{lbl} ({sc:.0f})</span></div>',
                unsafe_allow_html=True,
            )

    with t2:
        st.markdown(f"**Weekly signal: `{sig_weekly['label']}` ({sig_weekly['score']:.0f}/100)**")
        for reason in sig_daily.get("reasons", [])[:6]:
            icon = "📈" if any(w in reason.lower() for w in ["buy","bull","oversold","above","golden"]) else \
                   ("📉" if any(w in reason.lower() for w in ["sell","bear","overbought","below","death"]) else "➡️")
            st.markdown(f"{icon} {reason}")

    st.divider()

    # ── Fundamentals snapshot ──────────────────────────────────────────────────
    st.markdown("### 🏢 Fundamental Snapshot")
    fc = st.columns(6)
    metrics = [
        ("P/E",          _fmt_val(info.get("pe"),         "{:.1f}x")),
        ("EPS",          _fmt_val(info.get("eps"),         "${:.2f}")),
        ("Profit Margin",_fmt_val((info.get("profit_margin") or 0)*100, "{:.1f}%")),
        ("D/E Ratio",    _fmt_val(info.get("debt_equity"), "{:.2f}x")),
        ("Div Yield",    _fmt_val((info.get("dividend_yield") or 0)*100, "{:.2f}%")),
        ("Beta",         _fmt_val(info.get("beta"),        "{:.2f}")),
    ]
    for i, (label, value) in enumerate(metrics):
        with fc[i]:
            st.markdown(
                f'<div class="bf-card" style="text-align:center">'
                f'<div style="color:#6b6b8a;font-size:0.65rem;font-family:\'IBM Plex Mono\';'
                f'letter-spacing:1px;text-transform:uppercase">{label}</div>'
                f'<div style="font-family:\'IBM Plex Mono\';font-weight:700;font-size:1rem;'
                f'color:#e8e8f0;margin-top:4px">{value}</div>'
                f'</div>', unsafe_allow_html=True,
            )

    st.divider()

    # ── Sentiment ──────────────────────────────────────────────────────────────
    st.markdown("### 📰 News Sentiment")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Articles analysed", len(sent_df))
    sc2.metric("Avg sentiment", f"{sent_agg['mean']:+.3f}")
    sc3.markdown(f"""
    <div style="text-align:center;padding:8px">
        <div style="color:#6b6b8a;font-family:'IBM Plex Mono';font-size:0.7rem;letter-spacing:2px">SENTIMENT</div>
        <div style="color:{sent_agg['color']};font-family:'IBM Plex Mono';font-size:1.2rem;font-weight:700">
            {sent_agg['label']}
        </div>
    </div>""", unsafe_allow_html=True)

    if not sent_df.empty:
        top3 = sent_df.nlargest(3, "Score") if verdict == "BUY" else sent_df.nsmallest(3, "Score")
        st.markdown(f"**{'Most bullish' if verdict == 'BUY' else 'Most bearish'} headlines:**")
        for _, row in top3.iterrows():
            color = "#00d084" if row["Score"] >= 0 else "#ff3b5c"
            url   = row.get("URL", "#") or "#"
            link  = f'<a href="{url}" target="_blank" style="color:#e8e8f0">{row["Title"]}</a>'
            st.markdown(
                f'<div style="padding:4px 8px;border-left:3px solid {color};margin:3px 0;font-size:0.85rem">'
                f'{link} <span style="color:{color};font-family:\'IBM Plex Mono\';font-size:0.75rem">'
                f'({row["Score"]:+.2f})</span></div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Final recommendation ───────────────────────────────────────────────────
    st.markdown("### 🎯 Final Recommendation")

    # Build narrative
    tech_lbl = sig_daily["label"]
    fund_qual = "strong" if fund_score >= 65 else ("weak" if fund_score <= 40 else "mixed")
    sent_qual = "positive" if sent_agg["mean"] >= 0.1 else ("negative" if sent_agg["mean"] <= -0.1 else "neutral")

    if verdict == "BUY":
        summary = (
            f"**{ticker}** presents a **buying opportunity** over the {horizon.lower()} horizon. "
            f"The daily technical picture is **{tech_lbl.lower()}** (score {sig_daily['score']:.0f}/100), "
            f"supported by a **{sig_weekly['label'].lower()}** weekly trend. "
            f"Fundamentals appear **{fund_qual}** (score {fund_score:.0f}/100) and "
            f"news sentiment is **{sent_qual}** ({sent_agg['mean']:+.2f}). "
            f"The composite AI score of **{composite}/100** with **{confidence} confidence** "
            f"suggests positioning **long** with appropriate risk management."
        )
    elif verdict == "SELL":
        summary = (
            f"**{ticker}** shows **bearish signals** over the {horizon.lower()} horizon. "
            f"The daily technical picture is **{tech_lbl.lower()}** (score {sig_daily['score']:.0f}/100), "
            f"confirmed by a **{sig_weekly['label'].lower()}** weekly trend. "
            f"Fundamentals are **{fund_qual}** (score {fund_score:.0f}/100) and "
            f"news sentiment is **{sent_qual}** ({sent_agg['mean']:+.2f}). "
            f"The composite AI score of **{composite}/100** with **{confidence} confidence** "
            f"suggests **reducing or exiting** any long positions."
        )
    else:
        summary = (
            f"**{ticker}** gives **mixed signals** over the {horizon.lower()} horizon. "
            f"The daily technical picture is **{tech_lbl.lower()}** (score {sig_daily['score']:.0f}/100) "
            f"with a **{sig_weekly['label'].lower()}** weekly trend. "
            f"Fundamentals are **{fund_qual}** (score {fund_score:.0f}/100) and "
            f"news sentiment is **{sent_qual}** ({sent_agg['mean']:+.2f}). "
            f"The composite AI score of **{composite}/100** with **{confidence} confidence** "
            f"suggests **holding** existing positions and waiting for a clearer signal before adding."
        )

    st.markdown(f"""
    <div class="bf-card" style="border-color:{'#00d084' if verdict=='BUY' else ('#ff3b5c' if verdict=='SELL' else '#f59e0b')};
                                border-width:2px">
        <div style="font-family:'IBM Plex Mono';font-size:0.7rem;color:#6b6b8a;letter-spacing:2px;margin-bottom:8px">
            AI ADVISOR VERDICT — {ticker} — {horizon.upper()}
        </div>
        <div style="font-size:0.95rem;line-height:1.6;color:#e8e8f0">{summary}</div>
    </div>
    """, unsafe_allow_html=True)

    # Risk disclaimer
    st.markdown("""
    <div style="margin-top:12px;padding:8px 12px;background:#1a1a00;border-radius:6px;
                border-left:3px solid #f59e0b">
        <div style="font-size:0.75rem;color:#6b6b8a">
            ⚠️ <strong style="color:#f59e0b">Disclaimer:</strong>
            This is an automated algorithmic analysis for informational purposes only.
            It does not constitute financial advice. Always do your own research (DYOR)
            and consult a qualified financial advisor before making investment decisions.
            Past performance is not indicative of future results.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Comparables on watchlist ───────────────────────────────────────────────
    if len(st.session_state.watchlist) > 1:
        st.markdown("### 📊 Watchlist Signal Comparison")
        if st.button("▶️ Compare with Watchlist"):
            compare_tickers = [t for t in st.session_state.watchlist if t != ticker][:5]
            rows = [{"Ticker": ticker, "Signal": verdict,
                     "Score": composite, "Confidence": confidence}]
            prog2 = st.progress(0)
            for i, t in enumerate(compare_tickers):
                prog2.progress((i + 1) / len(compare_tickers))
                df_t = get_ohlcv(t, period="6mo", interval="1d")
                if df_t is not None and not df_t.empty:
                    r = compute_composite_signal(df_t)
                    rows.append({"Ticker": t, "Signal": r["label"],
                                 "Score": r["score"], "Confidence": r["confidence"]})
            prog2.empty()
            comp_df = pd.DataFrame(rows).sort_values("Score", ascending=False)

            def color_sig(val):
                if val == "BUY":  return "color:#00d084;font-weight:bold"
                if val == "SELL": return "color:#ff3b5c;font-weight:bold"
                return "color:#f59e0b;font-weight:bold"

            st.dataframe(
                comp_df.style.applymap(color_sig, subset=["Signal"])
                    .set_properties(**{"font-family": "IBM Plex Mono"}),
                use_container_width=True, hide_index=True,
            )
