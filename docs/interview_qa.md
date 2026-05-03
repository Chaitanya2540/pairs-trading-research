# Interview Q&A — Pairs Trading Project

Predictable questions a quant interviewer will ask about this project, with the answer you should give. Practise these so the response is fluent — but more importantly, understand *why* the answer is what it is, because interviewers will follow up with "and what if I changed X?"

The questions are loosely ordered by depth: the first half are basic-correctness checks ("does this person actually understand pairs trading?"), the second half are design-judgement checks ("would I trust this person to make these calls on a live book?").

---

## A. Strategy fundamentals

### A1. What is pairs trading and why should it work?

Pairs trading is a **market-neutral statistical-arbitrage strategy**. You take two assets whose prices are *cointegrated* — meaning a linear combination of them (the "spread") is stationary even though each price is non-stationary on its own. When the spread deviates significantly from its mean, you bet on reversion: long the cheap leg, short the expensive leg, in proportion to the hedge ratio.

It works for two reasons:
1. The trade is hedged: if both stocks fall together because of a market move, you make on one leg and lose on the other. P&L comes from the *relative* movement.
2. Cointegration implies that random shocks get arbitraged away — institutional money has historically kept these pairs from drifting too far apart.

### A2. What's the difference between correlation and cointegration?

Correlation is about *short-term co-movement*: do leg1 and leg2's daily returns tend to move in the same direction? Cointegration is about *long-term equilibrium*: even if both prices wander, does some linear combination of them stay around a stable mean?

You can have:
- **High correlation, no cointegration**: two stocks both going up forever, returns positively correlated, but the spread between them drifts indefinitely. No reversion → no trade.
- **Low correlation, cointegration**: two stocks that move idiosyncratically day-to-day but whose ratio is anchored by some economic relationship. Bad for trend-following, perfect for pairs.

For pairs trading, correlation tells you the hedge will *work* (returns are coupled). Cointegration tells you the spread will *revert* (the trade will close out). You need both, but cointegration is the harder condition.

### A3. Why HDFC and ICICI specifically?

Both are large private-sector Indian banks with similar deposit-side and asset-side mix, both regulated by the RBI under the same framework, both heavily exposed to the same Indian macro variables (rates, NPL cycle, retail credit). If a bad-news shock hits one (e.g. a rate cut, a budget announcement), the other gets the same shock — so their *idiosyncratic* dispersion mean-reverts even when the level wanders.

I tested this empirically: ADF p-value on the HDFC − 0.71×ICICI spread is 0.020 over the full sample, and 0.001 on the stable regime. Both well below the 0.05 cutoff — the spread is stationary, the precondition for trading is met.

### A4. Walk me through one trade end-to-end.

Pick the largest one. On day t, the rolling 60-day mean of the HDFC−0.71×ICICI spread is, say, ₹100, with rolling std ₹5. Today's spread is ₹113 → z = (113-100)/5 = +2.6. That crosses my +2.0 threshold so I **short the spread**: short 1 share of HDFC, long 0.71 shares of ICICI. I observe this signal at today's close but execute at tomorrow's close (1-day lag — I can't trade today's close at today's close). I pay 0.1% × tomorrow's spread value as entry transaction cost, on each leg.

Each subsequent day, I mark-to-market the position: P&L_today = -1 × (spread_today − spread_yesterday). The position bleeds when the spread widens, makes when it narrows.

When the rolling z-score drops back inside ±0.5 (say spread reverts to ₹103), I exit at that day's close, pay another 0.1% × spread cost on each leg. Trade complete. Realised P&L is `(113 − 103) × 1 - costs`, i.e. ~₹9.8 minus ~₹0.4 in costs = +₹9.4 net per unit spread.

---

## B. Risk and look-ahead

### B1. How did you handle look-ahead bias?

Two places it hides:
1. **Trade execution**: I observe the z-score on day t's close, but trade at day t+1's close (`execution_lag = 1` in the engine). You cannot in real life observe today's close and trade today's close — the data only exists at the moment trading ends.
2. **Hedge ratio**: this is the bigger one. A static OLS β fitted on the full 2-year sample uses information from 2026 to construct the spread on day 1 in 2024. Strictly speaking, that's look-ahead. I tested rolling β with windows from 30 to 252 days; the only stable choice was W=252, which burns enough history that only 2-3 trades fire. With static β stable around 0.71 and rolling-W=252 confirming β doesn't drift much, static is statistically more reliable on this dataset. The full analysis is in `docs/rolling_hedge_analysis.md`.

The conservative honest position: I use static β as the headline, and I have the rolling sweep documented to defend the choice if challenged.

### B2. What's your max drawdown and what does it mean?

