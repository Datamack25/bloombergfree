"""pages/dashboard.py — Market Dashboard"""

import streamlit as st
import pandas as pd
import time
from utils.data_fetcher import get_market_overview, get_top_movers
from utils.charts import movers_bar

def render():
    st.markdown("## 🌐 Market Dashboard")

    # Auto-refresh
    placeholder = st.empty()
    refresh_col, status_col = st.columns([1, 5])
    with refresh_col:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
    with status_col:
        st.caption(f"🕐 Last updated: {pd.Timestamp.now().strftime('%H:%M:%S UTC')} · Auto-refresh every 60s")

    # ── Market Overview ────────────────────────────────────────────────────────
    st.markdown("### 📊 Major Indices & Assets")
    with st.spinner("Fetching market data…"):
        overview = get_market_overview()

    if not overview.empty:
        cols = st.columns(len(overview))
        for i, row in overview.iterrows():
            with cols[i]:
                pct   = row["%Chg"]
                color = "#00d084" if pct >= 0 else "#ff3b5c"
                arrow = "▲" if pct >= 0 else "▼"
                st.markdown(f"""
                <div class="bf-card" style="text-align:center;min-height:90px">
                    <div style="font-size:0.65rem;color:#6b6b8a;letter-spacing:1px">{row['Asset'].upper()}</div>
                    <div style="font-family:'IBM Plex Mono';font-size:1.1rem;font-weight:700;color:#e8e8f0;margin:4px 0">
                        {row['Price']:,.2f}
                    </div>
                    <div style="color:{color};font-family:'IBM Plex Mono';font-size:0.85rem;font-weight:600">
                        {arrow} {abs(pct):.2f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ── Top Movers ────────────────────────────────────────────────────────────
    st.markdown("### 🚀 Top Movers")
    with st.spinner("Fetching movers…"):
        gainers, losers = get_top_movers(n=5)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📈 Top Gainers")
        if not gainers.empty:
            st.plotly_chart(movers_bar(gainers, title=""), use_container_width=True)
            st.dataframe(
                gainers[["Ticker","Price","Change","%Chg"]].style
                    .format({"Price":"${:.2f}","Change":"{:+.2f}","%Chg":"{:+.2f}%"})
                    .applymap(lambda v: "color:#00d084" if isinstance(v,float) and v>0 else "color:#ff3b5c",
                              subset=["%Chg","Change"]),
                use_container_width=True, hide_index=True,
            )
    with c2:
        st.markdown("#### 📉 Top Losers")
        if not losers.empty:
            st.plotly_chart(movers_bar(losers, title=""), use_container_width=True)
            st.dataframe(
                losers[["Ticker","Price","Change","%Chg"]].style
                    .format({"Price":"${:.2f}","Change":"{:+.2f}","%Chg":"{:+.2f}%"})
                    .applymap(lambda v: "color:#00d084" if isinstance(v,float) and v>0 else "color:#ff3b5c",
                              subset=["%Chg","Change"]),
                use_container_width=True, hide_index=True,
            )

    st.divider()

    # ── Market Status ─────────────────────────────────────────────────────────
    st.markdown("### 🔔 Market Status")
    now = pd.Timestamp.now(tz="America/New_York")
    is_weekend = now.dayofweek >= 5
    market_open = (not is_weekend) and (now.hour >= 9 and (now.hour < 16 or (now.hour == 9 and now.minute >= 30)))
    pre_market  = (not is_weekend) and (now.hour >= 4  and now.hour < 9)
    after_hours = (not is_weekend) and (now.hour >= 16 and now.hour < 20)

    if market_open:
        st.success(f"🟢 **US Markets OPEN** — NYSE/NASDAQ trading hours · {now.strftime('%H:%M ET')}")
    elif pre_market:
        st.warning(f"🟡 **Pre-Market** — 04:00–09:30 ET · {now.strftime('%H:%M ET')}")
    elif after_hours:
        st.warning(f"🟡 **After-Hours** — 16:00–20:00 ET · {now.strftime('%H:%M ET')}")
    else:
        st.error(f"🔴 **US Markets CLOSED** · {now.strftime('%A %H:%M ET')}")

    # ── Crypto 24h ────────────────────────────────────────────────────────────
    st.markdown("### ₿ Crypto Overview")
    crypto_tickers = {"Bitcoin":"BTC-USD","Ethereum":"ETH-USD","Solana":"SOL-USD",
                      "BNB":"BNB-USD","XRP":"XRP-USD","Cardano":"ADA-USD"}
    from utils.data_fetcher import get_bulk_quotes
    crypto_df = get_bulk_quotes(list(crypto_tickers.values()))
    if not crypto_df.empty:
        crypto_df["Name"] = crypto_df["Ticker"].map({v:k for k,v in crypto_tickers.items()})
        st.dataframe(
            crypto_df[["Name","Ticker","Price","Change","%Chg"]].style
                .format({"Price":"${:,.2f}","Change":"{:+.4f}","%Chg":"{:+.2f}%"})
                .applymap(lambda v: "color:#00d084" if isinstance(v,float) and v>0 else "color:#ff3b5c",
                          subset=["%Chg","Change"]),
            use_container_width=True, hide_index=True,
        )

    # Auto rerun every 60s
    time.sleep(0)
    st.markdown("""
    <script>
    setTimeout(function(){window.location.reload();}, 60000);
    </script>""", unsafe_allow_html=True)
