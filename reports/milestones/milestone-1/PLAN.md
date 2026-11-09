# Milestone 1 plan

Due **Mon 2026-11-09** (group). Course sheet: [`INSTRUCTIONS.md`](INSTRUCTIONS.md). Thesis: [`../../../docs/THESIS.md`](../../../docs/THESIS.md).

**How we work through this:** one step per session in VS Code. Each step lists decision points (`D#`). Claude proposes options with a recommendation, **Ethan decides**, and the decision is logged in `docs/DECISIONS.md` before code is written. Nothing below a decision point gets built until it's decided.

Status keys: `[ ]` not started, `[~]` in progress, `[x]` done.

---

## Settled already (2026-11-05)

| Item | Decision |
|---|---|
| Target | BTC-hedged spread of the follower, forward h bars, vol-scaled (`THESIS.md` definitions). h = 5 primary; 1 and 15 reported |
| Metric | Fit and improvement loop on **median daily rank IC**; judge on **cumulative net PnL** of the hedged position |
| Final plots | (1) cumulative OOS net PnL over time vs baseline, **required**; (2) feature distributions. No simulated parent orders (Ethan: they carry bias and distributional assumptions) |
| Stack | q -> Python -> Java laid out now. **q is Ethan's to write.** Tick data has an empty slot in the data layer |
| Code location | Everything new lives in this repo. Homework code isn't imported; ideas from it are rebuilt here |
| Data now | Binance USD-M 1-min bars, 5 perps, 2023-01-01 to 2025-11-30 |

## Lecture 9 feedback checklist (applies to every step)

- [ ] Data from 2023+; full history for minute-level work; count independent observations, not bars
- [ ] Carryover handled, not dropped blindly; stale bars masked, the bar after too
- [ ] Continuous target (no sign / yes-no labels)
- [ ] Linear model first; non-linear only if it beats linear OOS
- [ ] Naive baseline on every chart
- [ ] Collinearity threshold < 0.7; N-1 drop experiments instead of trusting ridge to sort it out
- [ ] Multi-window features as non-overlapping segments or EMA differences
- [ ] Every normalizer trailing (z-scores, winsor bounds, betas, vol)
- [ ] Sliding window 7-90 days, refit every 6-168 h; clean OOS left untouched
- [ ] Real fees: about 5 bps taker per side + half spread, on **both legs** of the hedge
- [ ] Backtest in stages: mid-to-mid -> fees + spread -> one-bar delay -> (funding, later)
- [ ] Long and short legs reported separately
- [ ] 5-8 features, 3-5 instruments

---

## Step 0: logistics (Thu Nov 5)

- [ ] Hank's research-plan write-up into `reports/research-plan/hank.md`
- [~] Environment checklist in `docs/SETUP.md` passes on both machines (2026-11-05: full stack chosen, see `DECISIONS.md`; passes on one machine, second pending)

## Step 1: combined write-up (Thu-Fri)

Merge `reports/research-plan/ethan.md` and `hank.md` into one document and work through the feedback checklist above.

- **D1. Decided 2026-11-05:** markdown in `reports/milestones/milestone-1/`, figures linked from `figures/`, exported with pandoc at submission.
- **D2.** What carries over from Hank's plan into the thesis, and what gets dropped. The old execution-timing / TWAP framing is retired (see `DECISIONS.md`); the use-case section is rewritten around the hedged spread.

## Step 2: data chapter (Thu-Fri)

Update `docs/DATA.md` from the actual files, not from memory.

- [x] q: 1-min archive into an HDB (2026-11-06: `q/load/bars.q`, 1,062 dates x 3 tables, 6.8 GB, 7.5 min; q `coverage[]` matches `output/coverage/by_year.csv` on every cell)
- [x] Coverage table per symbol and dataset: rows, missing days, carryover counts by year (2026-11-05, from the raw files via `python/scripts/coverage.py`; re-run through q `coverage[]` once the HDB exists, the two must match)
- [ ] Tick-data slot: what Hank's capture contains (venues, symbols, tables, dates, format). Left blank until known
- **D3a. Decided 2026-11-05:** ETH is a leader. Followers in the fit are SOL, XRP, DOGE; ETH-as-follower is reported once, untuned, as a robustness row.
- **D3b. Open, decided on evidence:** volume-weighted index as a second hedge alongside BTC. Waits for the hedge exposure test in step 3.
- **D4. Decided 2026-11-05:** Python waits for PyKX on the HDB. No temporary CSV reader. The q loader is the critical path.
- **Schema. Decided 2026-11-05:** HDB `date` partition = source file date (see `DECISIONS.md` for what that means at midnight).
- **D5. Decided 2026-11-05:** no outside data before Milestone 1. Funding rates and a second venue revisited afterwards.

## Step 3: features and quality survey (Fri-Sat)

Start from 5-8 features. Candidate menu (Ethan picks):