On the stable regime, max drawdown is **−₹66 absolute, or −52% of the running peak**. That means at the worst point, the cumulative P&L was 52% below the highest cumulative P&L it had previously achieved.

The number is large in percentage terms because the running peak itself is small (a few trades into the strategy, peak P&L is ~₹130). For position-sizing context, this would translate to a much smaller percentage-of-capital drawdown if I were vol-targeting position size — a real implementation would size each spread position based on rolling spread volatility, not a unit position as I've used.

### B3. What's the worst-case loss on a single trade, and why should I trust your strategy isn't going to blow up?

The worst single-trade loss in the headline backtest is ~₹21 vs ~₹40 best — so loss magnitude is roughly half of win magnitude, which is healthy asymmetry for a mean-reversion strategy.

The blow-up risk for pairs trading isn't typically a single bad trade — it's a *regime change* where the cointegrating relationship breaks down. That's exactly what happened to HDFC/ICICI in Feb 2026 (governance event). My strategy held a long-HDFC position when HDFC kept falling, and the loss kept compounding. The honest answer: this is the dominant risk, and the way to manage it is (a) a stop-loss on the trade, (b) re-test cointegration on the rolling window and exit if ADF p-value rises above 0.10. I haven't implemented either in v1 — both are obvious next steps.

---

## C. Parameter and design choices

### C1. Why ±2σ entry? Why not ±1.5 or ±3?

±2σ is the 5th percentile of the standard normal — encoding "the spread is in its outer 5% tail, so a reversion is more likely than not". It's the literature-standard threshold and any reviewer recognises it.

I checked the alternatives. On my (entry × window) sensitivity grid, **lower thresholds (1.0–1.5) score higher Sharpe** on this dataset (peak 2.4 on stable). I did not adopt them because:
- Lower thresholds fire many trades on small z-score deviations that are within the noise of the rolling estimate. The "Sharpe 2.4" result comes from many small wins on what's essentially mean-reversion of estimation noise, not signal.
- The standard error of a Sharpe estimate falls only when trades are statistically independent signals. Lower-threshold trades are more correlated.
- ±2σ is what an interviewer expects to see; deviating from it requires a separate justification.

The chosen cell sits in a 3×3 neighbourhood with mean Sharpe 1.01 — the headline result is not a lucky cell on the grid.

### C2. Why a 60-day rolling window?

~3 months of trading days. It sits in the most stable column on my sensitivity grid. Shorter (20-30d) makes the z-score itself unstable — the rolling std becomes too small in low-vol periods, generating spurious z-score crossings. Longer (100d+) mutes genuine reversion — the rolling mean is too slow to update when the spread's centre actually drifts.

### C3. What if I made you change the cost from 0.1% to 0.3% per leg?

The strategy still makes money but the Sharpe drops materially. On the stable regime, raising cost from 0.1% to 0.3% per leg (so 0.6% round-trip per trade × 4 legs = 2.4% per trade in costs) would consume most of the per-trade edge. Strategies like this are very cost-sensitive — they have to be, because mean-reversion edges are small in basis-point terms. Bigger funds get cheaper costs, which is part of why this kind of strategy is more profitable for institutions than retail.

The Streamlit app exposes the cost slider so you can see this directly.

### C4. Could you use a Kalman filter instead of rolling OLS?

Yes, and it's the right next step. The Kalman filter treats β as a hidden state that evolves as a slow random walk; the observation equation is the OLS regression. The benefit: you get a posterior estimate of β that updates one observation at a time, so you don't burn a 252-day window on warmup. You also get an explicit estimate of *how confident* the filter is in the current β.

It's out of scope for v1 because (a) it adds two more parameters (state noise, observation noise) that need to be tuned without overfitting, (b) on a 2-year sample where β is roughly constant, the Kalman approach degenerates toward the static estimate anyway. With 5+ years of data and a pair where the relationship genuinely drifts, Kalman is the right tool.

---

## D. Generalisation and validation

### D1. Does the strategy work on other pairs?

That's the multi-pair analysis. I ran the same pipeline (no parameter tuning per pair) on three pairs:
- **HDFC / ICICI**: ADF p = 0.020 → Sharpe +1.00 on stable regime
- **Infosys / TCS**: ADF p = 0.180 → Sharpe -0.84 on stable regime
- **Axis / Kotak**: ADF p = 0.236 → Sharpe -0.66 on stable regime

Three pairs, three predictions, three correct verdicts: **the ADF cointegration test correctly predicts which pair the strategy makes money on**, before any backtest is run.

This is actually the strongest result in the project. A red flag in pairs-trading work is "I tried 5 pairs and they all worked" — that's almost certainly cherry-picking. The honest result — one pair works, two don't, my pre-trade diagnostic correctly predicted which — demonstrates that the framework isn't built around a single dataset.

