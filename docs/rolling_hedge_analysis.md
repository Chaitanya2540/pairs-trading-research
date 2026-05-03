# Hedge-Ratio Choice: Static vs Rolling

This note documents why the headline backtest in this project uses a **static OLS hedge ratio**, and what we found when we compared it against rolling alternatives. It's the most-poked-at design choice in any pairs-trading project, so the analysis is laid out in full.

## The look-ahead concern

A static hedge ratio fits a single β to the entire sample:

```
HDFC_t = α + β · ICICI_t + ε_t   for t = 1, …, T
```

then applies that β to construct the spread `s_t = HDFC_t - β · ICICI_t` for *every* day, including the very first one. By construction, β was chosen to minimise the squared residuals on data you would not have observed at the time. The spread series therefore looks "cleaner" — more stationary, with smaller residuals — than a real-time trader would have seen.

The textbook fix is a **rolling-window hedge ratio**: at each date *t*, fit β_t on the trailing W days only, and use β_t to construct s_t. Information on day *t* is restricted to days ≤ t — no look-ahead.

## What we actually saw when we tried it

We swept the rolling window length from 30 to 252 days, keeping the z-score window fixed at 60 days. Results on the full Apr 2024 – Mar 2026 sample:

| Hedge window | β min | β max | β std | Trades | Sharpe | Total P&L (₹) |
|---|---|---|---|---|---|---|
| 30 | -0.70 | 1.13 | 0.35 | 7 | 2.63 | 2,379 |
| 60 | -0.52 | 0.96 | 0.35 | 5 | -1.40 | -166 |
| 90 | -0.57 | 0.95 | 0.34 | 5 | -2.02 | -408 |
| 120 | -0.36 | 0.95 | 0.29 | 2 | 0.87 | -52 |
| 180 | -0.00 | 0.77 | 0.21 | 3 | -4.87 | -640 |
| **252** | **0.50** | **0.70** | **0.05** | **3** | **1.74** | **153** |
| Static (full sample) | — | — | 0.71 (point) | 7 | 0.57 | 87 |

Two patterns jump out:

**1. Short windows produce nonsensical β values.**
At W = 30 the slope ranges from -0.70 to +1.13. A negative β means the regression is briefly claiming HDFC and ICICI move in opposite directions — economically incoherent for two large Indian banks with the same regulatory and macro exposure. The "Sharpe 2.63" result at W = 30 is therefore not a real signal; it's mean-reversion in a hedge that has no economic content. This is overfitting in slow motion: noisy β → noisy spread → spurious z-score crossings.

**2. Only at W ≈ 252 does β become economically reasonable.**
The 252-day rolling β stabilises in the [0.50, 0.70] band with a standard deviation of 0.05 — close to the full-sample static β of 0.71. This is the only configuration where the rolling estimate is doing what it's supposed to do (capturing slow drift in the relationship) rather than amplifying noise.

## The data-budget problem

Once you commit to a 252-day hedge window, the cost is severe on a 2-year dataset:

- 252 days lost to hedge warmup
- + 60 more days lost to z-score warmup
- = first tradeable signal arrives on day 312 of 496
- → only **184 trading days** in which a signal can fire on the full sample
- → only **128 trading days** on the stable regime (which ends day ≈ 440)

Result: **3 completed trades on the full sample, 2 trades on the stable regime.** Whatever Sharpe you compute on that small a sample carries a standard error roughly proportional to 1/√n_trades. A Sharpe of 1.74 on 3 trades is not meaningfully different from the static Sharpe of 0.57 on 7 trades — both confidence intervals overlap zero.

## Why the static β is defensible here

1. **The rolling W=252 sweep confirms β is roughly constant.** The cointegration relationship genuinely doesn't drift much over 2 years; the rolling estimate hovers near the full-sample value. This is what makes HDFC/ICICI a textbook pair.
2. **The ADF test on the full sample shows cointegration (p = 0.018).** A single β is therefore a defensible summary of the long-run relationship.
3. **The rolling alternatives that produce stable β use up so much of the sample that the remaining backtest is statistically empty.** Trading 2–3 times in 2 years tells you nothing about edge.
4. **The static β can be challenged on look-ahead — but the challenge is bounded.** Because β is stable, the look-ahead bias from using a future-informed β is small (the spread you would have constructed in real-time using only past data would have looked very similar).

## Recommendation, and the headline result

For this dataset, **report static β as the headline backtest, with this analysis attached as the justification.**

Headline results, stable regime (Apr 2024 – Jan 2026), static β = 0.7194:

- **Sharpe 1.00**, win rate **83.3 %** on **6 trades**, profit factor **5.5×**, max drawdown **−52 % of peak (−₹66)**.
- All P&L numbers are net of 0.1 % per-leg transaction costs and a 1-day execution lag (signal at *t* → trade at close of *t+1*).

## What would make rolling β work

Rolling β would be the right call given:

1. **More history.** With 5+ years of data you can afford a 252-day hedge window and still get 30+ trades.
2. **A pair with genuine relationship drift.** HDFC/ICICI is too stable for rolling β to add value. A pair where the cointegration coefficient is known to evolve (e.g. cross-asset or cross-currency pairs) would benefit.
3. **A Kalman filter instead of rolling OLS.** Kalman is the principled way to track a slowly-drifting parameter without burning a 252-day window — it produces a posterior estimate of β that updates one observation at a time. Out of scope for the v1 of this project but the natural next step.

The pipeline already supports rolling mode (`PipelineParams(hedge_mode="rolling", hedge_window=W)`). The Streamlit dashboard exposes both modes so a reader can verify the analysis above.
