# Multi-Pair Analysis — Does the Framework Generalise?

A pairs-trading framework that "works" on a single pair could be lucky. Running the same pipeline on multiple pairs with no parameter tuning is the standard test of whether the framework actually does what it claims, or whether you've curve-fit to one dataset.

We test three pairs spanning two sectors. Spoiler: only one of them is actually cointegrated, the strategy correctly makes money on that one and loses money on the other two — and the ADF p-value predicts the result before the backtest is run. That's the framework working as designed.

## Pairs tested

| ID | Pair | Sector rationale |
|---|---|---|
| `HDFC_ICICI` | HDFC Bank / ICICI Bank | Two largest private-sector banks. Same regulatory regime, similar deposit/loan mix. Textbook pair. |
| `INFY_TCS` | Infosys / TCS | Largest two Indian IT services. Both export-driven, similar BFSI/retail client mix. Textbook pair on paper. |
| `AXIS_KOTAK` | Axis Bank / Kotak Mahindra Bank | Two private-sector banks at different scale and customer mix. Useful contrast to HDFC/ICICI. |

Same parameters across all three — no tuning per pair: static OLS hedge, 60-day z-score window, ±2σ entry / ±0.5σ exit, 0.1% per-leg cost, 1-day execution lag.

## Headline numbers

### Stable regime (Apr 2024 – Jan 2026)

| Pair | β | ADF p (full) | Cointegrated? | Sharpe | Trades | Win % | P&L (₹) |
|---|---|---|---|---|---|---|---|
| **HDFC / ICICI** | 0.71 | **0.020** | yes | **+1.00** | 6 | **83.3 %** | +93.19 |
| Infy / TCS | 0.29 | 0.180 | no | -0.84 | 4 | 0.0 % | -307.67 |
| Axis / Kotak | 0.84 | 0.236 | no | -0.66 | 4 | 25.0 % | -92.36 |

### Full dataset (Apr 2024 – Mar 2026)

| Pair | Sharpe | Trades | Win % | P&L (₹) |
|---|---|---|---|---|
| HDFC / ICICI | +0.57 | 7 | 71.4 % | +86.89 |
| Infy / TCS | -0.37 | 5 | 20.0 % | -110.84 |
| Axis / Kotak | -0.36 | 5 | 20.0 % | -99.52 |

## What this means

**The ADF cointegration test acts as a *gate* — and it's right.**

The Augmented Dickey-Fuller test asks "is the spread stationary?" — a precondition for it being mean-reverting and tradeable. With a p-value cutoff of 0.05:

- HDFC/ICICI passes (p = 0.020) → strategy makes money
- Infy/TCS fails (p = 0.180) → strategy loses money
- Axis/Kotak fails (p = 0.236) → strategy loses money

Three pairs, three predictions, three correct verdicts. The test isn't perfect (small samples, structural breaks) but on this dataset it cleanly separates tradeable from untradeable pairs *before* a single trade is simulated.

**Why Infy/TCS isn't cointegrated despite "looking like" they should be.**
Both companies serve overlapping clients in similar segments, but Infosys went through a CEO transition and management restructuring during 2024 that changed its growth trajectory relative to TCS. The two stocks share macro factors (USD-INR, US tech demand) but their *idiosyncratic* paths diverged enough that the spread itself drifts rather than mean-reverts. The ADF test catches this; visual intuition does not.

**Why this is the strongest possible interview result.**
A common red flag in pairs-trading projects is "I tried 5 pairs and they all worked". That's almost certainly cherry-picking or framework error. The honest result — "I tested 3 pairs, one worked, two didn't, and my pre-trade diagnostic correctly predicted which would work" — demonstrates:

1. The framework wasn't built around a single dataset.
2. The diagnostic test (ADF) is doing what it's supposed to do.
3. The author is willing to report null results, not just headline wins.
4. There's a clear, defensible answer to "how would you decide whether to trade a new pair?" — *run the cointegration test, and only trade pairs that pass.*

## Caveats

1. **Two years of daily data is on the short side for ADF.** With 5+ years the test is more powerful and we'd be more confident in the negative results for Infy/TCS and Axis/Kotak.
2. **Cointegration can be regime-dependent.** Two pairs that fail today may pass in a different macro regime, and vice versa (HDFC/ICICI itself partially broke down in early 2026 — see `docs/rolling_hedge_analysis.md`).
3. **Choice of test matters.** The Engle-Granger ADF test is the simplest; Johansen would be more rigorous for joint testing. We use ADF because it has a single interpretable p-value, which is the right level of complexity for this project.

## Visualisation

See `results/multi_pair_pnl.png` for cumulative P&L on all three pairs in both regimes. The visual contrast is immediate: HDFC/ICICI climbs steadily; the other two bleed money in a roughly linear way that looks like exactly what it is — a strategy with no edge.
