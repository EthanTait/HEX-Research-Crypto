# Milestone 1: BTC-hedged spread forecast for alt perps

**HEX Research**: Ethan Tait, Hank Rugg. Fordham MSQF, Crypto Algorithmic Trading. Submitted 2026-11-09.

Everything in this document is produced by a script in `python/scripts/` from the repository `HEX-Research-Crypto`, at git commit `2c0bc98` plus the files listed in section 8. Every run that produced a number is one line in `experiments/registry.jsonl`.

**Figures:** this markdown names each figure; the figures themselves are embedded in `milestone-1.html` (built by `python/scripts/build_report.py` from `output/figures/`, which the scripts in section 8 produce). No PNGs are kept in the repository.

## 1. Research plan (combined)

### 1.1 What we forecast and why

**One line:** forecast the next few minutes of an alt perp's move *net of BTC* (its BTC-hedged spread), using what BTC, ETH and the alt itself have just done. The forecast says whether the alt is about to catch up to BTC or snap back.

Raw short-horizon crypto returns are mostly common factor and close to unpredictable, and a long-biased model on raw returns looks good in 2023-24 just by holding beta (Lecture 9, "alpha vs beta"). The hedged spread removes most of the common factor, cannot win by holding beta, and is a sentence a desk understands: "SOL has not caught up to BTC's last move yet".

Definitions on 1-minute bars (ASCII):

```
r_i(t)      = log(mid_i(t)) - log(mid_i(t-1))        NaN on stale bars and the bar after
beta_j(t)   = trailing OLS beta of r_j on r_BTC, 7-day window, bars <= t-1 only
e_j(t)      = r_j(t) - beta_j(t) * r_BTC(t)          hedged (residual) return of follower j
S_j(t,h)    = e_j(t+1) + ... + e_j(t+h)               forward hedged move over h bars
y_j(t,h)    = S_j(t,h) / sigma_e_j(t)                 vol-scaled target; sigma_e_j is a trailing 1-day EWMA
```

Followers: SOL, XRP, DOGE. Leaders: BTC (hedge and leader) and ETH (leader). Primary horizon h = 5 bars; h = 1 and 15 are reported for continuity, not optimized (Lecture 9: variable horizons invite overfit).

**Who would use it.** The buyer is a desk that already has a book: a market maker in alt perps who carries inventory from client flow and hedges it with BTC, or an execution desk holding hedged alt exposure. For them the forecast is not a new trade; it tilts trades they make anyway (which side of the market to lean on, when to hedge, when to unwind), so its value is measured as the PnL of the desk with the forecast minus the same desk without it, on the same flow (section 6). A relative-value desk could also trade the spread outright, and section 6.1 shows why that fails at taker fees: the forecast is right but small. The deliverable is the forecast; the desk simulation is the demonstration of whether it is worth anything after fees on every leg (Lecture 9: "a rule backtest is not signal research").

**Hypotheses.** H1: a combination of leader-move, catch-up and flow features predicts y_j(t,5) out of sample better than the best single feature (median daily rank IC). H2: it beats a static "BTC leads, alt catches up by beta" forecast. H3: a desk that uses the forecast to shade its quotes earns more than the same desk without it, after fees on every leg, with a placebo forecast earning nothing. (H3 was pre-registered as the net PnL of a standalone hedged position; the change to the desk framing, and why, is logged in `docs/DECISIONS.md` on 2026-11-07.) A null result is also informative: if the lead sits entirely inside the same 1-minute bar, bars cannot see it and the tick-data extension is motivated.

### 1.2 Where this came from

Ethan's plan (October, `reports/research-plan/ethan.md`) started from lead-lag between perps, an execution-desk use case with simulated parent orders, and a TWAP slippage metric. Two things changed after feedback and the first look at the data (both logged in `docs/DECISIONS.md`): the target became the hedged spread rather than the raw follower return, because the raw return is mostly beta; and simulated parent orders were retired, because they carry distributional assumptions that the forecast evaluation does not need. The lead-lag question, the false-positive list (stale bars, bounce-back, crash days, multiple testing) and the q -> Python -> Java stack carried over unchanged.

_Hank's plan: to be merged here from `reports/research-plan/hank.md` (step 1 of the plan, pending his write-up)._

### 1.3 Feedback checklist (Lecture 9), how each item is handled

