"""
Pairs Trading Research — interactive dashboard.

Lets you pick a pair, tune signal/hedge/cost parameters and immediately see
the resulting backtest. Same pipeline as the notebook and the test suite —
this is just a thin presentation layer on top of src/pairs/.

Run from the repo root:

    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from statsmodels.tsa.stattools import adfuller

# Make src/ importable when running `streamlit run app/streamlit_app.py`
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pairs.data import PAIR_REGISTRY, load_pair  # noqa: E402
from pairs.pipeline import PipelineParams, run_pipeline  # noqa: E402
from pairs.signals import (  # noqa: E402
    static_hedge_ratio,
    rolling_hedge_ratio,
    build_spread,
    zscore as compute_zscore,
)


# ─── Page setup ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pairs Trading Research",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1, h2, h3 { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        [data-testid="stMetric"] { background-color: rgba(38, 39, 48, 0.04); padding: 0.75rem; border-radius: 0.4rem; }
        [data-testid="stMetricValue"] { font-size: 1.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Cached pipeline runner ──────────────────────────────────────────────────
@st.cache_data(show_spinner="Running backtest…")
def cached_pipeline(pair_id: str, params_dict: dict) -> dict:
    params = PipelineParams(**params_dict)
    r = run_pipeline(pair_id, params)
    # Cache-friendly: drop the dataclass (Pair) and rehydrate downstream
    return {
        "pair_id": r["pair"].id,
        "leg1_label": r["pair"].leg1,
        "leg2_label": r["pair"].leg2,
        "label": r["pair"].label,
        "rationale": r["pair"].rationale,
        "leg1": r["leg1"],
        "leg2": r["leg2"],
        "hedge": r["hedge"],
        "spread": r["spread"],
        "zscore": r["zscore"],
        "daily": r["daily"],
        "trades": r["trades"],
        "summary": r["summary"],
        "params": r["params"],
    }


# ─── Sidebar — controls ──────────────────────────────────────────────────────
with st.sidebar:
    st.title("Pairs Trading")
    st.caption("Mean-reversion strategy on cointegrated Indian equities.")
    st.divider()

    st.subheader("Pair")
    pair_id = st.selectbox(
        "Select a pair",
        options=list(PAIR_REGISTRY.keys()),
        format_func=lambda pid: PAIR_REGISTRY[pid].label,
        index=0,
    )

    st.subheader("Regime")
    regime = st.radio(
        "Backtest period",
        ["Stable (Apr 24 → Jan 26)", "Full (Apr 24 → Mar 26)", "Custom"],
        index=0,
        help=(
            "The 'Stable' regime ends just before the HDFC governance event of "
            "1 Feb 2026, after which the cointegration relationship for "
            "HDFC/ICICI weakened. Useful for showing how the strategy "
            "performs before vs after a structural break."
        ),
    )

    if regime == "Custom":
        date_range = st.date_input(
            "Date range",
            value=(pd.Timestamp("2024-04-01"), pd.Timestamp("2026-03-30")),
            min_value=pd.Timestamp("2024-04-01"),
            max_value=pd.Timestamp("2026-03-30"),
        )
        start_str = str(date_range[0])
        end_str = str(date_range[1])
    elif regime.startswith("Stable"):
        start_str, end_str = None, "2026-01-30"
    else:
        start_str, end_str = None, None

    st.divider()
    st.subheader("Hedge ratio")
    hedge_mode = st.radio(
        "Mode", ["static", "rolling"], horizontal=True,
        help=(
            "Static fits one β on the entire window (look-ahead, but defensible "
            "if the relationship is stable). Rolling re-fits β on the trailing "
            "N days only — strictly walk-forward, but burns history. See the "
            "rolling_hedge_analysis doc."
        ),
    )
    hedge_window = (
        st.slider("Hedge window (days)", 30, 252, 252, 10)
        if hedge_mode == "rolling"
        else 60
    )

    st.subheader("Signal")
    z_window = st.slider("Z-score window (days)", 20, 120, 60, 10)
    entry_thr = st.slider("Entry |z|", 1.0, 3.0, 2.0, 0.25)
    exit_thr = st.slider("Exit |z|", 0.0, 1.0, 0.5, 0.1)

    st.subheader("Costs")
    cost_pct = st.slider(
        "Transaction cost per leg (%)",
        0.0, 0.5, 0.10, 0.05,
        help="0.1% is realistic for a retail trader on NSE (brokerage + STT + fees).",
    )

    st.divider()
    st.caption(
        "Built by Chaitanya. Source: "
        "[GitHub](https://github.com/) · See `docs/` for full methodology."
    )


# Compose params and run
params_dict = asdict(PipelineParams(
    window=z_window,
    entry_thr=entry_thr,
    exit_thr=exit_thr,
    cost_per_leg=cost_pct / 100.0,
    hedge_mode=hedge_mode,
    hedge_window=hedge_window,
    start=start_str,
    end=end_str,
))

result = cached_pipeline(pair_id, params_dict)
summary = result["summary"]


# ─── Header ──────────────────────────────────────────────────────────────────
st.title("Pairs Trading Research — Indian Equities")
st.markdown(
    f"**Pair:** {result['label']} ({result['leg1_label']} / {result['leg2_label']})  ·  "
    f"**Regime:** {regime}  ·  "
    f"**Hedge:** {hedge_mode}  ·  "
    f"**Signal:** ±{entry_thr:.2f}σ entry / ±{exit_thr:.2f}σ exit, "
    f"{z_window}-day z-window  ·  "
    f"**Cost:** {cost_pct:.2f}% per leg"
)
st.caption(result["rationale"])


# ─── KPI row ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Sharpe Ratio", f"{summary['sharpe']:.2f}",
          help="Annualised. >1 is considered good, >2 excellent.")
c2.metric("Win Rate", f"{summary['win_rate_pct']:.1f}%")
c3.metric("Trades", f"{summary['n_trades']}")
c4.metric("Total P&L", f"₹{summary['total_pnl']:.1f}")
c5.metric("Max Drawdown", f"{summary['max_drawdown_pct']:.1f}%",
          help="As percentage of running peak.")
c6.metric(
    "Profit Factor",
    "∞" if summary["profit_factor"] == float("inf")
        else f"{summary['profit_factor']:.2f}x",
    help="Gross profit / gross loss across closed trades.",
)


# ─── ADF cointegration banner ────────────────────────────────────────────────
spread_for_adf = result["spread"].dropna()
if len(spread_for_adf) >= 30:
    adf_stat, adf_p = adfuller(spread_for_adf.values)[:2]
    if adf_p < 0.05:
        st.success(
            f"**Cointegrated** — ADF p-value = {adf_p:.4f}. The spread is "
            f"stationary, the precondition for mean-reversion trading is met."
        )
    elif adf_p < 0.10:
        st.warning(
            f"**Borderline** — ADF p-value = {adf_p:.4f}. The spread is "
            f"weakly stationary; trade with caution."
        )
    else:
        st.error(
            f"**Not cointegrated** — ADF p-value = {adf_p:.4f}. The spread "
            f"is not statistically stationary; the strategy's main assumption "
            f"is violated. Expect to lose money — and the backtest typically does."
        )


# ─── Tabbed charts ───────────────────────────────────────────────────────────
tab_pnl, tab_signal, tab_prices, tab_trades, tab_diag = st.tabs(
    ["P&L", "Signal", "Prices", "Trades", "Diagnostics"]
)

# --- P&L tab -----------------------------------------------------------------
with tab_pnl:
    daily = result["daily"]
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.04,
        subplot_titles=("Cumulative P&L (₹)", "Position"),
    )
    fig.add_trace(
        go.Scatter(
            x=daily.index, y=daily["cum_pnl"],
            mode="lines", line=dict(width=2, color="#2ca02c"),
            name="Cumulative P&L", fill="tozeroy", fillcolor="rgba(44,160,44,0.12)",
        ),
        row=1, col=1,
    )
    fig.add_hline(y=0, line=dict(color="gray", width=0.8, dash="dash"), row=1, col=1)
    fig.add_trace(
        go.Bar(
            x=daily.index, y=daily["position"],
            marker_color=["#2ca02c" if p > 0 else "#d62728" if p < 0 else "lightgray"
                          for p in daily["position"]],
            name="Position", showlegend=False,
        ),
        row=2, col=1,
    )
    fig.update_yaxes(title_text="₹", row=1, col=1)
    fig.update_yaxes(title_text="Pos", tickvals=[-1, 0, 1],
                     ticktext=["Short", "Flat", "Long"], row=2, col=1)
    fig.update_layout(height=560, hovermode="x unified",
                      margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
    st.plotly_chart(fig, width="stretch")

# --- Signal tab --------------------------------------------------------------
with tab_signal:
    z = result["zscore"].dropna()
    spread = result["spread"]
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.5, 0.5],
        vertical_spacing=0.06,
        subplot_titles=("Spread", "Z-Score"),
    )
    fig.add_trace(
        go.Scatter(x=spread.index, y=spread.values,
                   line=dict(color="#1f77b4", width=1.4), name="Spread"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=z.index, y=z.values,
                   line=dict(color="#5c85d6", width=1.4), name="z-score"),
        row=2, col=1,
    )
    fig.add_hline(y=entry_thr, line=dict(color="#d62728", dash="dash", width=1.2),
                  annotation_text=f"+{entry_thr:.2f}", row=2, col=1)
    fig.add_hline(y=-entry_thr, line=dict(color="#2ca02c", dash="dash", width=1.2),
                  annotation_text=f"-{entry_thr:.2f}", row=2, col=1)
    fig.add_hline(y=exit_thr, line=dict(color="gray", dash="dot", width=0.8), row=2, col=1)
    fig.add_hline(y=-exit_thr, line=dict(color="gray", dash="dot", width=0.8), row=2, col=1)
    fig.add_hline(y=0, line=dict(color="black", width=0.5), row=2, col=1)

    # Mark trade entries/exits as dots on the z-score plot
    if not result["trades"].empty:
        for _, tr in result["trades"].iterrows():
            entry_d = tr["entry_date"]
            exit_d = tr["exit_date"]
            color = "#2ca02c" if tr["net_pnl"] > 0 else "#d62728"
            # Find z-values at entry/exit if present in series
            for d in (entry_d, exit_d):
                if d in z.index:
                    fig.add_trace(
                        go.Scatter(
                            x=[d], y=[z.loc[d]], mode="markers",
                            marker=dict(size=8, color=color,
                                        line=dict(color="white", width=1)),
                            showlegend=False, hoverinfo="skip",
                        ),
                        row=2, col=1,
                    )

    fig.update_layout(height=600, hovermode="x unified",
                      margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
    st.plotly_chart(fig, width="stretch")

# --- Prices tab --------------------------------------------------------------
with tab_prices:
    leg1, leg2 = result["leg1"], result["leg2"]
    leg1_label, leg2_label = result["leg1_label"], result["leg2_label"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=leg1.index, y=leg1.values,
                   line=dict(color="#1f77b4", width=1.4), name=leg1_label),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=leg2.index, y=leg2.values,
                   line=dict(color="#ff7f0e", width=1.4), name=leg2_label),
        secondary_y=True,
    )
    fig.update_yaxes(title_text=f"{leg1_label} (₹)", secondary_y=False)
    fig.update_yaxes(title_text=f"{leg2_label} (₹)", secondary_y=True)
    fig.update_layout(height=460, hovermode="x unified",
                      margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                  xanchor="right", x=1))
    st.plotly_chart(fig, width="stretch")

    # Normalised view
    leg1_norm = leg1 / leg1.iloc[0]
    leg2_norm = leg2 / leg2.iloc[0]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=leg1_norm.index, y=leg1_norm.values,
                              line=dict(color="#1f77b4", width=1.4), name=leg1_label))
    fig2.add_trace(go.Scatter(x=leg2_norm.index, y=leg2_norm.values,
                              line=dict(color="#ff7f0e", width=1.4), name=leg2_label))
    fig2.add_hline(y=1.0, line=dict(color="gray", dash="dash", width=0.6))
    fig2.update_layout(height=300, hovermode="x unified", title="Normalised prices (Day 1 = 1.0)",
                       margin=dict(l=10, r=10, t=40, b=10),
                       legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                   xanchor="right", x=1))
    st.plotly_chart(fig2, width="stretch")

# --- Trades tab --------------------------------------------------------------
with tab_trades:
    if result["trades"].empty:
        st.info("No completed trades for the current parameter choice.")
    else:
        t = result["trades"].copy()
        # Friendly columns
        t["side"] = t["side"].map(
            {"long_spread": "Long spread", "short_spread": "Short spread"})
        t["entry_date"] = pd.to_datetime(t["entry_date"]).dt.strftime("%Y-%m-%d")
        t["exit_date"] = pd.to_datetime(t["exit_date"]).dt.strftime("%Y-%m-%d")
        for col in ("entry_spread", "exit_spread", "gross_pnl", "net_pnl", "cost"):
            t[col] = t[col].round(2)
        st.dataframe(
            t[["entry_date", "exit_date", "side", "holding_days",
               "entry_spread", "exit_spread", "gross_pnl", "cost", "net_pnl"]],
            width="stretch", hide_index=True,
        )
        # Summary line
        wins = (t["net_pnl"] > 0).sum()
        st.caption(
            f"{len(t)} completed trades · {wins} wins · "
            f"{len(t) - wins} losses · "
            f"avg holding {t['holding_days'].mean():.1f} days · "
            f"avg P&L ₹{t['net_pnl'].mean():.2f} per trade"
        )

# --- Diagnostics tab ---------------------------------------------------------
with tab_diag:
    leg1, leg2 = result["leg1"], result["leg2"]
    if hedge_mode == "rolling":
        beta_path = result["hedge"]
        beta_static_full = static_hedge_ratio(leg1, leg2)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=beta_path.index, y=beta_path.values,
                                 line=dict(color="#1f77b4", width=1.6),
                                 name=f"Rolling β (W={hedge_window})"))
        fig.add_hline(y=beta_static_full, line=dict(color="#d62728", dash="dash"),
                      annotation_text=f"Static full-sample β = {beta_static_full:.3f}")
        fig.update_layout(
            height=360, hovermode="x unified",
            title="Hedge ratio over time",
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            f"β stats: min {beta_path.min():.3f}, max {beta_path.max():.3f}, "
            f"mean {beta_path.mean():.3f}, std {beta_path.std():.3f}. "
            f"Wide range ⇒ unstable hedge ⇒ noisy spread. See "
            f"`docs/rolling_hedge_analysis.md` for the full discussion."
        )
    else:
        beta_static = static_hedge_ratio(leg1, leg2)
        st.markdown(
            f"**Static hedge ratio β** = `{beta_static:.4f}` (fitted on the "
            f"entire selected window). Switch the sidebar to *rolling* to "
            f"see how a walk-forward β behaves and read the diagnostics."
        )

    st.divider()
    st.markdown("### Compare alternative parameter choices")
    st.caption(
        "Run the same pair under different hedge / signal settings to "
        "feel the sensitivity of the result. The full sensitivity heatmap "
        "across (entry threshold × z-window) is in "
        "`results/parameter_sensitivity.png`."
    )

    alt_cols = st.columns(2)
    with alt_cols[0]:
        st.markdown("**Static β · ±2σ entry · 60-day window**")
        ref = cached_pipeline(pair_id, asdict(PipelineParams(
            window=60, entry_thr=2.0, exit_thr=0.5, cost_per_leg=cost_pct/100,
            hedge_mode="static",
            start=start_str, end=end_str,
        )))
        st.metric("Sharpe", f"{ref['summary']['sharpe']:.2f}",
                  delta=f"{ref['summary']['sharpe'] - summary['sharpe']:+.2f} vs current")
        st.caption(f"{ref['summary']['n_trades']} trades · "
                   f"win {ref['summary']['win_rate_pct']:.0f}%")
    with alt_cols[1]:
        st.markdown("**Rolling β-252 · ±2σ entry · 60-day window**")
        alt = cached_pipeline(pair_id, asdict(PipelineParams(
            window=60, entry_thr=2.0, exit_thr=0.5, cost_per_leg=cost_pct/100,
            hedge_mode="rolling", hedge_window=252,
            start=start_str, end=end_str,
        )))
        st.metric("Sharpe", f"{alt['summary']['sharpe']:.2f}",
                  delta=f"{alt['summary']['sharpe'] - summary['sharpe']:+.2f} vs current")
        st.caption(f"{alt['summary']['n_trades']} trades · "
                   f"win {alt['summary']['win_rate_pct']:.0f}%")


# ─── Footer ──────────────────────────────────────────────────────────────────
st.divider()
with st.expander("About this project / methodology"):
    st.markdown("""
