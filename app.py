"""
BloombergFree — Professional Market Terminal
Entry point & navigation
"""

import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BloombergFree Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

:root {
    --bg-primary:    #0a0a0f;
    --bg-secondary:  #0f0f1a;
    --bg-card:       #13131e;
    --bg-elevated:   #1a1a2e;
    --accent-green:  #00d084;
    --accent-red:    #ff3b5c;
    --accent-blue:   #0ea5e9;
    --accent-orange: #f59e0b;
    --accent-gold:   #ffd700;
    --text-primary:  #e8e8f0;
    --text-muted:    #6b6b8a;
    --border-subtle: #1e1e32;
    --font-mono: 'IBM Plex Mono', monospace;
    --font-sans: 'IBM Plex Sans', sans-serif;
}
html, body, [class*="css"] {
    font-family: var(--font-sans);
    background-color: var(--bg-primary);
    color: var(--text-primary);
}
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-subtle);
}
[data-testid="stMetricValue"] {
    font-family: var(--font-mono);
    font-size: 1.4rem !important;
    font-weight: 600;
}
.bf-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}
.pos { color: var(--accent-green) !important; font-weight: 600; }
.neg { color: var(--accent-red)   !important; font-weight: 600; }
.neu { color: var(--text-muted)   !important; }
.gauge-buy  { background: linear-gradient(135deg,#003d20,#00d084); color:#fff; border-radius:8px; padding:0.8rem 1.5rem; text-align:center; font-weight:700; font-size:1.5rem; letter-spacing:2px; }
.gauge-sell { background: linear-gradient(135deg,#3d0010,#ff3b5c); color:#fff; border-radius:8px; padding:0.8rem 1.5rem; text-align:center; font-weight:700; font-size:1.5rem; letter-spacing:2px; }
.gauge-hold { background: linear-gradient(135deg,#1a1a00,#f59e0b); color:#fff; border-radius:8px; padding:0.8rem 1.5rem; text-align:center; font-weight:700; font-size:1.5rem; letter-spacing:2px; }
.stTabs [data-baseweb="tab-list"] { background: var(--bg-elevated); border-radius: 6px; gap: 4px; }
.stTabs [data-baseweb="tab"] { color: var(--text-muted); font-family: var(--font-mono); font-size: 0.8rem; letter-spacing: 1px; text-transform: uppercase; padding: 8px 16px; }
.stTabs [aria-selected="true"] { background: var(--bg-card) !important; color: var(--accent-blue) !important; }
.stTextInput input, .stSelectbox > div > div { background: var(--bg-elevated) !important; border: 1px solid var(--border-subtle) !important; color: var(--text-primary) !important; font-family: var(--font-mono) !important; border-radius: 4px !important; }
.stButton > button { background: var(--bg-elevated); color: var(--text-primary); border: 1px solid var(--border-subtle); border-radius: 4px; font-family: var(--font-mono); font-size: 0.8rem; letter-spacing: 1px; text-transform: uppercase; transition: all 0.2s; }
.stButton > button:hover { background: var(--accent-blue); border-color: var(--accent-blue); color: #fff; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.terminal-header { font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); letter-spacing: 3px; text-transform: uppercase; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.4rem; margin-bottom: 1rem; }
.terminal-logo { font-family: var(--font-mono); font-size: 1.6rem; font-weight: 700; color: var(--accent-gold); letter-spacing: 4px; }
.ticker-tag { display: inline-block; background: var(--bg-elevated); border: 1px solid var(--accent-blue); color: var(--accent-blue); font-family: var(--font-mono); font-size: 0.75rem; padding: 2px 8px; border-radius: 3px; margin: 2px; }
div[data-testid="stHorizontalBlock"] > div { border-right: none; }
</style>
""", unsafe_allow_html=True)

# ── Session-state defaults ─────────────────────────────────────────────────────
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "BTC-USD"]
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []
if "finnhub_key" not in st.session_state:
    st.session_state.finnhub_key = ""
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = "AAPL"

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="terminal-logo">📈 BF</div>', unsafe_allow_html=True)
    st.markdown('<div class="terminal-header">BloombergFree Terminal v1.0</div>', unsafe_allow_html=True)

    quick_ticker = st.text_input("⚡ Quick Ticker", placeholder="AAPL, BTC-USD, EURUSD=X…")
    if quick_ticker:
        st.session_state.active_ticker = quick_ticker.upper().strip()
        st.success(f"Active: {st.session_state.active_ticker}")

    st.divider()
    with st.expander("🔑 Finnhub API Key (Optional)"):
        fh_key = st.text_input("Free key → finnhub.io", value=st.session_state.finnhub_key, type="password")
        if fh_key != st.session_state.finnhub_key:
            st.session_state.finnhub_key = fh_key
            st.success("Key saved!")
        st.caption("[Get free key at finnhub.io](https://finnhub.io) — 60 calls/min")

    st.divider()
    if st.session_state.alerts:
        st.markdown("### 🔔 Recent Alerts")
        for alert in st.session_state.alerts[-3:]:
            st.warning(alert)
    st.divider()
    st.caption("Data: yfinance · Finnhub · ccxt")
    st.caption("Auto-refresh every 60s")

# ── Navigation ─────────────────────────────────────────────────────────────────
try:
    from streamlit_option_menu import option_menu
    selected = option_menu(
        menu_title=None,
        options=["Dashboard","Watchlist","Charts","Signals","Fundamentals",
                 "News","Screener","Portfolio","Calendar","AI Advisor"],
        icons=["grid-3x3-gap","star","bar-chart-line","lightning",
               "building","newspaper","funnel","briefcase","calendar3","robot"],
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"background-color": "#0f0f1a", "padding": "4px", "border-bottom": "1px solid #1e1e32"},
            "icon": {"color": "#6b6b8a", "font-size": "14px"},
            "nav-link": {"font-family": "'IBM Plex Mono'", "font-size": "11px", "letter-spacing": "1px",
                         "text-transform": "uppercase", "color": "#6b6b8a", "padding": "8px 12px", "border-radius": "4px"},
            "nav-link-selected": {"background-color": "#13131e", "color": "#0ea5e9", "border": "1px solid #1e1e32"},
        },
    )
except ImportError:
    pages_list = ["Dashboard","Watchlist","Charts","Signals","Fundamentals",
                  "News","Screener","Portfolio","Calendar","AI Advisor"]
    selected = st.selectbox("Navigate", pages_list)

# ── Route ──────────────────────────────────────────────────────────────────────
if selected == "Dashboard":
    from pages import dashboard; dashboard.render()
elif selected == "Watchlist":
    from pages import watchlist; watchlist.render()
elif selected == "Charts":
    from pages import charts; charts.render()
elif selected == "Signals":
    from pages import signals_page; signals_page.render()
elif selected == "Fundamentals":
    from pages import fundamentals; fundamentals.render()
elif selected == "News":
    from pages import news; news.render()
elif selected == "Screener":
    from pages import screener; screener.render()
elif selected == "Portfolio":
    from pages import portfolio; portfolio.render()
elif selected == "Calendar":
    from pages import calendar_page; calendar_page.render()
elif selected == "AI Advisor":
    from pages import ai_advisor; ai_advisor.render()