### D2. Why doesn't Infy / TCS work despite both being large IT services?

They share macro factors (USD-INR, US tech demand, BFSI client exposure) so their *correlation* is high. But Infosys went through CEO transition and management restructuring during 2024 that changed its growth trajectory relative to TCS. The two stocks' idiosyncratic paths diverged enough that the spread itself drifts rather than mean-reverts. Visual inspection alone wouldn't catch this — the ADF test does.

### D3. How would you scale this to many pairs?

Three layers:
1. **Candidate generation**: cluster stocks by sector / fundamentals → all within-cluster pairs are candidates.
2. **Cointegration screening**: run ADF (or Johansen for multi-asset baskets) on every candidate spread, on a rolling window. Keep pairs that pass.
3. **Position sizing**: vol-target each spread's exposure so that a portfolio of 10–20 pairs has a target portfolio volatility (e.g. 10% annualised). Diversification across uncorrelated spreads is what makes a real pairs-trading book viable.

I haven't implemented any of this in v1 — the project is a *framework*, not a portfolio.

---

## E. Honest limitations

### E1. What's the biggest weakness of this project?

Three things, in order of how likely they are to come up:

1. **Sample size.** 2 years of daily data, 6–7 trades. Sharpe estimates carry meaningful sampling error — the 95% CI on a Sharpe of 1.0 from 6 trades is roughly [0, 2.0]. The headline number is the point estimate; I can't claim statistical significance from this sample alone.
2. **Pair selection is manual.** A real fund automates candidate-pair screening. I picked HDFC/ICICI because it's the textbook Indian pair, then tested 2 more for generalisation. That selection was guided by the same human intuition that I'm trying to test. Best evidence against cherry-picking is the multi-pair result showing the *negative* cases.
3. **No execution model.** I assume I can transact at the daily close. In reality there's bid-ask spread, market impact, and adverse selection — particularly on the short side where shares-to-borrow may be unavailable for the right size.

### E2. What would you do next?

In rough priority:
1. **Stop-loss / time-stop**: kill trades that don't revert within N days, or that reach a loss of M× the entry threshold. Both bound the regime-change risk.
2. **Kalman-filter hedge ratio.** Same role as rolling β, doesn't burn 252 days of warmup.
3. **Multi-pair portfolio.** Vol-target across 5–10 cointegrated pairs.
4. **Live paper-trade.** Walk-forward in time on out-of-sample data — a backtest that goes well doesn't prove a live edge, only a paper-trade does.
5. **More rigorous cointegration test.** Engle-Granger ADF is the simplest. Johansen is multi-asset and gives you confidence intervals on β. Worth doing for the 5-pair portfolio version.

---

## F. The "would I hire this person" questions

### F1. Why are you interested in quant?

(Have a personal answer ready. The truth — that you're transitioning from another field, that you find the combination of probability theory + market intuition + engineering compelling, that you have a portfolio of work to back up the interest — is much better than a stock answer.)

### F2. What would you have done differently if you'd known what you know now?

I would have started with the multi-pair test earlier. I spent a lot of effort on parameter sensitivity within HDFC/ICICI before testing whether the framework even generalised. Once I ran it on Infy/TCS and Axis/Kotak, the *most defensible* result — that ADF correctly gates strategy success — was the multi-pair one, not the single-pair Sharpe number. Lesson: always test generalisation early, single-instance results are easy to overfit to in your own head.

I'd also have implemented a stop-loss before reporting the regime-change drawdown. The "open long HDFC" position that bled the strategy through Feb-Mar 2026 should have been closed by a 30-day time-stop, and a v2 of this project would do that.

### F3. What did you learn doing this?

Three things, all unrelated to pairs trading specifically:

1. **The *quality* of a research result is in the diagnostics, not the headline number.** A Sharpe of 1.0 means nothing without confidence intervals, regime analysis, parameter robustness, and out-of-sample generalisation. The first time my backtest hit Sharpe 1.74 with a rolling β on 3 trades, my instinct was "great, ship it" — and the honest second look was "wait, that's 3 trades, the standard error swamps the estimate". Learning to ignore "good" results until they survive their own diagnostics is the actual skill.

2. **Look-ahead bias is sneaky.** It hides in places that read as innocuous — using a hedge ratio that knows the future, exiting at the same close where you observed the signal. Most undergrad backtests cheat in at least one of these places.

3. **Honest null results are stronger than fragile positive ones.** A framework that says "this pair will work, that pair won't" — and is right — is more impressive than one that claims to work on every pair. The Infy/TCS and Axis/Kotak losses are the most credible thing in this project, not a weakness to hide.