| Item | Where |
|---|---|
| Data from 2023+, full history, count independent observations | 2023-01 to 2025-11, 1-min; every metric is per day, one day = one observation (section 4.2) |
| Carryover handled, not dropped blindly | stale bar and the bar after are masked; positions are booked through them (sections 2.3, 4.4) |
| Continuous target | y_j(t,h), vol-scaled, no labels |
| Linear first | ridge on standardized features; nothing non-linear yet |
| Naive baseline on every chart | zero, static BTC-leads, best standalone feature (section 4.3) |
| Collinearity < 0.7, N-1 experiments | survey section 3.2; loop iteration 2 |
| Multi-window features as EMA differences | `btc_ema3_15`, `own_ema3` (section 3.1) |
| Every normalizer trailing | betas, vol, z-scores, position scaling: all from bars <= t or the fit window (section 4.1) |
| Sliding window 7-90 days, refit 6-168 h | 60-day fit, 7-day test, weekly refit, 5-bar purge |
| Real fees on both legs | 5 bps taker + observed half spread, each leg, entry and exit (section 6) |
| Backtest in stages | mid-to-mid -> fees + spread -> 1-bar delay (figure 6.1) |
| Long and short legs reported separately | section 6 |
| 5-8 features, 3-5 instruments | 7 features, 3 followers + 2 leaders |

## 2. Data chapter

Full version with the audit evidence: `docs/DATA.md`.

### 2.1 What we have, and the pipeline

Binance USD-M perpetual futures, 1-minute bars, 2023-01-01 to 2025-11-30, five symbols (BTC, ETH, SOL, XRP, DOGE), three datasets per symbol-day: `level1_1min` (top of book, mid, spread statistics), `trade_1min` (OHLC trades, buy/sell volume, taker counts), `book_1min` (depth snapshot). 15,924 compressed CSV files, 2.3 GB.

The files are loaded into a date-partitioned kdb+ database (`data/hdb`, 6.8 GB, 7.5 minutes to build) by a q loader written for this milestone (`q/load/bars.q`, schema in `q/schema/bars.q`). Research code reads it only through two q functions, `bars[]` and `coverage[]` (`q/lib/bars.q`), called from Python through PyKX. The Java replay engine is laid out but not needed for this milestone. Acceptance test, passed: the q `coverage[]` table equals an independent audit of the raw files (`python/scripts/coverage.py`) on every (symbol, year) cell.

### 2.2 Coverage

Every file that exists has exactly 1,440 bars; there are no duplicate, non-monotonic or off-grid timestamps. Missing days (file dates): all datasets 2025-11-26..28; level1 ETH+SOL 2024-01-13..14 and SOL+XRP 2025-11-24. 1,062 of 1,065 days are present. Bars per series: 1,529,280 (1,524,960 to 1,527,840 where level1 days are missing). Carryover counts by year and the longest stale runs are in the coverage table of `docs/DATA.md`.

### 2.3 What the audit found, and what it changed

1. **Two timestamp conventions in one archive.** A level1/trade file dated D holds bars ending D 00:01 .. D+1 00:00; a book file holds snapshots at D 00:00 .. D 23:59, taken about 0.6 s after their timestamp. Same `bin_id`, book timestamp is 60 s earlier. We join on timestamp, never on `bin_id`, and shift book features one bar so that a feature at t uses the last snapshot known at t.
2. **Stale bars are mostly not simultaneous across names.** 1.1% of level1 minutes have at least one name stale; in 91% of those only some of the five names are stale, and the first live bar after a stale run is 2-3x the normal size. That is exactly the shape of a fake lead-lag. Stale level1 bars cluster in 2024-25 (whole-day outages: BTC, ETH, DOGE on 2025-01-27), while 2023 is nearly clean. We mask the stale bar and the bar after and never forward-fill a return (decision D12). The measured effect on BTC-alt correlations is 0.002-0.006; it is concentrated in a few days, which is why per-day metrics matter.
3. **`carryover` means different things per dataset.** It is a run counter (1, 2, 3, ...) on repeated bars and a constant -1 on NaN-price bars; in the trade file the stale XRP/DOGE bars of 2024-11-30 carry a NaN price rather than a repeat, and the flag can start one bar late. We also mask on `trade_count == 0` or a NaN price.
4. **When level1 is stale, trade and book are live in 99% of those minutes**, so the level1 gaps are recording gaps, not market halts. Filling the return from trade prices is a candidate improvement, not used here.
5. Tick size matters for XRP and DOGE: a visible spike of exactly-zero 1-minute returns (figure 3.6).

