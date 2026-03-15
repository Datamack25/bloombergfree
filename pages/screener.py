"""pages/screener.py — Stock Screener"""

import streamlit as st
import pandas as pd
import io
from utils.data_fetcher import get_screener_data, get_sp500_tickers


def render():
    st.markdown("## 🔍 Stock Screener")
    st.caption("Filter the S&P 500 universe by fundamental & technical metrics.")

    # ── Filter panel ───────────────────────────────────────────────────────────
    with st.expander("⚙️ Filters", expanded=True):
        fc = st.columns(3)
        with fc[0]:
            mkt_cap_min = st.number_input("Min Market Cap ($B)", 0.0, 5000.0, 0.0, 1.0)
            mkt_cap_max = st.number_input("Max Market Cap ($B)", 0.0, 5000.0, 5000.0, 10.0)
        with fc[1]:
            pe_min = st.number_input("Min P/E", -200.0, 2000.0, -200.0, 1.0)
            pe_max = st.number_input("Max P/E", -200.0, 2000.0, 200.0, 1.0)
        with fc[2]:
            div_min = st.number_input("Min Div Yield %", 0.0, 20.0, 0.0, 0.1)
            beta_max= st.number_input("Max Beta", 0.0, 10.0, 5.0, 0.1)

        fc2 = st.columns(3)
        with fc2[0]:
            vol_min = st.number_input("Min Avg Volume (M)", 0.0, 1000.0, 0.0, 0.5)
        with fc2[1]:
            sectors_all = ["All","Technology","Healthcare","Financials","Consumer Cyclical",
                           "Communication Services","Industrials","Consumer Defensive",
                           "Energy","Utilities","Real Estate","Basic Materials"]
            sector_filter = st.selectbox("Sector", sectors_all)
        with fc2[2]:
            max_tickers = st.slider("Max tickers to screen", 10, 100, 30, 5)
            st.caption("⚠️ More tickers = slower. Start with 30.")

    if st.button("▶️ Run Screener", type="primary"):
        tickers = get_sp500_tickers()[:max_tickers]
        with st.spinner(f"Screening {len(tickers)} tickers…"):
            df = get_screener_data(tickers)

        if df.empty:
            st.error("No data returned. Try again.")
            return

        # Apply filters
        mask = pd.Series([True] * len(df))
        mask &= df["Mkt Cap ($B)"].fillna(0)  >= mkt_cap_min
        mask &= df["Mkt Cap ($B)"].fillna(0)  <= mkt_cap_max
        if pe_min > -200:
            mask &= df["PE"].fillna(0) >= pe_min
        mask &= df["PE"].fillna(999) <= pe_max
        mask &= df["Div Yield%"].fillna(0) >= div_min
        mask &= df["Beta"].fillna(0) <= beta_max
        mask &= df["Volume (M)"].fillna(0) >= vol_min
        if sector_filter != "All":
            mask &= df["Sector"] == sector_filter

        result = df[mask].reset_index(drop=True)

        st.success(f"✅ {len(result)} stocks match your criteria")

        # Color P/E and Div
        def color_pe(val):
            if pd.isna(val): return ""
            if val < 0:  return "color:#ff3b5c"
            if val < 15: return "color:#00d084"
            if val > 40: return "color:#f59e0b"
            return ""
        def color_div(val):
            if pd.isna(val): return ""
            return "color:#00d084" if val > 2 else ""

        if not result.empty:
            styled = result.style \
                .applymap(color_pe,  subset=["PE"]) \
                .applymap(color_div, subset=["Div Yield%"]) \
                .format({"Price":"${:.2f}", "Mkt Cap ($B)":"${:.1f}B",
                         "PE":"{:.1f}", "Fwd PE":"{:.1f}", "EPS":"${:.2f}",
                         "Div Yield%":"{:.2f}%", "Beta":"{:.2f}",
                         "Volume (M)":"{:.1f}M", "52W High":"${:.2f}", "52W Low":"${:.2f}"},
                        na_rep="N/A") \
                .set_properties(**{"font-family":"IBM Plex Mono","font-size":"12px"})

            st.dataframe(styled, use_container_width=True, hide_index=True,
                         height=min(700, 50 + len(result)*36))

            # Export
            buf = io.StringIO()
            result.to_csv(buf, index=False)
            st.download_button("⬇️ Export CSV", buf.getvalue(), "screener_results.csv", "text/csv")

            # ── Sector breakdown chart ────────────────────────────────────────
            if "Sector" in result.columns:
                from utils.charts import sector_heatmap
                # For heatmap we need %Chg — compute from Price vs 52W High as proxy
                st.markdown("### 🏭 Sector Breakdown")
                sect_counts = result["Sector"].value_counts().reset_index()
                sect_counts.columns = ["Sector","Count"]
                import plotly.express as px
                fig = px.treemap(sect_counts, path=["Sector"], values="Count",
                                 color="Count", color_continuous_scale="Teal")
                fig.update_layout(paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a0f",
                                  font=dict(family="IBM Plex Mono", color="#e8e8f0"),
                                  height=320, margin=dict(l=10,r=10,t=30,b=10))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Set your filters and click **Run Screener** to start.")
        st.markdown("""
        **Tips:**
        - Screen for deep-value: P/E < 15, Div Yield > 2%, Beta < 1
        - Growth screen: Fwd P/E < 25, large cap ($B > 10)
        - Dividend screen: Div Yield > 3%, Payout < 60%
        - Start with 30 tickers for speed; increase for completeness
        """)
