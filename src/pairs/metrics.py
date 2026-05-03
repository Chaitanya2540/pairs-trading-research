"""
Performance metrics for a pairs-trading backtest.

All metrics take the `daily` and `trades` dataframes produced by
pairs.backtest.run_backtest and return plain floats / dicts so they're easy
to display in a Streamlit table or assert on in a test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252
DEFAULT_RFR_ANNUAL = 0.065  # India 10-year G-sec / T-bill proxy


def sharpe_ratio(
    daily_pnl: pd.Series,
    rfr_annual: float = DEFAULT_RFR_ANNUAL,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualised Sharpe on a daily P&L series.

    Computed on the full calendar of the backtest (including flat days with
    zero P&L), which is the conservative / standard convention.
    """
    rfr_daily = rfr_annual / trading_days
    mu = daily_pnl.mean()
    sd = daily_pnl.std()
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float((mu - rfr_daily) / sd * np.sqrt(trading_days))


def max_drawdown(cum_pnl: pd.Series) -> tuple[float, float]:
    """Return (max_drawdown_abs, max_drawdown_pct_of_peak).

    pct is expressed as a negative number. If the peak was zero or negative
    we return 0.0 pct (the conventional guard for early losses).
    """
    cp = cum_pnl.values
    peak = np.maximum.accumulate(cp)
    dd = cp - peak
    idx = int(np.argmin(dd))
    max_dd_abs = float(dd[idx])
    peak_at_min = peak[idx]
    if peak_at_min <= 0:
        return max_dd_abs, 0.0
    return max_dd_abs, float(max_dd_abs / peak_at_min * 100)


def profit_factor(trades: pd.DataFrame) -> float:
    """Gross profits / gross losses across completed trades."""
    if trades.empty:
        return 0.0
    wins = trades.loc[trades["net_pnl"] > 0, "net_pnl"].sum()
    losses = -trades.loc[trades["net_pnl"] < 0, "net_pnl"].sum()
    if losses <= 0:
        return float("inf")
    return float(wins / losses)


def win_rate(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    return float((trades["net_pnl"] > 0).mean() * 100)


def summarise(daily: pd.DataFrame, trades: pd.DataFrame) -> dict:
    """Roll every metric into a single dict for reporting / testing."""
    max_dd_abs, max_dd_pct = max_drawdown(daily["cum_pnl"])
    return {
        "n_days": int(len(daily)),
        "n_trades": int(len(trades)),
        "win_rate_pct": win_rate(trades),
        "total_pnl": float(trades["net_pnl"].sum()) if not trades.empty else 0.0,
        "avg_trade_pnl": float(trades["net_pnl"].mean()) if not trades.empty else 0.0,
        "best_trade": float(trades["net_pnl"].max()) if not trades.empty else 0.0,
        "worst_trade": float(trades["net_pnl"].min()) if not trades.empty else 0.0,
        "sharpe": sharpe_ratio(daily["daily_pnl"]),
        "max_drawdown": max_dd_abs,
        "max_drawdown_pct": max_dd_pct,
        "profit_factor": profit_factor(trades),
    }
