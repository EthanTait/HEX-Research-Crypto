# Evaluation protocol

Shared by every idea. It exists because of two risks we flagged in ideation:

1. **Event trap:** a few crashes or squeezes produce most of the "signal", and the result is really about three days.
2. **Undefined success:** without a metric fixed in advance, the thesis drifts to whatever the data happened to show.

So the rule is: **each idea states its metrics in the table at the bottom before we look at out-of-sample results.** Changing them afterwards goes in `DECISIONS.md` with a reason.

## 1. Sample discipline

- **Walk-forward (sliding) in-sample / out-of-sample windows**, as in the Lecture 4 signal-optimization slide: fit on IS, evaluate on the next OOS block, slide forward. No shuffled cross-validation, because time series leak.
- A **final holdout** (e.g. the last 2-3 weeks) is left untouched until the method is frozen. We look at it once.
- Hyperparameters (windows, half-lives, thresholds) are chosen on IS only. These are the IS/OOS rules from MSQF Quant Methods.

## 2. Primary metric: per-day, rank-based, vol-normalized

- Forecast target: forward return over horizon h **divided by current EWMA vol**, so high-vol days don't dominate by scale alone.
- Metric: **rank IC** (Spearman correlation of signal against target) **computed per day**.
- Report: **median daily IC**, **% of days with IC > 0**, and the IC distribution, not only the pooled number. One crash day then counts as one observation.

## 3. Robustness checks (run for every headline number)

| Check | Why |
|---|---|
| Drop the top 5 days by realized vol, re-run | Is it just an event effect? |
| Block bootstrap by day for CIs | Intraday observations are not independent |
| Newey-West standard errors when forward windows overlap | Lecture 4: overlapping 5-min windows produce spurious autocorrelation |
| Split by regime (high/low vol, weekday/weekend, Asia/EU/US hours) | Is it stable, or does one regime drive it? |
| Winsorize or cbrt-transform features (Lecture 4 "reducing tails") | Keeps correlations from being driven by the tails |
| Placebo / surrogate null (e.g. circular time-shift of one series) | Separates real structure from artefacts like autocorrelation, stale prices or tick size |

## 4. Forecast comparison

Any claim that "model A beats model B" uses a **Diebold-Mariano test** on OOS loss differentials, not just two IC numbers side by side.

For probability or classification forecasts, check **calibration**: predicted versus realized hit rates by bucket, with Kupiec/Christoffersen-style tests (the VaR backtesting framework from MSQF Risk Management, applied to signal forecasts).

## 5. Economic value (tiered, reported honestly)

1. **Mid-to-mid PnL:** the Lecture 4 method (position proportional to signal, cumulative forward return).
2. **After costs:** spread crossing plus taker fees at a stated fee tier.
3. **After latency:** repeat 2 with decision latency L in {0, 10ms, 100ms, 1s}. Lecture 4 already shows a 1-minute entry delay degrading PnL.
4. Sharpe, drawdown, turnover, number of trades.

A result that dies at step 2 or 3 is still a result: "the effect is statistically real but not harvestable at retail fees and latency" is a legitimate conclusion.

## 5b. Hedged spread specifics (2026-11-05)

- Position: long follower j, short beta_j * BTC notional (or the reverse), size proportional to the forecast, held for h bars (Lecture 5 backtest).
- Costs on **both legs**: taker fee (about 5 bps per side) plus half the spread on each leg at entry and exit. State the fee tier.
- Stages, each one a line on the cumulative PnL chart: mid-to-mid -> fees + spread -> one-bar delay -> funding (later).
- Long and short legs reported separately (Lecture 9).
- Sharpe annualized with 525,600 minutes per year (crypto trades 24/7).

## 6. Pre-registration (filled 2026-11-05, before any OOS result)

| Item | Value |
|---|---|
| Target variable and horizon(s) | y_j(t,h): forward BTC-hedged spread of follower j, vol-scaled (`THESIS.md`). h = 5 primary; 1, 15 reported |
| Primary metric | Median daily rank IC (Spearman) on the 2024 walk-forward |
| Judging metric | Cumulative net PnL of the hedged position, costs on both legs |
| Benchmark it must beat | (1) best standalone feature (chosen on 2023), (2) static "BTC leads" forecast, (3) zero |
| Significance test | Day-block bootstrap CI on median daily IC; Diebold-Mariano vs the static baseline |
| Robustness checks that must pass | Drop top 5 vol days; per-follower results; weekday vs weekend; circular time-shift placebo |
| What counts as a null result | Lead concentrated at lag 0, or combined forecast not better than the best feature beyond 1 bootstrap s.e. |
| Holdout period | 2025-01-01 to 2025-11-30, opened once, logged in `experiments/registry.jsonl` |
