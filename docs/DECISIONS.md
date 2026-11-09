# Decision log

Newest entries at the top. One entry per decision: what was decided, why, and what was ruled out. If a decision is reversed, add a new entry rather than editing the old one.

---

### 2026-11-09: tick data is a separate study, decided after Milestone 1; extra deliverable only if it holds
- **Decided (Ethan):** wait until Hank describes the capture, then run it as a **separate pathway** (`reports/tick-study/README.md`): (1) a forward test of the frozen 1-minute model on ticks aggregated to 1-minute bars, opened once like the 2025 holdout; (2) an event-time version, quote by quote, since that is how the desk we pitched to would run it. It must not interfere with the 1-minute thesis; if it does not hold, the 1-minute result stands.
- **Ruled out for now:** adding the capture as a second pre-registered holdout today (venue, symbols and format are not known yet); folding tick features into the current loop.

---

### 2026-11-08: desk v2 after the three-lens review; v1 numbers withdrawn
- **Decided:** the mock desk's first version was reviewed by three independent agents (timing, economics/overfitting, independent re-implementation) before its number went into the report. It implemented its spec exactly and had no look-ahead, but: fills were booked at the close mid (hiding intra-bar adverse selection: same-bar corr(taker sell-buy, r_j) = -0.66); fills and the limit stretch were uncapped (a 2024-01-03 flash crash let the desk absorb $2.2M in a minute and reach 5.45 N0 against a stated limit of 3, one day being a quarter of a two-month sample's value); z carried a week-long lean that earned through the BTC hedge leg; fills continued through stale level1 runs at a frozen mid; and the value scaled with the unsearched risk budget. Version 2 fixes all of these (taker-side VWAP fill prices, $200k per-side per-minute cap, stretch <= 1.5 L, fills masked on stale bars, trailing-demeaned z, per-leg attribution, per-limit unit, delay profile, ex-top-5 |delta| days).
- **Result (2024 OOS, parameters re-chosen on 2023: k 0.25, s_max 0.8, z_in 1.5, tilt 0):** +0.0057 N0/day = +0.52 bps of fills = +6.3 bps/day per N0 of limit, CI [+0.0011, +0.0097], 64% of days, placebos +0.01 / -0.13 bps, ex-top-5 |delta| days +0.0074, alt leg +0.0084 vs hedge leg +0.0006, value flat for a forecast up to 15 min old and gone at 240 min; L = 2/3/5 gives 5.0/6.3/5.6 bps per N0 of limit; h60 forecast +0.61 bps (placebo -0.01). The v1 figures (+0.80 / +0.96 / +1.43 bps) are withdrawn; the v1 runs stay in the registry marked superseded.
- **What the report now says:** the desk metric is exploratory and post hoc; the pre-registered standalone result (fails at costs) leads the section; the value is small, real, hour-scale, proportional to the risk budget, and rests on 2024 (selection year positive at every grid point but not significant).