### 2.4 Tick data (slot)

Hank has been capturing tick data for several weeks. Venue, symbols, tables, dates and format are to be filled in with him; the q tables it loads into (`trade`, `quote`) are sketched in `docs/ARCHITECTURE.md`. The 1-minute archive ends 2025-11-30; the capture is a forward period it never saw.

## 3. Features and the quality survey

All survey numbers are on the 2023 selection year only. 2024 is the walk-forward, 2025 is the untouched holdout.

### 3.1 The candidate menu

| Group | Feature | Definition (all trailing) |
|---|---|---|
| Leader move | `btc_ema3_15` | EMA(span 3) - EMA(span 15) of 1-min BTC returns |
| Leader move | `eth_ema3_15`, `eth_btc_ema3_15` | same for ETH; ETH minus BTC |
| Catch-up gap | `gap5`, `gap15`, `gap60` | sum of e_j over the last N bars (how far the alt has moved away from its BTC-implied path) |
| Own move | `own_ema3`, `own_ema3_15` | follower's own return EMA (bounce-back control) |
| Flow | `tib`, `tib_diff` | trade imbalance (buy - sell)/(buy + sell), EMA span 5; follower minus BTC |
| Book | `bib` | top-of-book size imbalance, shifted one bar, EMA span 5 |
| Conditioning | `btc_vol`, `relvol` | log trailing BTC vol (1-day EWMA); log volume relative to its 1-day EWMA |

### 3.2 Distributions and collinearity [submit]

Figure 3.1: `figures/feature_hist.png`. Table: `output/tables/feature_stats.csv`. The return-based features are centred (|mean|/std < 0.01) with excess kurtosis 140 to 600: one-minute crypto returns have tails that a least-squares fit will chase. Trade and book imbalances are bounded and near-Gaussian (kurtosis 0.7 to 1.1, -0.3 for `bib`). `btc_vol` drifts across quarters (std ratio 2.1), as a vol level should.

Figure 3.2: `figures/feature_corr.png`. Pairs above the 0.7 threshold: `btc_ema3`/`btc_ema3_15` 0.92, `eth_ema3`/`eth_ema3_15` 0.92, `own_ema3`/`own_ema3_15` 0.92, BTC vs ETH short EMAs 0.77-0.84. The rule "one member per EMA family, and not both leaders" leaves everything else below 0.65.

### 3.3 Correlation with the target at h = 1, 5, 15 [submit]

Figure 3.3: `figures/feature_target_ic_h5.png`. Table: `output/tables/feature_target_corr.csv` (Pearson, Spearman and median daily rank IC per follower and horizon).

| Feature | SOL | XRP | DOGE | reading |
|---|---|---|---|---|
| `gap15` | -0.053 | -0.051 | -0.064 | the alt mean-reverts against BTC: a negative gap (alt lagging) is followed by a positive hedged move |
| `gap60` | -0.050 | -0.055 | -0.064 | same, slower |
| `own_ema3` | -0.033 | -0.031 | -0.028 | own bounce-back |
| `tib` | -0.033 | -0.026 | -0.027 | buying pressure reverses |
| `tib_diff` | -0.013 | -0.023 | -0.027 | |
| `btc_ema3_15` | +0.008 | +0.018 | +0.018 | a BTC move is followed by the alt catching up, only in XRP and DOGE |
| `btc_vol` | +0.016 | +0.018 | +0.022 | |
| `eth_*`, `bib`, `relvol` | ~0 | ~0 | ~0 | |

Median daily rank IC with y(t,5), 2023. The gap numbers sit at the project's "suspicious above 5%" line, so they were audited before being used: no shared bar between feature and target (every gap input is <= t, every target input is >= t+1), unchanged when one or two bars are skipped between feature and target, zero unflagged stale bars, a day-shift placebo at the noise floor, and the effect is stronger where the spread is wider (SOL gap5 IC -0.085 at >= 2 ticks vs -0.028 at 1 tick) and strongest in XRP, whose tick is 2.7 bps. It is a genuine short-horizon reversal of the hedged mid, consistent with the HW1 finding of lag-1 autocorrelation of about -0.04 on 1-min BTC. Whether it is harvestable is section 6.

### 3.4 BTC vs ETH [submit]

`output/tables/btc_vs_eth.csv`: 1-min returns 0.83 (0.85 for EMA 15), trade imbalance 0.52 (0.57 for its EMA), relative volume 0.78, log volume 0.80. ETH's trade features carry half of BTC's information; its returns carry most of it, which is why ETH enters as a leader only through the ETH-minus-BTC difference (loop iteration 4).

