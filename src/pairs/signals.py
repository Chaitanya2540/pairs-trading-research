"""
Hedge-ratio estimation, spread construction, and z-score signal generation.

Two hedge-ratio modes are supported:

1. **Static OLS** — single β estimated on a fixed window of history.
   Simple and interpretable, but uses in-sample information to pick the slope
   that will be applied to the *same* data. Fine for EDA / ADF testing.

2. **Rolling OLS** — β re-estimated every day on a rolling window of recent
   history (default 60 days). At each point t, the hedge used to trade on
   day t is fitted on days [t-W, t-1] only. No future information leaks into
   the current-day spread. This is the honest way to construct the signal
   for a backtest.

The z-score is always a rolling statistic so that the standardisation is
local in time — pairs-trading signals depend on *recent* dispersion, not the
full-history standard deviation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


# ── Hedge ratio ──────────────────────────────────────────────────────────────

def static_hedge_ratio(leg1: pd.Series, leg2: pd.Series) -> float:
    """OLS slope: leg1 = α + β * leg2 + ε. Returns β.

    Uses the entire supplied window. Appropriate for EDA, the ADF cointegration
    test, and reporting a single interpretable β. Not appropriate for the
    signal that drives a backtest — see rolling_hedge_ratio.
    """
    y = leg1.values
    X = sm.add_constant(leg2.values)
    return float(sm.OLS(y, X).fit().params[1])


def rolling_hedge_ratio(
    leg1: pd.Series,
    leg2: pd.Series,
    window: int = 60,
) -> pd.Series:
    """Rolling-window OLS hedge ratio.

    At each date t, β_t is the OLS slope fitted on the previous `window`
    observations (inclusive of t). Early observations where fewer than
    `window` history points exist return NaN.

    This avoids the look-ahead bias of a static full-period β applied to
    the same history.
    """
    y = leg1.values
    x = leg2.values
    n = len(y)
    out = np.full(n, np.nan)
    for t in range(window - 1, n):
        yw = y[t - window + 1 : t + 1]
        xw = x[t - window + 1 : t + 1]
        X = sm.add_constant(xw)
        # np.linalg.lstsq is faster than statsmodels for a tight inner loop
        beta, *_ = np.linalg.lstsq(X, yw, rcond=None)
        out[t] = beta[1]
    return pd.Series(out, index=leg1.index, name="hedge_ratio")


# ── Spread ───────────────────────────────────────────────────────────────────

def build_spread(
    leg1: pd.Series,
    leg2: pd.Series,
    beta: float | pd.Series,
) -> pd.Series:
    """spread_t = leg1_t - β_t * leg2_t.

    β can be a scalar (static hedge) or a per-date series (rolling hedge).
    """
    if isinstance(beta, pd.Series):
        beta_aligned = beta.reindex(leg1.index)
        spread = leg1 - beta_aligned * leg2
    else:
        spread = leg1 - float(beta) * leg2
    spread.name = "spread"
    return spread


# ── Z-score signal ───────────────────────────────────────────────────────────

def zscore(spread: pd.Series, window: int = 60) -> pd.Series:
    """Rolling z-score: (spread - μ_window) / σ_window."""
    mu = spread.rolling(window=window).mean()
    sd = spread.rolling(window=window).std()
    z = (spread - mu) / sd
    z.name = "zscore"
    return z
