# Headline Results — HDFC / ICICI Pairs Trading

All results use **static hedge ratio β = 0.7194**, **z-score window = 60 days**,
**entry ±2σ / exit ±0.5σ**, **0.1 % per-leg transaction cost**, **1-day execution lag**.
See `docs/rolling_hedge_analysis.md` for why static β is the right choice on this dataset.

## Stable regime (Apr 2024 – Jan 2026, before HDFC governance event)

| Metric | Value |
|---|---|
| Trading days | 397 |
| Completed trades | 6 |
| Win rate | 83.3 % |
| Total net P&L | ₹93.47 (per unit spread) |
| **Sharpe Ratio** | **1.00** |
| Max drawdown | -₹65.69 (-52.0 % of peak) |
| Profit factor | 5.53× |

## Full dataset (Apr 2024 – Mar 2026, includes governance event)

| Metric | Value |
|---|---|
| Trading days | 437 |
| Completed trades | 7 |
| Win rate | 71.4 % |
| Total net P&L | ₹87.41 |
| Sharpe Ratio | 0.57 |
| Max drawdown | -₹75.66 (-57.4 % of peak) |
| Profit factor | 4.40× |

## Regime delta

The strategy's Sharpe **almost halves** (1.00 → 0.57) once the post-governance
period is included. The ADF p-value on the spread also rises from **0.0012 → 0.0182**,
confirming that the cointegration relationship has weakened. This is the project's
central narrative: the strategy worked exactly as designed until the economic
relationship that justified it broke down — model failure can be diagnosed, not
just suffered.
