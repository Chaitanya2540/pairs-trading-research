# Parameter Sensitivity — Robustness of the Headline Sharpe

If the only configuration that produces a positive Sharpe is the exact one you put on your resume, you've overfit. This note shows that the chosen configuration sits inside a broad, consistently positive region of parameter space — the headline result is not a fluke of the grid.

## Setup

We sweep two parameters that drive the signal:

- **Entry threshold** (|z| at which we open a trade): 1.0 to 3.0 in 0.25 steps
- **Z-score rolling window** (days used to standardise the spread): 20, 30, 40, 60, 80, 100, 120

Everything else stays at the defaults from the headline backtest (static β, exit at |z| < 0.5, 0.1% per-leg cost, 1-day execution lag).

We compute the annualised Sharpe of the resulting strategy in each cell of the (entry × window) grid, on both the **stable regime** (Apr 2024 – Jan 2026) and the **full dataset** (Apr 2024 – Mar 2026). See `results/parameter_sensitivity.png` for the heatmap.

## Headline findings

**The chosen point (entry = 2.0, window = 60) is *not* the best cell in either grid — and that's intentional.** Picking the best-on-history cell is overfitting in disguise. Picking from a broad good region is robustness.

### Stable regime
- Chosen Sharpe: **1.00**
- 3×3 neighbourhood around the chosen point: range 0.47 – 1.95, **mean 1.01** (the headline number is the local average — no special trick is being played by parameter choice)
- 30 of 48 cells with ≥3 trades have **Sharpe > 1**
- All 48 cells with ≥3 trades have **positive Sharpe**

### Full dataset
- Chosen Sharpe: **0.57**
- 3×3 neighbourhood: range -0.25 – 1.72, mean **0.57**
- 23 of 49 cells with ≥3 trades have Sharpe > 1
- 46 of 49 cells with ≥3 trades have positive Sharpe

## Why entry = 2.0 even though it's not the best cell

The grid clearly shows that entry thresholds in the **1.0 – 1.5** band produce higher Sharpe (peak 2.39 on stable, 2.17 on full) than the standard ±2σ rule.

Three reasons we don't use that:

1. **Sample size, not signal.** Lower thresholds fire more trades, mostly on small z-score deviations that are well within the noise band of a rolling estimate. The "Sharpe 2.39" comes from many small wins on what is effectively reversion of estimation noise. The standard error on Sharpe falls with √n_trades — but only when the trades are statistically independent signals, which lower-threshold trades are not.

2. **The threshold has economic meaning.** ±2σ is the 5th percentile of the standard normal. It encodes the prior that "spreads outside their 5% tails are *unusually* wide and likely to revert". This is the textbook decision rule and any reviewer recognises it. A lower threshold needs to be re-justified from scratch.

3. **Out-of-sample stability.** The peak cells on this 2-year sample may not be the peak cells on a different 2-year sample — that's overfitting. The conservative cell at the literature standard is more likely to survive a regime change.

## Why window = 60

A 60-day rolling window standardises the spread over roughly the last 3 months of trading. The grid shows it sits in the most stable column — windows of 20–30 are too noisy (z-score itself becomes unstable), windows of 100+ start to mute genuine mean-reversion (the "rolling" is too slow to react). Window = 60 is the standard mid-range choice and the grid confirms it's well inside the robust region.

## Grid visualisation

See `results/parameter_sensitivity.png` for a side-by-side heatmap. The chosen cell is outlined in blue. Note the broad green plateau in both grids — robustness is visible at a glance.

The full numerical grid is in `results/parameter_grid.json` for anyone who wants to dig in.
