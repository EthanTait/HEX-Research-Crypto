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
- [~] Environment checklist in `docs/SETUP.md` passes on both machines (2026-11-05: full stack chosen, see `DECISIONS.md`; in progress on Ethan's machine)

## Step 1: combined write-up (Thu-Fri)

Merge `reports/research-plan/ethan.md` and `hank.md` into one document and work through the feedback checklist above.

- **D1. Decided 2026-11-05:** markdown in `reports/milestones/milestone-1/`, figures linked from `figures/`, exported with pandoc at submission.
- **D2.** What carries over from Hank's plan into the thesis, and what gets dropped. The old execution-timing / TWAP framing is retired (see `DECISIONS.md`); the use-case section is rewritten around the hedged spread.

## Step 2: data chapter (Thu-Fri)

Update `docs/DATA.md` from the actual files, not from memory.

- [ ] q: 1-min archive into an HDB (**Ethan writes this**; see `q/README.md` for the table contract)
- [ ] Coverage table per symbol and dataset: rows, missing days, carryover counts by year
- [ ] Tick-data slot: what Hank's capture contains (venues, symbols, tables, dates, format). Left blank until known
- **D3.** Universe: is ETH a leader only, or also a follower? Is a volume-weighted index used as a second hedge alongside BTC?
- **D4.** Python access while the q loader is being written: wait for PyKX on the HDB, or a temporary CSV reader in `notset.io` behind the same function signature so research isn't blocked. _Open until q is installed (environment decision, 2026-11-05)._
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

- [ ] Distribution per feature with mean, std, skew, kurtosis
- [ ] Feature cross-correlation matrix; flag pairs > 0.7
- [ ] Correlation of each feature with the target at h = 1, 5, 15
- [ ] BTC vs ETH return and trade-feature correlations
- [ ] Cross-correlation matrices across EMA horizons; time-averaged daily matrix for the chosen span
- [ ] High-vol day matrix vs long-run average
- [ ] Volume-weighted index of the 5 names; return histograms of the index and each name on one plot
- [ ] Lag profile: corr(r_BTC(t-k), e_j(t)) for k = 0..15. Is the lead all at lag 0?

- **D6.** Final feature list for the first model.
- **D7.** Tail treatment per feature (winsorize at trailing bounds, cbrt, or log).

## Step 4: baselines and optimizer (Sat)

- Splits: **2023** feature selection and survey; **2024** sliding-window walk-forward (the improvement loop runs here); **2025-01 to 2025-11** clean OOS, opened once at the end and logged.
- Optimizer: ridge on standardized features, sliding window, purge of h bars between fit and test.
- Baselines on every chart:
  1. zero forecast
  2. static "BTC leads": forecast = beta_j * (recent BTC move not yet reflected in j)
  3. best standalone feature (chosen on 2023)
- Pass condition for the sheet: combined forecast beats the best standalone feature OOS on median daily rank IC.

- **D8.** Sliding-window length and refit cadence (Lecture 9 range: 7-90 days, refit 6-168 h).
- **D9.** Ridge penalty chosen how (fixed a priori, or picked on 2023 only).

## Step 5: improvement loop (Sat-Sun)

The loop (decide the exact rule as **D10** before the first run):

1. Read `research/LEARNINGS.md` and `experiments/registry.jsonl`.
2. Propose one change (add or drop one feature group, a transform, a window). Ethan approves.
3. Run the 2024 walk-forward. Log the run in the registry.
4. Keep the change only if median daily rank IC improves by more than its bootstrap s.e. **and** net PnL doesn't get worse.
5. Write one line in `LEARNINGS.md` about what was learned, kept or rejected.

Run it 3-5 times. Output: metric across iterations, with every trial shown, including rejected ones [submit].

## Step 6: final plot v1 (Sun)

- [ ] Cumulative net PnL over time, 2024 walk-forward OOS, hedged position proportional to the forecast, vs the static BTC-leads baseline and the best standalone feature. Show the stages: mid-to-mid, after fees + spread, after one-bar delay.
- [ ] Companion: distributions of the final features, and the sorted-signal plot from Lecture 5 (cumulative realized spread vs sorted forecast).
- **D11.** Is the 2025 clean OOS opened for Milestone 1, or saved for the final presentation? Recommendation: save it. It can only be looked at once.

## Step 7: assemble and submit (Mon Nov 9)

- [ ] Figures copied into `reports/milestones/milestone-1/figures/`, each produced by a script in `python/scripts/`
- [ ] Combined doc updated with the data chapter, survey, procedure, loop results and final plot v1
- [ ] Decisions D1-D11 all logged in `docs/DECISIONS.md`
