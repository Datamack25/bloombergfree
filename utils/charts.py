"""
utils/charts.py
Plotly chart builders — Bloomberg dark theme.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ── Theme constants ────────────────────────────────────────────────────────────
BG       = "#0a0a0f"
BG_PAPER = "#0f0f1a"
GRID     = "#1e1e32"
TEXT     = "#e8e8f0"
GREEN    = "#00d084"
RED      = "#ff3b5c"
BLUE     = "#0ea5e9"
GOLD     = "#ffd700"
ORANGE   = "#f59e0b"
PURPLE   = "#a78bfa"
FONT     = "IBM Plex Mono"

LAYOUT_BASE = dict(
    paper_bgcolor=BG_PAPER,
    plot_bgcolor=BG,
    font=dict(family=FONT, color=TEXT, size=11),
    margin=dict(l=40, r=20, t=40, b=30),
    xaxis=dict(gridcolor=GRID, showgrid=True, zeroline=False),
    yaxis=dict(gridcolor=GRID, showgrid=True, zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=GRID),
    hovermode="x unified",
)

def _apply_theme(fig):
    fig.update_layout(**LAYOUT_BASE)
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


# ── Candlestick main chart ─────────────────────────────────────────────────────

def candlestick_chart(df: pd.DataFrame, ticker: str, overlays: list = None) -> go.Figure:
    """
    Full-featured candlestick chart with optional overlays.
    overlays: list of column names to plot as lines (SMA/EMA/BB etc.)
    """
    if df is None or df.empty:
        return go.Figure()

    rows_cfg = [{"secondary_y": False}]
    row_heights = [0.6]
    subplot_titles = [f"{ticker} — Price"]

    # Detect which indicators are present
    has_volume = "Volume" in df.columns
    has_rsi    = "RSI" in df.columns
    has_macd   = "MACD" in df.columns

    if has_volume:
        rows_cfg.append({"secondary_y": False})
        row_heights.append(0.15)
        subplot_titles.append("Volume")
    if has_rsi:
        rows_cfg.append({"secondary_y": False})
        row_heights.append(0.12)
        subplot_titles.append("RSI")
    if has_macd:
        rows_cfg.append({"secondary_y": False})
        row_heights.append(0.13)
        subplot_titles.append("MACD")

    n_rows = len(rows_cfg)
    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
        specs=[[r] for r in rows_cfg],
    )

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name=ticker,
        increasing_line_color=GREEN,
        decreasing_line_color=RED,
        increasing_fillcolor=GREEN,
        decreasing_fillcolor=RED,
    ), row=1, col=1)

    # Overlay lines
    color_cycle = [BLUE, GOLD, ORANGE, PURPLE, GREEN, "#f472b6", "#34d399"]
    overlay_cols = overlays or [c for c in df.columns
                                 if any(c.startswith(p) for p in
                                        ["SMA_","EMA_","BB_","ICH_","VWAP"])]
    ci = 0
    for col in overlay_cols:
        if col not in df.columns or df[col].isna().all():
            continue
        dash = "dot" if col.startswith("BB_") else "solid"
        col_name = col.replace("_", " ")
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col],
            name=col_name,
            line=dict(color=color_cycle[ci % len(color_cycle)], width=1, dash=dash),
            opacity=0.8,
        ), row=1, col=1)
        ci += 1

    row_n = 2
    # Volume
    if has_volume:
        colors = [GREEN if df["Close"].iloc[i] >= df["Open"].iloc[i] else RED
                  for i in range(len(df))]
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"],
            name="Volume", marker_color=colors, opacity=0.7,
        ), row=row_n, col=1)
        row_n += 1

    # RSI
    if has_rsi:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"],
            name="RSI", line=dict(color=PURPLE, width=1.5),
        ), row=row_n, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color=RED,   opacity=0.5, row=row_n, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color=GREEN, opacity=0.5, row=row_n, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color=TEXT,  opacity=0.2, row=row_n, col=1)
        row_n += 1

    # MACD
    if has_macd:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD"],
            name="MACD", line=dict(color=BLUE, width=1.5),
        ), row=row_n, col=1)
        if "MACD_signal" in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["MACD_signal"],
                name="Signal", line=dict(color=ORANGE, width=1.2, dash="dash"),
            ), row=row_n, col=1)
        if "MACD_hist" in df.columns:
            hist_colors = [GREEN if v >= 0 else RED for v in df["MACD_hist"].fillna(0)]
            fig.add_trace(go.Bar(
                x=df.index, y=df["MACD_hist"],
                name="Histogram", marker_color=hist_colors, opacity=0.6,
            ), row=row_n, col=1)

    fig = _apply_theme(fig)
    fig.update_layout(
        title=dict(text=f"<b>{ticker}</b>", font=dict(size=16, color=GOLD)),
        xaxis_rangeslider_visible=False,
        height=600 + (n_rows - 1) * 120,
    )
    return fig


# ── Simple line chart ──────────────────────────────────────────────────────────

def line_chart(df: pd.DataFrame, y_col: str, title: str, color: str = BLUE) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df[y_col],
        name=y_col,
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)",
    ))
    fig = _apply_theme(fig)
    fig.update_layout(title=dict(text=title, font=dict(size=14, color=TEXT)), height=300)
    return fig


# ── Gauge chart ───────────────────────────────────────────────────────────────

def signal_gauge(score: float, label: str) -> go.Figure:
    color = GREEN if score >= 60 else (RED if score <= 40 else ORANGE)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        delta={"reference": 50, "valueformat": ".1f"},
        title={"text": f"<b>{label}</b>", "font": {"size": 18, "color": TEXT}},
        number={"font": {"size": 36, "color": color, "family": FONT}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": TEXT,
                     "tickfont": {"color": TEXT, "size": 9}},
            "bar":  {"color": color, "thickness": 0.3},
            "bgcolor": BG,
            "borderwidth": 0,
            "steps": [
                {"range": [0,  40], "color": "#1a0008"},
                {"range": [40, 60], "color": "#1a1a00"},
                {"range": [60,100], "color": "#001a08"},
            ],
            "threshold": {
                "line": {"color": GOLD, "width": 3},
                "thickness": 0.75,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG,
        font=dict(family=FONT, color=TEXT),
        margin=dict(l=20, r=20, t=60, b=20),
        height=250,
    )
    return fig


# ── Portfolio pie ─────────────────────────────────────────────────────────────

def portfolio_pie(labels: list, values: list) -> go.Figure:
    colors = [GREEN, BLUE, GOLD, ORANGE, PURPLE, RED,
              "#34d399", "#60a5fa", "#fcd34d", "#f472b6"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=colors[:len(labels)], line=dict(color=BG, width=2)),
        textfont=dict(family=FONT, color=TEXT, size=11),
        hoverinfo="label+percent+value",
    ))
    fig = _apply_theme(fig)
    fig.update_layout(
        title=dict(text="Portfolio Allocation", font=dict(color=GOLD)),
        height=350, showlegend=True,
    )
    return fig


# ── Bar race / movers ─────────────────────────────────────────────────────────

def movers_bar(df: pd.DataFrame, col="%Chg", title="Top Movers") -> go.Figure:
    df = df.sort_values(col)
    colors = [GREEN if v >= 0 else RED for v in df[col]]
    fig = go.Figure(go.Bar(
        x=df[col], y=df["Ticker"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.2f}%" for v in df[col]],
        textposition="outside",
        textfont=dict(family=FONT, color=TEXT, size=10),
    ))
    fig = _apply_theme(fig)
    fig.update_layout(title=dict(text=title, font=dict(color=GOLD)), height=280)
    return fig


# ── Heatmap ───────────────────────────────────────────────────────────────────

def sector_heatmap(df: pd.DataFrame) -> go.Figure:
    """Simple performance heatmap by sector."""
    if df.empty or "Sector" not in df.columns:
        return go.Figure()
    grouped = df.groupby("Sector")["%Chg"].mean().reset_index().sort_values("%Chg")
    colors  = [GREEN if v >= 0 else RED for v in grouped["%Chg"]]
    fig = go.Figure(go.Bar(
        x=grouped["Sector"], y=grouped["%Chg"],
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in grouped["%Chg"]],
        textposition="outside",
        textfont=dict(family=FONT, color=TEXT, size=10),
    ))
    fig = _apply_theme(fig)
    fig.update_layout(title=dict(text="Sector Performance", font=dict(color=GOLD)), height=280)
    return fig