### 3.5 Cross-correlation across EMA horizons, daily average, high-vol day [submit]

Figure 3.4: `figures/xcorr_ema_spans.png` (spans 1, 3, 10, 30, 60). Figure 3.5: `figures/xcorr_daily_vs_highvol.png`. Tables `xcorr_*.csv`. Pooled over 2023, BTC-ETH is 0.83 at 1 minute and 0.85 at span 30; BTC-SOL 0.60 -> 0.63; BTC-XRP 0.52 -> 0.53; the matrix is stable across spans. With span 3 (our favourite from HW2), the average of the 365 daily matrices has mean pairwise correlation 0.65. On the highest-BTC-vol day of 2023 (2023-08-17, 22 bps/min realized vol) it is 0.88, with XRP the name whose correlation rises most (+0.34 to BTC). High vol compresses the cross-section towards one factor, which is the regime in which a BTC hedge is both most needed and least residual-rich.

### 3.6 Volume-weighted index [submit]

Figure 3.6: `figures/index_return_hist.png`, `output/tables/index_return_stats.csv`. Weights are trailing 1-day dollar volume, lagged one bar. 1-minute return std: index 6.6 bps, BTC 6.2, ETH 6.7, SOL 14.2, XRP 10.4, DOGE 10.6. All have excess kurtosis in the hundreds. The spike at exactly zero for XRP and DOGE is tick size, not a data error.

### 3.7 Lag profile [submit]

Figure 3.7: `figures/lag_profile.png`, `output/tables/lag_profile.csv`. corr(r_BTC(t-k), r_j(t)) is 0.52-0.60 at k = 0 and 0.005 (SOL), 0.018 (XRP), 0.016 (DOGE) at k = 1; from k = 2 it is slightly negative. Against the hedged e_j, lag 1 is 0.016 (XRP), 0.015 (DOGE), 0.001 (SOL). **The lead is almost entirely inside the same minute.** What is left at lag 1 is small and absent in SOL, the most liquid follower. This is the null result the plan anticipated and the reason the tick-data extension matters.

### 3.8 Hedge exposure test (decision D3b) and beta window

`output/tables/exposure_test.csv`, `exposure_two_factor.csv`, figure `figures/beta_windows.png`. On 2023, after the BTC hedge the three follower residuals still share a common factor: pairwise correlation 0.27, first principal component 52% of the residual variance (the market-model vs factor-model residual from Quant Methods). Adding a second leg, the leave-one-out volume-weighted index of the other alts, removes it (pairwise -0.03, first PC 37%) and raises R^2 by 0.05-0.10, but the alts then load 0.6-1.0 on the index and only 0.25-0.6 on BTC, and the trade would have four or five legs. Rather than choose a priori, both targets were run through the same walk-forward (section 5). Beta window: 1-day betas move 0.25-0.33 per day, 7-day 0.06, 30-day 0.02, with residual correlation 0.270 / 0.277 / 0.284; 7 days was chosen.

### 3.9 Decisions taken from the survey

Seven features (D6): `btc_ema3_15`, `gap15`, `gap60`, `own_ema3`, `tib`, `tib_diff`, `btc_vol`; max pairwise |corr| 0.62. Tails (D7): trailing z-score on the fit window, clipped at +/-5. Beta 7 days, 1-day vol scale.

## 4. Optimization procedure

### 4.1 Model and walk-forward

One ridge regression pooled over the three followers (the target is vol-scaled, so followers are comparable), on standardized features:

```
y_j(t,5) ~ ridge( z(features_j(t)) ),  alpha = 1 per row, features standardized on the fit window and clipped at +/-5
fit window: trailing 60 days; purge: 5 bars; test block: next 7 days; slide: 7 days  -> 52 refits over 2024
```

Nothing a forecast touches is computed from the test block: betas and vol from bars <= t-1 and <= t, standardization from the fit window, the ridge penalty chosen on 2023 only (0.1 / 1 / 10 gave median daily rank IC 0.035 / 0.038 / 0.036; alpha = 1 frozen), position scaling from past forecasts. The purge is at least h bars so no fit label overlaps the test block. The 2025 holdout is refused by the data layer unless opened through the project's `/holdout` procedure, which has not been run.

### 4.2 Metric