| Group | Candidate | Expected range / shape |
|---|---|---|
| Leader move | BTC 1-min return EMA (short span), as EMA differences | centered, fat-tailed -> clip or cbrt |
| Leader move | ETH return EMA | same |
| Catch-up gap | accumulated hedged spread e_j over the last N bars (has the alt lagged BTC's move?) | centered |
| Own move | follower's own return EMA (bounce-back control) | centered |
| Flow | trade imbalance (buy - sell) / (buy + sell), EMA, follower minus leader | bounded [-1, 1] |
| Book | top-of-book size imbalance, shifted 1 bar | bounded [-1, 1] |
| Conditioning | trailing BTC vol or relative volume, used as a continuous multiplier, not as regimes | positive, log-transform |

Survey outputs (each one is a `[submit]` item on the sheet):

- [x] Distribution per feature with mean, std, skew, kurtosis (2026-11-06, `python/scripts/survey.py`, `output/tables/feature_stats.csv`, `figures/feature_hist.png`)
- [x] Feature cross-correlation matrix; flag pairs > 0.7 (8 pairs, all inside the EMA families and BTC-vs-ETH)
- [x] Correlation of each feature with the target at h = 1, 5, 15 (`feature_target_corr.csv`; gap features -0.05 to -0.06, audited)
- [x] BTC vs ETH return and trade-feature correlations (returns 0.83, trade imbalance 0.52)
- [x] Cross-correlation matrices across EMA horizons; time-averaged daily matrix for the chosen span (span 3; mean pairwise 0.65)
- [x] High-vol day matrix vs long-run average (2023-08-17: 0.88 vs 0.65)
- [x] Volume-weighted index of the 5 names; return histograms of the index and each name on one plot
- [x] Lag profile: corr(r_BTC(t-k), e_j(t)) for k = 0..15. The lead is at lag 0; lag 1 is 0.016 for XRP/DOGE, 0.001 for SOL
- [x] Hedge exposure test on 2023 (`exposure_test.py`): residual pairwise corr 0.27 after the BTC hedge, -0.03 with an alt-index leg; 7-day beta chosen

- **D6. Decided 2026-11-06:** `btc_ema3_15`, `gap15`, `gap60`, `own_ema3`, `tib`, `tib_diff`, `btc_vol` (max pairwise |corr| 0.62).
- **D7. Decided 2026-11-06:** trailing z-score on the fit window, clipped at +/-5.
- **D12. Decided 2026-11-06:** stale level1 bars (and the bar after) are masked, not filled from trade or book. The trade-close fill is a candidate loop iteration.
- **Target parameters. Decided 2026-11-06:** beta window W chosen by the 2023 exposure test among 1, 7, 30 days; sigma_e is a 1-day-half-life EWMA.

## Step 4: baselines and optimizer (Sat)

- Splits: **2023** feature selection and survey; **2024** sliding-window walk-forward (the improvement loop runs here); **2025-01 to 2025-11** clean OOS, opened once at the end and logged.
- Optimizer: ridge on standardized features, sliding window, purge of h bars between fit and test.
- Baselines on every chart:
  1. zero forecast
  2. static "BTC leads": forecast = beta_j * (recent BTC move not yet reflected in j)
  3. best standalone feature (chosen on 2023)
- Pass condition for the sheet: combined forecast beats the best standalone feature OOS on median daily rank IC. **Passed 2026-11-07:** final model 0.047 [0.043, 0.054] vs -gap15 0.039 and static 0.038 on 2024 (`python/scripts/run_walkforward.py`).

- **D8. Decided 2026-11-06:** 60-day fit, purge 5 bars, 7-day test, slide weekly (about 52 refits over 2024).
- **D9. Decided 2026-11-06:** ridge alpha picked on 2023 only from {0.1, 1, 10}, then frozen. **Result:** 0.035 / 0.038 / 0.036, alpha = 1.

## Step 5: improvement loop (Sat-Sun)

The loop (decide the exact rule as **D10** before the first run):

1. Read `research/LEARNINGS.md` and `experiments/registry.jsonl`.
2. Propose one change (add or drop one feature group, a transform, a window). Ethan approves.
3. Run the 2024 walk-forward. Log the run in the registry.
4. Keep the change only if median daily rank IC improves by more than its bootstrap s.e. **and** net PnL doesn't get worse.
5. Write one line in `LEARNINGS.md` about what was learned, kept or rejected.

Run it 3-5 times. Output: metric across iterations, with every trial shown, including rejected ones [submit].

- **D10. Decided 2026-11-07:** the rule above, plus: an execution-only change (no effect on the IC by construction) is judged on net PnL alone. Verdicts are appended to the registry as a separate line, since run lines are never edited.
- **Done 2026-11-07:** 4 iterations (clip target: kept; drop btc_vol: rejected; 1.5 sd no-trade band: kept; ETH-minus-BTC feature: rejected) plus the D3b hedge comparison (rejected). `figures/loop_metric.png`, `output/tables/loop_iterations.csv`.

## Step 6: final plot v1 (Sun)

- [x] ~~Cumulative net PnL of the standalone hedged position~~ (`figures/final_pnl_v1.png`): mid-to-mid +8,275 bps, after fees -146,869. Kept as the diagnosis (report 6.1), not the final plot.
- [x] **Final plot v1 (reworked 2026-11-07, corrected after review 2026-11-08):** value of the forecast to a mock market-making desk with a book, 2024 OOS, `figures/final_desk_v1.png`, `python/scripts/desk_run.py` (desk v2). +0.0057 N0/day = +0.52 bps of fills = 5-6 bps/day per $1M of inventory limit, CI [+0.0011, +0.0097], placebos 0, positive on all three names, value in the alt leg, flat for a forecast up to 15 min old and gone at 4 h.
- [x] Companion: feature distributions (`figures/feature_hist.png`) and the sorted-signal plot (`figures/sorted_signal.png`).
- **D11. Decided 2026-11-07:** the 2025 holdout stays closed for Milestone 1; `notset.io` refuses 2025 reads unless `/holdout` sets `NOTSET_HOLDOUT=1`.

## Step 7: assemble and submit (Mon Nov 9)

- [x] Figures copied into `reports/milestones/milestone-1/figures/`, each produced by a script in `python/scripts/` (12 figures, 2026-11-07)
- [~] Combined doc `reports/milestones/milestone-1/milestone-1.md`: data chapter, survey, procedure, loop results and final plot v1 written 2026-11-07; Hank's plan section still pending (step 1); Ethan to read through and confirm the LEARNINGS lines
- [x] Decisions D1-D12 logged in `docs/DECISIONS.md`
- [ ] Export with pandoc on submission day (D1)
