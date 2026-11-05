# Decision log

Newest entries at the top. One entry per decision: what was decided, why, and what was ruled out. If a decision is reversed, add a new entry rather than editing the old one.

---

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