Pre-registered before any OOS result (`docs/EVALUATION.md`, 2026-11-05): **median daily rank IC** (Spearman of forecast vs y(t,5) within each day, pooled over followers), with a day-block bootstrap confidence interval and the share of days with IC > 0. One day is one observation, because overlapping 5-minute targets sampled every minute are not independent. Judging metric for economic value: the value of the forecast to a desk with a book, net of fees on every leg (section 6; changed from the standalone hedged position on 2026-11-07, see `docs/DECISIONS.md`).

### 4.3 Baselines on every chart

1. zero forecast; 2. static "BTC leads": the alt will close the gap, forecast = -gap5 = beta_j x (recent BTC move) - (recent alt move), no fitting; 3. best standalone feature chosen on 2023: -gap15.

### 4.4 Result: combined forecast vs the best standalone feature, 2024 OOS

| | median daily rank IC | 95% CI | days IC > 0 | h=1 | h=15 |
|---|---|---|---|---|---|
| first model (`spread_v0`, 7 features) | 0.040 | [0.035, 0.044] | 87% | 0.039 | 0.037 |
| **final model (`spread_v3`)** | **0.047** | **[0.043, 0.054]** | **91%** | 0.045 | 0.049 |
| static BTC-leads (-gap5) | 0.038 | | | | |
| best standalone feature (-gap15) | 0.039 | | | | |
| zero | 0 | | | | |

Per follower, final model: SOL 0.054, XRP 0.054, DOGE 0.047. The combined forecast beats the best standalone feature out of sample by about three bootstrap standard errors (0.047 vs 0.039, s.e. 0.0024): **H1 passes**; it also beats the static forecast (H2 on IC). The forecast is stable across horizons it was not optimized for. Ridge weights per refit are in `figures/ic_weights_spread_v3_walk_forward.png`: all seven keep their 2023 signs through 2024, with `gap15` weakening from -0.04 to about 0 in the last quarter of 2024, a regime shift worth watching (parameter stability, Lecture 9).

**Scope change, logged (2026-11-07): the same model trained at longer horizons.** The economic diagnosis in 6.1 found that the move the forecast predicts accrues for about two hours, so the same seven features and ridge were retrained on y(t,15) and y(t,60) (purge = h), four logged runs:

| training horizon | 2023 selection year | 2024 walk-forward | days > 0 (2024) | the same forecast scored at h = 5 |
|---|---|---|---|---|
| h = 5 (pre-registered) | 0.038 | 0.047 | 91% | 0.047 |
| h = 15 | 0.061 | 0.058 | 86% | 0.051 |
| h = 60 | 0.070 | 0.069 | 82% | 0.050 |

The improvement is monotone and holds on both years: a slow catch-up is forecast better over a longer window because the target is less noisy relative to it. The selection year alone would have picked h = 60. We keep h = 5 as the headline because it was pre-registered and the longer horizons were run after the 2024 results of h = 5 had been seen; h = 60 is the recommendation for the rest of the project, to be confirmed on the 2025 holdout.

## 5. Improvement loop

Rule (D10), fixed before the first iteration: one change per run, logged whether kept or not; keep it only if the median daily rank IC improves by more than its bootstrap standard error and the net PnL does not get worse; an execution-only change (which cannot move the IC) is judged on net PnL alone. Every trial is in `experiments/registry.jsonl` (56 lines: 1 failed run, 6 selection runs on 2023, 8 walk-forward runs, 2 verdict lines, 22 runs of the superseded desk including its two grids, and 17 runs of the reported desk including its grid, placebos, delay profile and sensitivities).

Figure 5.1: `figures/loop_metric.png`. Table: `output/tables/loop_iterations.csv`. The net PnL column is the standalone hedged position of section 6.1, which every version loses; it is shown because that is what the loop was judged on at the time.

| Run | Change | IC (CI) | net PnL, bps (standalone, section 6.1) | Verdict | What we learned |
|---|---|---|---|---|---|
| v0 | first model | 0.040 [0.035, 0.044] | -323,271 | baseline | beats the best feature by 0.001 only |
| v0_2f | target hedged with BTC + alt index (D3b) | 0.037 [0.033, 0.042] | -323,855 | rejected | the cleaner residual is less forecastable; BTC-only stays the target |
| v1 | clip the target at +/-5 in the fit | 0.047 [0.043, 0.054] | -280,701 | **kept** | the fit was chasing crash minutes while the metric is rank-based |
| v2 | drop `btc_vol` (N-1) | 0.046 [0.043, 0.051] | -284,442 | rejected | the model does not depend on it, but removing it buys nothing |
| v3 | no-trade band at 1.5 sd (execution only) | 0.047 (unchanged) | -146,869 | **kept** | turnover 54 -> 33 units/day, loss halved, still a loss |
| v4 | add ETH-minus-BTC EMA difference | 0.047 [0.042, 0.053] | -148,743 | rejected | ETH's move net of BTC does not lead the alts (weight -0.004 +/- 0.005) |