### 2026-11-07: scope change: the model retrained at h = 15 and h = 60; headline stays h = 5
- **Decided (Ethan: "don't stop looking and minorly changing the scope"):** the seven-feature ridge was retrained on y(t,15) and y(t,60) with purge = h. Median daily rank IC 2023 / 2024: h5 0.038 / 0.047, h15 0.061 / 0.058, h60 0.070 / 0.069. Through the corrected desk (v2, see 2026-11-08) on 2024 the h60 forecast is worth +0.61 bps of fills vs +0.52 for h5, both with clean placebos once z is demeaned (the v1 desk's +0.60 bps h60 placebo was the undemeaned lean).
- **Headline stays h = 5** because it was pre-registered and the longer horizons were run after the 2024 h5 results were seen. The selection year on its own picks h = 60; that is the recommendation for the rest of the project, subject to the 2025 holdout.
- **Also tried:** one BTC hedge for the three-name book (+0.82 vs +0.80 bps, 67 vs 72 hedge trades a day): kept as a sensitivity, not as the headline.

### 2026-11-07: judging metric changed: value of the forecast to a desk with a book (reverses the 2026-11-05 "cumulative net PnL of the hedged position")
- **Decided (Ethan):** "mock an execution or broker / mm desk that has a book, where hedging isn't always new." The economic value of the forecast is the net PnL of a mock market-making desk that uses the forecast to shade its quotes minus the same desk without it, on the same observed taker flow (`python/notset/eval/desk.py`).
- **Why:** the standalone hedged position earned +8,275 bps mid-to-mid on 2024 and lost 146,869 bps after fees because it round-trips four fills every five minutes against a 1-2 bps edge; 90-97% of the cost is fees (`output/tables/diag_cost_decomposition.csv`). The signal is real but small and slow (the catch-up accrues for ~2 h while the forecast decays in ~10 min), so its buyer is a desk that trades anyway. This is a change to the pre-registered judging metric (`docs/EVALUATION.md` section 6) and is reported as such; the standalone result stays in the report as the diagnosis (section 6.1).
- **Desk design, fixed before any run:** f = 2% of taker flow, N0 = $1M, inventory limit L = 3, hedge band T = 0.25, inventory skew 0.5, skew cap 0.8; only (k, s_max, z_in, tilt) chosen on 2023 (24-point grid, all logged). Fees: maker 1 bps, taker 3.5 bps (Ethan: "a VIP tier"), retail 2/5 reported as sensitivity.
- **Ruled out:** trading the extremes with 1-2 h holds as a standalone strategy (positive only under maker-fill assumptions on the alt leg); keeping the negative standalone plot as the headline; reframing without a new number.
- **Result:** the first version's 2024 number (+0.80 bps of fills) was withdrawn after review; the corrected desk gives +0.52 bps of fills = 6.3 bps/day per N0 of limit (see 2026-11-08 and the report section 6.4).

### 2026-11-07: D11 the 2025 holdout stays closed for Milestone 1
- **Decided (Ethan):** Milestone 1 reports the 2024 walk-forward only. `notset.io.guard` raises on any 2025 read unless `NOTSET_HOLDOUT=1`, which only `/holdout` sets. `python/scripts/coverage.py` read 2025 for row and carryover counts only (no prices or returns), for the data chapter.

### 2026-11-07: D10 loop rule applied; verdicts live in a separate registry line
- **Decided:** keep a change only if median daily rank IC improves by more than its bootstrap s.e. and net PnL after delay is not worse; an execution-only change (no effect on the IC by construction) is judged on net PnL alone. Because registry lines are never edited and the verdict is known only after the run, verdicts are appended as their own line (`..._retro_loop1`).
- **Outcome:** 4 iterations approved by Ethan in advance, 2 kept (clip target at +/-5; 1.5 sd no-trade band), 2 rejected (drop btc_vol; ETH-minus-BTC feature). Final Milestone 1 model: `config/spread_v3.yaml`.

### 2026-11-07: D3b outcome: BTC-only hedge stays the target
- **Result:** on the 2024 walk-forward the two-factor target (BTC + leave-one-out alt index) had median daily rank IC 0.037 vs 0.040 for BTC-only, and lower mid-to-mid PnL, before paying for the extra legs. The pre-registered target stands.

### 2026-11-07: D9 outcome: alpha = 1
- **Result:** 2023 walk-forward, alpha 0.1 / 1 / 10: median daily rank IC 0.035 / 0.038 / 0.036. Note: the first implementation scaled the penalty so small that the grid was effectively OLS (found by the leakage audit); fixed to per-row units before the selection runs.

### 2026-11-07: D4 consequence: Ethan asked Claude to write the Python research layer
- **Decided (Ethan):** "let's go into python research"; `python/notset/` (io, features, target, eval) and the scripts were written by Claude with the leakage-auditor review applied before any result went into the report. Ethan reviews the report and confirms the LEARNINGS lines.

### 2026-11-06: D7 tails: trailing z-score on the fit window, clipped at +/-5
- **Decided:** every feature is standardized with the fit window's mean and std (nothing from the test block) and clipped at 5 standard deviations. One rule for all features.
- **Ruled out for now:** cube-root transform (candidate loop iteration), trailing percentile winsorization (noisy on a 60-day window).

### 2026-11-06: D6 first feature set: 7 features
- **Decided:** `btc_ema3_15`, `gap15`, `gap60`, `own_ema3`, `tib`, `tib_diff`, `btc_vol`. Max pairwise |corr| 0.62 on 2023.
- **Why:** 2023 evidence (`output/tables/feature_target_corr.csv`): gap15/gap60 median daily rank IC -0.05 to -0.06, own_ema3 and tib -0.03, tib_diff -0.02, btc_ema3_15 +0.02 for XRP and DOGE, btc_vol +0.02. ETH EMAs are 0.83 correlated with the BTC ones; `bib` and `relvol` show no signal.
- **Loop candidates:** eth-minus-btc EMA difference, bib, relvol, cbrt tails, trade-close fill (D12), alt-index-minus-BTC feature.

### 2026-11-06: beta window W = 7 days
- **Decided:** from the 2023 exposure test (`output/tables/exposure_test.csv`): 1-day betas move 0.25-0.33 per day, 7-day 0.06, 30-day 0.02; residual cross-correlation 0.270 / 0.277 / 0.284. 7 days is within 0.007 of the best tracking with a hedge ratio that is cheap to maintain.

### 2026-11-06: D3b hedge: compare the two hedges on the 2024 walk-forward, don't pick a priori
- **Decided (Ethan):** "have multiple suggestions and compare performance, this should be the first thought". Both targets run through the same walk-forward and cost stages: (1) BTC-only, e_j = r_j - beta_j r_BTC, two legs; (2) BTC + leave-one-out alt index, e_j = r_j - b1 r_BTC - b2 r_IDX(-j), traded with all legs. Each is a logged run; the comparison is a reported result, and the pre-registered target (1) stays the headline unless (2) wins on both median daily rank IC and net PnL.
- **Evidence that motivated it:** on 2023 the BTC-only residuals of SOL/XRP/DOGE have pairwise correlation 0.27 (first-PC share 0.52); the second leg removes it (-0.03, 0.37) and adds 0.05-0.10 of R^2, but the alts then load 0.6-1.0 on the index and only 0.25-0.6 on BTC.

### 2026-11-06: D9 ridge penalty picked on 2023 only, from {0.1, 1, 10}
- **Decided:** run the 2023 walk-forward with alpha in {0.1, 1, 10} on standardized features, keep the best median daily rank IC, freeze it for 2024. Logged in the registry as three `select` trials.
- **Ruled out:** a fixed a-priori alpha (no protection if features stay collinear); nested selection at every refit (slower, moving penalty hides weight instability).

### 2026-11-06: D8 walk-forward is 60-day fit, 7-day test, refit weekly, purge h bars
- **Decided:** fit on the trailing 60 days, purge 5 bars, forecast the next 7 days, slide by 7 days; about 52 refits over 2024. Inside the Lecture 9 range (7-90 days, 6-168 h).
- **Why:** HW3 found longer windows more stable up to 90 days; 60 keeps the first 2024 test week fit on Nov-Dec 2023 rather than a quarter-old regime.
- **Ruled out:** 90-day (first test week fit on Oct 2023); 30-day with daily refit (HW3 instability, 335 refits).

### 2026-11-06: target parameters: beta window chosen by the 2023 survey among 1, 7, 30 days; vol scale is a 1-day EWMA
- **Decided (Ethan):** do not fix the beta window a priori. The 2023 hedge exposure test runs beta_j with W = 1, 7, 30 days (1440, 10080, 43200 bars, bars up to t-1) and the window with the lowest residual cross-correlation and the most stable beta is frozen for 2024. sigma_e_j(t) is an EWMA of e_j^2 with a 1-day half-life, trailing (my reading of the choice; the question offered the 1-day half-life with every option).
- **Why:** betas moved a lot in 2024; the selection year should show which window tracks them without going noisy.
- **Consequence:** the target code takes W as a parameter; `config/*.yaml` records the chosen W.

### 2026-11-06: D12 stale level1 bars are masked, not filled
- **Decided:** r_j(t) is NaN on any bar with `carryover != 0` or a NaN mid, and on the bar after. The 99%-live trade and book rows are not used to fill them for Milestone 1.
- **Why:** simplest, matches the gotchas, and the audit measured a 0.002-0.006 effect on correlations. Filling from trade `close_price` adds bid-ask bounce and another look-ahead surface.
- **Later:** the trade-close fill can be tried as one improvement-loop iteration, so its effect is measured.

### 2026-11-06: Ethan asked Claude to finish the q data layer
- **Decided (Ethan):** "fix everything data stage related". Claude completed `q/schema/bars.q` (column lists generated from the real headers), `q/load/bars.q`, `q/init.q`, fixed the split delimiter in `q/lib/cfg.q`, normalised line endings to LF, and ran the full load. The q layer stays Ethan's to extend.

### 2026-11-05: HDB `date` partition = source file date
- **Decided:** in `l1bar`, `tradebar` and `bookbar`, `date` is the date in the raw file name. One raw file becomes one (date, sym) slice.
- **Why:** the loader is a per-file append and row counts reconcile 1:1 with the raw-file coverage audit (`python/scripts/coverage.py`). For level1 and trade, the file date is the day the bar starts in, which is the right day for daily IC and PnL.
- **Consequence:** a level1/trade file dated D holds `ts_end` D 00:01 .. D+1 00:00, a book file dated D holds D 00:00 .. D 23:59. So `date` is not `date$ts_end` on the midnight bar, and one book row per day joins to a level1 bar in the previous partition. `bars[]` has to select on `ts_end` as well as `date`, and research code takes the day from `date`, never from `ts_end`.
- **Ruled out:** partitioning on the calendar date of `ts_end` (loader has to move a row per file across partitions; daily grouping puts the last return of each day on the next day).

### 2026-11-05: D4 Python waits for PyKX on the HDB; no temporary CSV reader
- **Decided:** `notset.io` reads bars only through PyKX from the HDB built by Ethan's q loader. No interim CSV backend.
- **Why (Ethan):** one code path, and the q -> Python claim holds from the first figure.
- **Consequence:** step 3 onward starts when the HDB loads. The q loader is the critical path for the Monday deadline.
- **Not covered by this:** `python/scripts/coverage.py` reads the raw files directly. It audits the archive as delivered and is the reference the loader's row counts are checked against; it is not a research data path.

### 2026-11-05: D3b second hedge (volume-weighted index) not decided yet; decide on evidence
- **Deferred (Ethan):** the hedge shouldn't be chosen before the exposure is measured. "The whole point of a hedge or limited exposure trade is to understand the true exposure first then decide."
- **Next:** an exposure test on 2023 (selection period) goes into the step 3 survey, and D3b is decided from its output. The test design is put to Ethan at the start of step 3.

### 2026-11-05: D3a ETH is a leader; one untuned ETH-as-follower check is reported
- **Decided:** followers in the fit and the improvement loop stay SOL, XRP, DOGE. ETH-as-follower is run once with the settings chosen on those three and reported as a robustness row.
- **Why:** keeps the trial count down and ETH's return EMA a clean leader feature, while still showing the result on the most liquid, cheapest spread.
- **Ruled out:** ETH as a fourth follower inside the fit (the lead is likely weakest there and it would dilute the median daily rank IC); dropping ETH as a follower entirely.

### 2026-11-05: Milestone 1 runs on the full stack; set it up this week
- **Decided:** follow `docs/SETUP.md` end to end (WSL2, KDB-X, Miniforge + PyKX, Java) before step 2, rather than running Milestone 1 on Windows Python with q deferred.
- **Why (Ethan):** Milestone 1 should show the whole q -> Python -> Java pipeline runs end to end. That is the credibility check before tick data gets wired into the same slots.
- **Ruled out:** a Windows-only shortcut for the milestone. D4 (Python access while the q loader is written) stays open until q is installed and is settled at step 2.

### 2026-11-05: D1 combined document is markdown in `reports/milestones/milestone-1/`, exported at submission
- **Decided:** the milestone document is markdown in the repo; figures are linked from `reports/milestones/milestone-1/figures/`, each produced by a script in `python/scripts/`. Export to Word or PDF with pandoc on submission day.
- **Why:** the document can't drift from the code; a rerun of a script updates the figure in place.
- **Ruled out:** a Word document as for the homeworks (hand-pasted figures, binary outside git diffs).

### 2026-11-05: D5 no outside data requested before Milestone 1
- **Decided:** nothing requested from the course this week.
- **Why (Ethan):** keep the four days on the core result. Funding rates (needed for the last backtest stage in `EVALUATION.md`) and a second venue are revisited after Milestone 1, once Hank's capture is described.
- **Ruled out for now:** funding rates, open interest, Hyperliquid, Bybit/OKX.

### 2026-11-05: Milestone 1 due Mon Nov 9; plan in `reports/milestones/milestone-1/PLAN.md`
- **Decided:** one step per VS Code session; open choices are numbered D1-D11 in the plan and logged here when Ethan decides them.

### 2026-11-05: Target is the BTC-hedged spread, not the raw return
- **Decided:** forecast the follower's forward move net of beta * BTC, vol-scaled, h = 5 min primary (1 and 15 reported). Followers SOL, XRP, DOGE; leaders BTC, ETH. Definitions in `THESIS.md`.
- **Why (Ethan):** the signal has to be interpretable and pitchable to a desk. Raw short-horizon returns are close to unpredictable; a spread or difference forecast with an execution strategy on top is a view a desk can take. If it carries over to raw returns, that's a bonus.
- **Ruled out for now:** cross-venue basis and perp-spot basis (no data yet; revisit once Hank's tick capture is described).

### 2026-11-05: TWAP execution metric and simulated parent orders retired
- **Decided:** reverses the 2026-10-01 execution-desk pitch. No synthetic parent orders.
- **Why (Ethan):** simulated orders carry a lot of bias and assume a distribution of order activity. Feature distributions matter more.
- **Removed:** `ideas/02-execution-timing-signal.md`, `ideas/README.md`, `ideas/_TEMPLATE.md`, `docs/RESEARCH_PLAN_TEMPLATE.md` (all in git history). `ideas/01` became `docs/THESIS.md`.

### 2026-11-05: Metric and final plots
- **Decided:** fit and run the improvement loop on **median daily rank IC**; judge on **cumulative net PnL** of the hedged position (costs on both legs, staged as in Lecture 9).
- **Final plots:** cumulative OOS net PnL over time vs a baseline is required; feature distributions alongside.

### 2026-11-05: Stack laid out in full now; q is Ethan's
- **Decided:** q -> Python -> Java framework stays, even without tick data yet. Ethan writes the q layer himself, so Claude proposes and reviews q but doesn't write it unless asked. Hank's tick capture (3-4 weeks so far) gets an empty slot in `DATA.md` and the q schema, wired up later.
- **Also:** all project code lives in this repo. Homework notebooks aren't imported; their lessons are rebuilt here (gotchas carried into `CLAUDE.md`).

### 2026-11-05: Group and roles
- **Decided:** group name HEX Research. Ethan Tait CRO/COO, Hank Rugg CTO/COO (course group-formation sheet).

### 2026-11-05: Claude Code setup for the research loop
- **Decided:** `CLAUDE.md` + project subagents (`.claude/agents/`) + skills (`.claude/skills/`). Every run appends to `experiments/registry.jsonl`; lessons go in `research/LEARNINGS.md`. Both are read at the start of each session, which is how later sessions learn from earlier runs.

### 2026-10-01: Live signal computed in q, in the same pass as data processing
- **Decided:** in production, data is received and processed in q and the signal is computed in that same pass, then pushed to the Java engine.
- **Why (Ethan, from a q → Python → Java desk stack):** the long part is market-data latency; computing the signal is quick by comparison. We measure q compute time per update to back this up.

### 2026-10-01: Benchmarks reported side by side
- **Decided:** report execution improvement against arrival price (implementation shortfall, primary), the baseline TWAP schedule, and interval VWAP.
- **Why (Ethan):** in practice the benchmark is client-dependent; there's no single standard.

### 2026-10-01: Pitch the signal to an execution desk; ideas narrowed to 01 + 02
- **Decided:** keep `ideas/01` (cross-asset leadership, the signal engine) and add `ideas/02` (execution-timing application). Ideas 02-06 from 2026-09-24 removed (still in git history), including the parked adverse-selection file.
- **Why:** the Signal Research Plan asks for a use case, a buyer and a final deliverable metric. An execution desk is the best-fit buyer: it pays spread and fees anyway, so the signal only has to improve timing, and success (slippage saved vs benchmark on simulated parent orders) is verifiable with market data alone, without client data.
- **Also:** scope toned down: the 5 homework symbols (+HYPE if available), trades + BBO, no L2, taker-only fills in the core.
- **Not observed in practice (Ethan):** exactly how an execution algo consumes a short-horizon signal. Schedule tilt is our design choice and is stated as such.

### 2026-09-24: Stack fixed: kdb+/q → Python → Java
- **Decided:** q for tick storage and querying, Python for research, Java for event-driven execution simulation.
- **Why:** tick data needs event-time joins at scale, which is q's strength. The split mirrors a production trading-desk stack, which is part of what we want to learn.
- **Condition on Java:** it enters once a strategy needs state, latency or an order lifecycle. Vectorized mid-to-mid tests stay in Python/q.
- **Licensing:** KDB-X Community Edition (free, per-person licence), OpenJDK 21, conda Python.

### 2026-09-24: Repo is public
- **Consequence:** no data, no licence files, no credentials in git, ever (see `CONTRIBUTING.md`).

### 2026-09-24: Evaluation protocol before thesis
- **Decided:** success metrics are shared across ideas and fixed before looking at OOS results (`EVALUATION.md`).
- **Why:** avoids the event trap and stops the thesis drifting toward whatever the data shows.

### 2026-09-24: Adverse-selection / protective-skew framing parked
- **Why:** success can't be verified without client or fill data, and it turns the project into a maker-desk simulation built on many assumptions. See `ideas/06-adverse-selection-protective-skew.md` (removed 2026-10-01, still in git history).

---

## Open questions

- [ ] What Hank's tick capture contains: venues, symbols, tables, date range, format
- [ ] Milestone 1 decisions D1-D11 (`reports/milestones/milestone-1/PLAN.md`)
- [ ] Common event grid for tick data: fixed interval (100ms / 250ms / 1s) vs refresh-time
- [ ] Maven vs Gradle for `java/`
