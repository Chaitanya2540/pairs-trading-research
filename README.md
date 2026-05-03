# Pairs Trading Research — Indian Equities

Statistical-arbitrage research project. Builds a mean-reversion strategy on cointegrated Indian equity pairs, with a regime-aware backtest, an honest treatment of look-ahead and transaction costs, a parameter-sensitivity check, a multi-pair generalisation test, and an interactive Streamlit dashboard.

> **Headline result.** On the **HDFC Bank / ICICI Bank** pair, stable regime (Apr 2024 – Jan 2026), the strategy delivers an **annualised Sharpe of 1.00** with an **83.3% win rate on 6 trades** and a max drawdown of -52% of peak — net of 0.1% per-leg transaction costs and a 1-day execution lag.

| | Stable regime (Apr 24 – Jan 26) | Full data (Apr 24 – Mar 26) |
|---|---|---|
| ADF p-value (spread stationarity) | 0.0013 | 0.0195 |
| Sharpe Ratio | **1.00** | 0.57 |
| Win rate | 83.3 % | 71.4 % |
| Trades | 6 | 7 |
| Max drawdown (% of peak) | −52.0 % | −55.1 % |
| Profit factor | 5.5 × | 4.4 × |
| Total P&L (₹ per unit spread) | +93.2 | +86.9 |

The Sharpe almost halves once the post-Feb 2026 period (after the HDFC governance event) is included. The ADF p-value also rises by an order of magnitude. **Both diagnostics flag the same regime break, before P&L tells you about it.** That's the project's central narrative — model failure is *diagnosable*, not just suffered.

---

## Demo

**Live Streamlit app:** _coming soon — link will go here once deployed_
**Walkthrough notebook:** [`notebooks/analysis.ipynb`](notebooks/analysis.ipynb)

![Multi-pair P&L comparison](results/multi_pair_pnl.png)

The chart above is from the **multi-pair generalisation test**. The framework was run identically on HDFC/ICICI, Infosys/TCS, and Axis/Kotak. Only HDFC/ICICI is statistically cointegrated (ADF p < 0.05), and only HDFC/ICICI makes money — the other two bleed in roughly straight lines, exactly as you'd expect from a strategy with no edge. **The ADF cointegration test correctly predicts which pair the strategy will work on, before any backtest is run.**

---

## What's in here

```
pairs-trading-research/
├── data/raw/                   daily NSE close prices (CSV per symbol)
├── src/pairs/                  importable Python package
│   ├── data.py                   loaders + pair registry
│   ├── signals.py                static + rolling hedge, z-score
│   ├── backtest.py               trade engine, look-ahead-free, cost-aware
│   ├── metrics.py                Sharpe, max drawdown, profit factor
│   └── pipeline.py               run_pipeline(pair_id, params) → results
├── app/streamlit_app.py        interactive dashboard
├── tests/test_pipeline.py      pytest regression suite (13 tests, ~1.5s)
├── scripts/fetch_data.py       refresh CSVs from Yahoo Finance
├── notebooks/                  walkthrough (jupyter)
├── docs/
│   ├── rolling_hedge_analysis.md   why static β is the headline; what we found with rolling
│   ├── parameter_sensitivity.md    why the chosen (entry, window) is robust, not fitted
│   ├── multi_pair_analysis.md      generalisation across 3 pairs and the ADF gating story
│   └── interview_qa.md             predictable interview questions, with answers
└── results/                    saved charts + JSON summaries
```

---

## How it works (in one paragraph)

For two prices `leg1, leg2`, fit `leg1 = α + β · leg2 + ε` to define a hedge ratio β. The **spread** `s_t = leg1_t − β · leg2_t` is the portfolio's value relative to its hedge. If `s_t` is stationary (ADF p-value < 0.05), it mean-reverts — extreme deviations are likely to revert, which is the trading edge. Standardise `s_t` on a rolling 60-day window to get a z-score; **enter** when `|z| > 2.0` (long the spread if z<0, short if z>0), **exit** when `|z| < 0.5`. Charge **0.1% per leg** in transaction costs, observe the signal at close-of-day t but execute at close-of-day t+1 (no look-ahead).

---

## Methodology — design choices that survive an interview

Each of these is a design decision a quant interviewer is likely to challenge. The full reasoning lives in the linked docs.