Two of four changes were kept. The number of trials on the 2024 walk-forward is six; the selection year carried four more (alpha grid, desk forecasts) plus the survey, and the desk's parameters another 36 selection-year points (section 6.3). We state this because a 0.047 IC found after six trials is a weaker claim than the same number found once.

## 6. Economic value: what the forecast is worth to a desk with a book

### 6.1 Why a standalone hedged trade cannot work at taker fees (the diagnosis that reworked this section)

The first version of this section traded the forecast outright: position proportional to the forecast, long follower / short beta x BTC, held 5 bars, rebalanced every minute (`figures/final_pnl_v1.png`, `output/tables/diag_cost_decomposition.csv`). On the 2024 walk-forward the final model earned +8,275 bps of follower notional mid-to-mid (Sharpe 5.0) and lost 146,869 bps after 5 bps taker fees and the half spread on both legs. The decomposition says why, and it is not the forecast:

| per day, bps of follower notional, 2024 | gross edge | alt-leg fees | alt spread | BTC-leg fees | BTC spread | turnover |
|---|---|---|---|---|---|---|
| SOL | +37 | 189 | 3.5 | 239 | 0.5 | 38 units |
| XRP | +8 | 196 | 34 | 160 | 0.3 | 39 |
| DOGE | +23 | 178 | 14 | 226 | 0.4 | 36 |

Fees are 90-97% of the cost; spreads are almost nothing. The BTC hedge leg costs more than the alt leg because beta is about 1.3. The strategy pays 11 bps per unit traded to earn under 1 bp, because it round-trips four fills every five minutes. Two more facts from the same diagnosis (`diag_edge_by_horizon.csv`, `diag_persistence.csv`): the move the forecast predicts keeps accruing for about two hours (after |z| >= 2 the sign-adjusted hedged move is 1.5 bps at 5 min, 5.3 at 60, 9.4 at 120 for SOL, similar for DOGE), while the forecast itself decays in ten minutes (autocorrelation 0.55 at 5 min, 0.28 at 15). A 1-minute forecast of a slow catch-up is worth a few bps per entry, and no four-fill round trip at 3.5-5 bps per fill can pay for that. This is a property of the signal's size, not a bug, and it says the right buyer is a desk that trades anyway.

### 6.2 The mock desk

