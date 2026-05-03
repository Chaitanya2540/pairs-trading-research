"""
Pairs-trading backtest engine.

Rules (vectorisable but kept as an explicit event loop for clarity):

- State is one of {flat, long_spread, short_spread}.
- Entry:  |z| > entry_thr and currently flat.
          z > +entry_thr → short the spread (expect it to fall).
          z < -entry_thr → long the spread (expect it to rise).
- Exit:   |z| < exit_thr while holding a position.
- Execution: signals are observed on day t's close, but trades are executed
             at day t+1's close to avoid look-ahead (you cannot trade on
             today's close using today's close as a signal).
- Costs:  round-trip transaction cost of `cost_per_leg * |spread|` on entry
          and again on exit (i.e. both legs pay). Default 0.1% per leg.
- P&L:    daily mark-to-market on the spread while in position.
          net_trade_pnl = position × (exit_spread - entry_spread) − 2 × costs

Returns a dict with:
- daily: DataFrame(date, zscore, position, spread, mtm_pnl, trade_pnl, cum_pnl)
- trades: DataFrame(entry_date, exit_date, side, entry_spread, exit_spread, net_pnl)
- params: the parameters used (for reproducibility)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestParams:
    entry_thr: float = 2.0
    exit_thr: float = 0.5
    cost_per_leg: float = 0.001  # 0.1% per leg
    execution_lag: int = 1  # trade at t+execution_lag after signal at t


def run_backtest(
    spread: pd.Series,
    zscore: pd.Series,
    params: BacktestParams | None = None,
) -> dict:
    """Run the pairs-trading backtest.

    spread: pd.Series indexed by trading date.
    zscore: pd.Series indexed on the same calendar as spread.
    """
    if params is None:
        params = BacktestParams()

    # Align
    df = pd.concat([spread.rename("spread"), zscore.rename("zscore")], axis=1)
    df = df.dropna()

    s = df["spread"].values
    z = df["zscore"].values
    dates = df.index
    n = len(df)

    position = 0           # +1 long spread, -1 short spread, 0 flat
    entry_spread = None    # spread at which current position was opened
    entry_date = None

    mtm_pnl = np.zeros(n)     # mark-to-market P&L each day
    trade_pnl = np.zeros(n)   # realised P&L on exit days
    position_series = np.zeros(n, dtype=int)

    trades: list[dict] = []

    # We look at z on day t to decide an action executed on day t + lag.
    # Simplest implementation: on each day t, the decision from day t-lag fires.
    lag = params.execution_lag

    for t in range(n):
        # Mark-to-market: if currently in a position, today's return from
        # yesterday's spread level
        if position != 0 and t > 0:
            mtm_pnl[t] = position * (s[t] - s[t - 1])

        position_series[t] = position

        # Look at the signal from `lag` days ago to decide today's action
        signal_t = t - lag
        if signal_t < 0:
            continue
        z_sig = z[signal_t]

        # ── Exit: |z| has reverted inside exit_thr ─────────────────────────
        if position != 0 and abs(z_sig) < params.exit_thr:
            exit_cost = params.cost_per_leg * abs(s[t])
            realised = position * (s[t] - entry_spread) - exit_cost
            # The entry-day cost was already subtracted at entry time, so
            # realised here is only the exit leg's cost. Record the total
            # net P&L for the trade (gross minus both entry + exit cost).
            gross = position * (s[t] - entry_spread)
            entry_cost = params.cost_per_leg * abs(entry_spread)
            net = gross - entry_cost - exit_cost
            trades.append({
                "entry_date": entry_date,
                "exit_date": dates[t],
                "side": "long_spread" if position == 1 else "short_spread",
                "entry_spread": entry_spread,
                "exit_spread": s[t],
                "gross_pnl": gross,
                "net_pnl": net,
                "cost": entry_cost + exit_cost,
                "holding_days": t - (dates.get_loc(entry_date)),
            })
            trade_pnl[t] = -exit_cost  # P&L impact of the exit leg itself
            position = 0
            entry_spread = None
            entry_date = None

        # ── Entry: |z| has crossed entry_thr and we're flat ─────────────────
        if position == 0:
            if z_sig > params.entry_thr:
                position = -1
                entry_spread = s[t]
                entry_date = dates[t]
                trade_pnl[t] = -params.cost_per_leg * abs(s[t])
            elif z_sig < -params.entry_thr:
                position = +1
                entry_spread = s[t]
                entry_date = dates[t]
                trade_pnl[t] = -params.cost_per_leg * abs(s[t])

    # total daily P&L = unrealised (mtm) + realised trade-event P&L
    total_daily = mtm_pnl + trade_pnl

    daily = pd.DataFrame(
        {
            "spread": s,
            "zscore": z,
            "position": position_series,
            "mtm_pnl": mtm_pnl,
            "trade_pnl": trade_pnl,
            "daily_pnl": total_daily,
            "cum_pnl": np.cumsum(total_daily),
        },
        index=dates,
    )

    trades_df = pd.DataFrame(trades)

    return {
        "daily": daily,
        "trades": trades_df,
        "params": asdict(params),
    }