**What this is.** A pairs-trading research framework for Indian equities. The
strategy goes long/short on the *spread* between two cointegrated stocks when
its z-score crosses a threshold, and exits when the z-score reverts toward zero.

**How it works (in one sentence):** fit `leg1 = α + β · leg2` to define a hedge,
construct the spread, standardise it on a rolling window, trade extremes.

**Honest design choices:**
- Static β is the headline because the rolling alternatives either (a) need a
  long enough window to be stable that the backtest dies of starvation, or
  (b) introduce noise that swamps the signal. `docs/rolling_hedge_analysis.md`
  shows the full sweep.
- Trades are executed at the close *after* the signal is observed (1-day lag),
  not on the signal day. No look-ahead bias.
- Transaction costs (0.1% per leg) are realistic for retail NSE trading and
  are subtracted from every entry and exit. Most "great" strategies don't
  survive this.
- ADF cointegration test acts as a *gate* — pairs that fail it (p > 0.05)
  lose money in backtest. We tested this on 3 pairs and got 3 correct
  predictions.

**Caveats:**
- 2 years of daily data is on the short side. Sharpe / drawdown estimates
  carry meaningful sampling noise.
- Pair selection itself is human/manual. A real fund would automate
  candidate-pair screening.
- The strategy uses unit position sizing. A real implementation would
  vol-target.
""")