This metric is exploratory: it was built after the pre-registered one failed, and it is reported as such. A market-making desk in each follower, driven by the observed taker flow (no simulated order process). Each minute it fills a share f = 2% of the market's taker volume passively: takers who sell are bought from, takers who buy are sold to. Fills are priced at the bar's taker-side VWAP (the desk buys at the VWAP of taker sells, sells at the VWAP of taker buys) and marked at the close mid, so the adverse selection a passive quote eats inside the minute is paid, not assumed away; a maker fee of 1 bps is charged (a Binance VIP tier; retail would be 2 bps). Fills are capped at $200k a side a minute. The desk carries the alt inventory I in units of N0 = $1M, hedges it with BTC at H = beta_j x I but only when the hedge drifts more than T = 0.25 units from target (taker 3.5 bps plus the BTC half spread), and unwinds inventory beyond |I| > L = 3 at taker (stretchable to at most 1.5 L). Its quotes always lean against inventory (skew -0.5 x I/L). Fills are suppressed on bars where the level1 or trade bar is stale (the project's masking rule), while held positions keep earning the unmasked move.

The forecast does one thing: when |z| >= 1.5 it shades the quotes by k x z, capped at +/-s_max, so the desk captures more of the flow on the side the forecast favours. z is the forecast minus its trailing 7-day mean, over its trailing 7-day std, on the minute grid, so the desk acts on timing and not on a week-long lean. Everything is decided at the end of bar t and acts on the fills and prices of bar t+1; betas and spreads are the trailing values used everywhere else.

**Value of the forecast** = net PnL of this desk minus the net PnL of the same desk with the forecast switched off, on the same flow. Fills, spread revenue and inventory management are identical in both; only the lean differs. Nothing in it is a new round trip. Because the lean is sized by the inventory limit, the value is reported **per unit of risk budget** (bps a day per N0 of limit) as well as in bps of the desk's fills. Code: `python/notset/eval/desk.py` (version 2), driver `python/scripts/desk_run.py`.

A first version of this desk (fills at the close mid, no caps, z not demeaned) was reviewed by three independent reviewers before its number went anywhere; they found that it hid intra-bar adverse selection, that one 15-minute flash crash on 2024-01-03 produced a quarter of a two-month sample's value, and that two-thirds of its value came through the BTC hedge leg via the slow part of the forecast. All three are fixed above; the first version's runs stay in the registry, marked superseded.

### 6.3 Parameters chosen on 2023, frozen for 2024

Four free parameters (k, s_max, z_in, tilt) were chosen on the 2023 selection year from a 24-point grid (`output/tables/desk_grid_select_v2.csv`, every point logged; the superseded first version used 36 points). Every one of the 24 points was positive in total (+0.44 to +0.99 bps of fills), but every CI crossed zero, and the dead zone and a wider skew cap mattered more than the gain k; the tilt made no difference once the limit stretch was capped. Chosen: k = 0.25, s_max = 0.8, z_in = 1.5, tilt = 0 (+0.0048 per day, +0.99 bps of fills, median day +0.0067, 70% of days positive, CI [-0.0027, +0.0107]). **The selection-year evidence is not significant on its own and is mostly DOGE** (SOL -0.19, XRP +0.39, DOGE +4.7 bps of fills), which the first version also showed. f, N0, L, T, the inventory skew, the fill cap and the fees were fixed before the grid and not tuned; the sensitivity to L is reported below because the value scales with it.

### 6.4 Result, 2024 walk-forward (the forecast's OOS year), parameters frozen [final plot v1]

Figure 6.1: `figures/final_desk_v1.png` (left: cumulative value of the forecast, per name and total; right: the desk's own PnL with and without it). Tables: `output/tables/desk2_walk_forward_*.csv`.

| 2024, per day, N0 = $1M units | value of the forecast | bps of the desk's fills | bps/day per N0 of inventory limit | days > 0 | day-bootstrap 95% CI |
|---|---|---|---|---|---|
| all three names | **+0.0057** (about $5,700/day for a 2%-of-flow desk with a $3M limit per name) | **+0.52** | **+6.3** | 64% (median day +0.0058) | [+0.0011, +0.0097] |
| SOL | +0.0020 | +0.34 | | 61% | [+0.0002, +0.0040] |
| XRP | +0.0008 | +0.36 | | 65% | [-0.0021, +0.0035] |
| DOGE | +0.0029 | +1.00 | | 64% | [+0.0008, +0.0049] |

Where it comes from, per day: alt inventory +0.0084, BTC hedge leg +0.0006, realized spread +0.0007, extra hedging and unwind costs -0.0041. The value is in the alt inventory, i.e. in the hedged spread the forecast is about, not in BTC timing. The desk with the forecast carries 3.7x the inventory (std 0.52 vs 0.14 N0, never above the 3.0 limit) and hedges 2.8x as often (60 vs 21 BTC trades a day); those costs are inside the number.

Robustness (pre-registered, `docs/EVALUATION.md` section 3, plus the reviewers' additions):
- **Placebo:** the same desk fed the forecast from one or seven days earlier gets +0.01 and -0.13 bps of fills (51% and 48% of days positive, CIs through zero). The value is timing, not leaning.
- **Events:** without the five largest |value| days the mean *rises* to +0.0074 (the largest days were losses); without the five highest-BTC-vol days +0.0045. Not an event result.
- **How old can the forecast be:** fed a forecast 0 / 5 / 15 / 60 / 240 minutes old the desk earns +0.52 / +0.53 / +0.54 / +0.31 / -0.05 bps of fills. The book's inventory turns over in hours, so what it monetizes is the forecast's hour-scale information; the 5-minute component is invisible to it, and the information is gone after four hours. This is the same fact as section 4.4's horizon result seen from the trading side.
- **Risk budget:** L = 2 / 3 / 5 gives +0.27 / +0.52 / +0.76 bps of fills, i.e. +5.0 / +6.3 / +5.6 bps a day per N0 of limit: the value is proportional to the inventory the desk is allowed to carry, which is why the per-limit unit is the honest one.
- **Fees:** the value is the same at a zero maker fee (+0.51), by construction, since both desks fill the same flow. What the fee changes is the desks' own PnL: at 1 bps the base desk loses -0.0152 a day (Sharpe -18) and the forecast cuts that to -0.0095 (Sharpe -4); at a zero maker fee the forecast desk is positive (+0.0015 a day, Sharpe 0.6) and the base desk is not (-0.0042). A touch desk paying 1 bps against 0.1-0.8 bps half spreads loses money in this data with or without a forecast; real desks live on rebates and queue priority.
- **Not demeaning z** (letting the desk also follow the forecast's week-long lean): +0.58, with the extra coming through the hedge leg. The demeaned number is the headline.
- **The 60-minute forecast** (section 4.4) through the same desk and parameters: +0.0067 a day, +0.61 bps of fills, +7.5 bps per N0 of limit, CI [+0.0008, +0.0122], placebo -0.01 bps. On 2023 it gives +1.10 bps of fills with a CI through zero, like the 5-minute one.

**H3 in the desk framing:** a desk that already trades these names and leans its quotes on the forecast earns about **half a basis point on every dollar of flow it handles, or 5-6 bps a day per $1M of inventory limit**, out of sample on 2024, positive on all three names, significant on the day bootstrap, zero under the placebo, not driven by events, and attributable to the alt leg. It is a small number. The selection-year evidence is positive at every grid point but not significant, so the claim rests on 2024 and on the 2025 holdout, which is opened once at the end of the project. Trials behind this section: 36 + 24 grid points on 2023 and 16 + 20 evaluation runs, all in the registry.

### 6.5 What a desk would push back on (assumptions, stated)

The fill share responds linearly to the skew and a passive quote is always filled at the bar's taker-side VWAP; a real desk's share of flow depends on queue position and quote width, and leaning harder may fill less, not more. The VWAP convention charges the average adverse selection of the bar's flow, not the worst of it. Unwinds pay the fee and half spread but no market impact. The BTC hedge is per name; one hedge for the three-name book nets little (positions are 0.3 correlated; tested). The maker fee makes the base desk unprofitable by construction at this tier, which is why the value is reported as a difference and per unit of risk, not as the desk's own PnL. Figure 6.2 (`figures/sorted_signal.png`) remains the plainest picture of the forecast: the top vigintile of forecasts is followed by +1.6 bps over five minutes, the bottom by -0.05, the middle by about -0.2.

## 7. What's next (after Milestone 1)

- Tick slot: describe and load Hank's capture; rerun the lag profile at second horizons; the forward period (late 2026) is a true out-of-sample test the archive never saw.
- The desk: a fill model with queue position and quote width instead of a linear share; impact on unwinds; a maker-rebate fee schedule; the ETH leg; the h = 60 forecast as the production one if the holdout confirms it.
- Target: the trade-close fill for stale level1 bars (D12 candidate), per-regime results (weekday/weekend, vol), Diebold-Mariano against the static baseline (pre-registered, not yet run).
- Leadership rotation and market-vs-idiosyncratic flow (`docs/THESIS.md` extensions).
- 2025 holdout: opened once, at the end, through `/holdout`.

## 8. Reproducibility

Scripts (`python/scripts/`): `build_report.py` (this document as one self-contained HTML with the figures embedded), `make_walkthrough.py` (the step-by-step notebook `python/notebooks/walkthrough.ipynb`), `coverage.py` (data chapter), `survey.py` (section 3), `exposure_test.py` (3.8), `run_walkforward.py --config spread_vN --split select|walk_forward` (sections 4-5), `final_plots.py --run <run_id>` (5, 6.1), `pnl_diagnosis.py --run <run_id>` (6.1), `desk_run.py --run <run_id> --split select --grid`, then `--split walk_forward --params '{"k": 0.25, "s_max": 0.8, "z_in": 1.5, "tilt": 0}'` with `--placebo-shift-days`, `--delay-bars`, `--no-demean` for the robustness rows (6.3-6.4). Configs: `config/spread_v0.yaml` .. `spread_v4.yaml`, `spread_v0_2f.yaml`. Package: `python/notset/` (io via PyKX, features, target, eval incl. `desk.py`). Tests: `python/tests/` (12 look-ahead, alignment and accounting asserts; all pass). Data layer: `q/` (schema, loader, query functions). Decisions D1-D12 and the 2026-11-07 change of the judging metric: `docs/DECISIONS.md`. Lessons: `research/LEARNINGS.md`.
