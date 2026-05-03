"""
End-to-end pipeline: pair id + parameters → full results dict.

This is the single entry point used by the notebook, the Streamlit app, and
the regression tests. Keeping it centralised means one place to change the
contract and everything downstream follows.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal

import pandas as pd

from . import data, signals, backtest, metrics


HedgeMode = Literal["static", "rolling"]


@dataclass(frozen=True)
class PipelineParams:
    window: int = 60
    entry_thr: float = 2.0
    exit_thr: float = 0.5
    cost_per_leg: float = 0.001
    hedge_mode: HedgeMode = "static"
    hedge_window: int = 60  # only used when hedge_mode == "rolling"
    execution_lag: int = 1
    start: str | None = None
    end: str | None = None  # inclusive


def run_pipeline(pair_id: str, params: PipelineParams | None = None) -> dict:
    """Run the full pipeline on a registered pair.

    Returns a dict with keys:
      pair, leg1, leg2, params, hedge, spread, zscore, daily, trades, summary
    """
    if params is None:
        params = PipelineParams()

    leg1, leg2, pair = data.load_pair(pair_id)

    # Optional date filter
    if params.start is not None:
        start = pd.Timestamp(params.start)
        leg1 = leg1.loc[leg1.index >= start]
        leg2 = leg2.loc[leg2.index >= start]
    if params.end is not None:
        end = pd.Timestamp(params.end)
        leg1 = leg1.loc[leg1.index <= end]
        leg2 = leg2.loc[leg2.index <= end]

    # Hedge ratio
    if params.hedge_mode == "static":
        beta = signals.static_hedge_ratio(leg1, leg2)
    else:
        beta = signals.rolling_hedge_ratio(leg1, leg2, window=params.hedge_window)

    spread = signals.build_spread(leg1, leg2, beta)
    z = signals.zscore(spread, window=params.window)

    bt = backtest.run_backtest(
        spread=spread,
        zscore=z,
        params=backtest.BacktestParams(
            entry_thr=params.entry_thr,
            exit_thr=params.exit_thr,
            cost_per_leg=params.cost_per_leg,
            execution_lag=params.execution_lag,
        ),
    )

    summary = metrics.summarise(bt["daily"], bt["trades"])

    return {
        "pair": pair,
        "leg1": leg1,
        "leg2": leg2,
        "params": asdict(params),
        "hedge": beta,
        "spread": spread,
        "zscore": z,
        "daily": bt["daily"],
        "trades": bt["trades"],
        "summary": summary,
    }