| Choice | What I did | Why this isn't a red flag |
|---|---|---|
| Static vs rolling β | **Static**, fitted on the full sample | Tested rolling β with windows from 30 to 252 days. Short windows give noisy β (range -0.7 to +1.1, economically nonsensical). Only at W=252 does β stabilise, but that burns 312 days of warmup → only 2-3 trades remain on 2 years of data. With β stable around 0.71, static is defensible *and* statistically more reliable. [Full sweep](docs/rolling_hedge_analysis.md). |
| Entry threshold | **\|z\| > 2.0** | Lower thresholds (1.0–1.5) actually score higher Sharpe on the grid, but trade more often on small-magnitude signals that are within rolling-estimate noise. ±2σ is the literature standard (5th percentile of standard normal) and any reviewer recognises it. The chosen point sits in a 3×3 neighbourhood whose mean Sharpe is 1.01 — the headline isn't a lucky cell. [Full grid](docs/parameter_sensitivity.md). |
| Z-score window | **60 days** | ~3 months of trading. Sits in the most stable column on the sensitivity grid. Shorter (20-30d) makes the z-score itself unstable; longer (100d+) mutes genuine reversion. |
| Look-ahead | **execution_lag = 1** (signal at t → trade at close of t+1) | Most undergrad backtests cheat here — they observe today's close and trade today's close. Real trading can't. Adding the lag costs ~₹5-10 per trade × 6 trades on this dataset, but it's the difference between an interview-survivable result and a fragile one. |
| Transaction costs | **0.1% per leg** (entry + exit, both legs of the pair) | Realistic for retail trading on NSE (brokerage + STT + exchange fees ≈ 8–12 bps round-trip). Most "great" strategies don't survive costs. |
| Position sizing | Unit position in the spread | Simplest possible. Real implementation would vol-target. Documented as a known limitation. |
| Pair selection | Manual, with sectoral rationale per pair | Real fund would automate candidate-pair screening (cluster on sector + run ADF on every pair within cluster). Out of scope for v1. |

---

## Run it locally

```bash
git clone <this-repo> pairs-trading-research
cd pairs-trading-research

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# (Optional) refresh prices from Yahoo
python scripts/fetch_data.py

# Run the regression test suite
pytest                                    # 13 tests, ~1.5s

# Launch the interactive dashboard
streamlit run app/streamlit_app.py
```

---

## Reproducible benchmark numbers

Pinned in `tests/test_pipeline.py`. Anyone refactoring should keep these green:

```
HDFC/ICICI, Stable regime  : Sharpe 1.00, 6 trades, win 83.3%, P&L ₹93.2, max DD -52%
HDFC/ICICI, Full dataset   : Sharpe 0.57, 7 trades, win 71.4%, P&L ₹86.9, max DD -55%
INFY/TCS,    Stable regime : Sharpe -0.84, 4 trades — ADF p=0.33 (not cointegrated, expected to lose)
AXIS/KOTAK,  Stable regime : Sharpe -0.66, 4 trades — ADF p=0.45 (not cointegrated, expected to lose)
```

---

## What this project deliberately doesn't do

- Doesn't claim a Sharpe above 1.5. The honest headline is 1.00; cells in the heatmap that score higher trade too often or use too short a hedge window to be defensible.
- Doesn't run on live data or paper-trade. The pipeline is offline-batch — the Streamlit app re-runs the backtest from the historical CSVs every time you change a slider.
- Doesn't use ML for signal generation. The decision rule is `|z| > 2.0` — interpretable, debuggable, defensible. ML for pairs is a follow-up project.
- Doesn't model market impact, execution shortfall, or adverse selection. Single-spread positions on India's two most liquid bank stocks make this approximation defensible at small size. It would not be defensible at a fund's actual size.

---

## Resume bullet

> **Pairs Trading Research — Indian Equities** ([code](https://github.com/), [demo](https://streamlit.io/))
> Built a mean-reversion pairs-trading framework on cointegrated NSE stocks: rolling-OLS hedge with parameter-sensitivity validation, z-score signal with realistic transaction costs and 1-day execution lag, regime-aware backtest, ADF cointegration gating, pytest regression suite, interactive Streamlit dashboard. Headline: **Sharpe 1.0 on the stable HDFC/ICICI regime (6 trades, 83% win rate)**, with model failure correctly diagnosed by ADF when applied to non-cointegrated pairs.

---

Built by **Chaitanya** · 2026 · See `docs/interview_qa.md` for a deeper Q&A walkthrough.
