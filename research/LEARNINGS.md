# Learnings

What each run taught us. Read before proposing the next change. Lines are added through `/iterate` or `/retro`, and Ethan confirms each one. Wrong lines get struck through with the run that contradicted them, never deleted. Every line cites run ids from `experiments/registry.jsonl`.

## Carried over from the homeworks (1-min Binance, before this repo)

These came from HW2/HW3 on the same data. They're priors, not results of this project, so treat them as things to re-check here.

- Short return EMAs of 1-min returns (span ~3-5) carry most of the single-name 5-min predictability; MACD didn't beat them (HW2).
- Short-horizon 1-min returns mean-revert slightly (lag-1 autocorrelation about -0.04 on BTC, Jan 2024) (HW1).
- Refitting a 3-parameter combo on a short sliding window gave unstable weights and lost OOS to fixed weights; longer windows were better, monotonically up to 90 days (HW2, HW3).
- Adding a beta-hedged relative-value feature to single-name features raised walk-forward Sharpe on the 5 names (2.41 -> 3.09 in 2024, 1.52 -> 2.36 in 2025) (HW3). That's evidence the cross-asset spread holds information at 1-min.
- Mean pairwise 5-min correlation rises from about 0.52 in low-vol to 0.69 in high-vol regimes (2024); XRP and DOGE pairs move most (HW3).
- Scaling positions by a 1-day variance timed vol inside a name and halved Sharpe vs a 90-day variance (HW3).
- DOGE was the only name negative OOS in HW3 Task 3.

## This project

_Proposed 2026-11-07 from the Milestone 1 runs; each line waits for Ethan's confirmation._

- The lead of BTC over SOL/XRP/DOGE at 1-min is almost all at lag 0 (corr 0.52-0.60); lag 1 is 0.016 for XRP and DOGE and 0.001 for SOL, and the hedged lag profile is flat after that (survey, `output/tables/lag_profile.csv`). Bars can't see most of the lead; ticks might.
- The hedged spread mean-reverts at short horizons: `gap15`/`gap60` (sum of e_j over the last N bars) have median daily rank IC -0.05 to -0.06 against y(t,5) on 2023, stronger where ticks are wide; audited as not look-ahead (skip-bar, placebo, stale-bar checks). The sign is "alt lagging BTC catches up", not "BTC move leads".
- Least squares on a fat-tailed target loses a rank metric: the 7-feature ridge had IC 0.040 vs 0.039 for -gap15 alone until the target was clipped at +/-5 in the fit, then 0.047 [0.043, 0.054] (runs `..._spread_v0_...` vs `..._spread_v1_...`).
- Hedging with BTC plus a leave-one-out alt index removes the common alt factor from the residual (pairwise corr 0.27 -> -0.03) but the cleaner residual is less forecastable (IC 0.037 vs 0.040) and costs 2-3 more legs (`..._spread_v0_2f_...`). BTC-only stays the target.
- `btc_vol` and the ETH-minus-BTC EMA difference add nothing beyond one s.e. (`..._spread_v2_...`, `..._spread_v4_...`). ETH's move net of BTC does not lead the alts.
- Forecast is real, trade is not, at taker fees: 0.7 bps earned per unit traded vs about 13 bps of round-trip cost on two legs; a 1.5 sd no-trade band halves the loss (`..._spread_v3_...`). Execution (maker fills, wider band, longer hold) is the lever, not the model.
- The 2024 ridge weights keep their 2023 signs, but `gap15` fades from -0.04 to about 0 in Q4 2024: the reversal weakened late in 2024 (watch for regime dependence).
- Where the standalone trade's money went: 90-97% fees, spreads almost nothing; the BTC hedge leg (beta ~1.3) costs more than the alt leg. The predicted catch-up accrues for ~2 h (sign-adjusted move after |z| >= 2: 1.5 bps at 5 min, 5.3 at 60, 9.4 at 120 for SOL) while the forecast decays in ~10 min, so exits must be fixed-length, not forecast-fade (`output/tables/diag_*.csv`).
- ~~To a desk with a book the forecast is worth +0.80 bps of every dollar of flow it handles on 2024~~ Withdrawn 2026-11-08: that desk booked fills at the close mid, let a flash crash fill $2.2M in a minute, and leaned on the forecast's week-long mean (runs `..._desk_walk_forward`, superseded). With fills at the taker-side VWAP, capped fills, and demeaned z the value is **+0.52 bps of fills = 5-6 bps a day per $1M of inventory limit** on 2024 (CI [+0.0011, +0.0097] N0/day, 64% of days, placebos +0.01 / -0.13 bps), positive on all three names, in the alt leg not the hedge leg (`..._desk2_walk_forward`). Report it per unit of risk budget: L = 2/3/5 gives 5.0/6.3/5.6 bps per N0 of limit.
- A book with an inventory half-life of hours monetizes the forecast's hour-scale information, not its 5-minute edge: fed a 0/5/15/60/240-minute-old forecast the desk earns +0.52/+0.53/+0.54/+0.31/-0.05 bps of fills (`..._desk2_walk_forward` delay runs). Same fact as the horizon result below, seen from the trading side.
- The desk's selection-year evidence is positive at every grid point but never significant and mostly DOGE (SOL slightly negative on 2023); the 2024 result is the first OOS look at the desk design. The 2025 holdout decides.
- Longer training horizons forecast the catch-up better, monotonically and on both years: median daily rank IC h5 0.038/0.047, h15 0.061/0.058, h60 0.070/0.069 (2023/2024; `..._spread_v3_h15_...`, `..._spread_v3_h60_...`). The h60 forecast still scores 0.050-0.057 at h = 5, and is worth +0.61 bps of fills to the corrected desk (placebo -0.01).
- Demean a forecast before feeding it to a slow book: the undemeaned h60 forecast's week-long lean earned +0.60 bps of fills under a day-shift placebo, through the BTC hedge leg; demeaned, the placebo is zero (`..._desk2_walk_forward_h60placebo1`).
- A touch market maker paying a 1 bps maker fee against 0.1-0.8 bps half spreads loses money in this data with or without a forecast; the value of a forecast to it must be reported as a difference, never as the desk's own PnL.
- Netting the BTC hedge across the three names barely helps (72 -> 67 hedge trades a day) because their positions are 0.3 correlated.
- Review before reporting paid for itself twice: the leakage audit caught a ridge penalty scaled to OLS and a backtest that skipped costs around every stale run; the desk review caught close-mid fills and an event-driven sample. Give reviewers the code and a data slice, not the conclusion.

<!-- retro: 2026-11-07, runs through ..._desk_walk_forward (placebo7) -->
