# CLAUDE.md

Guidance for Claude Code sessions in this repo. Read this, then `research/LEARNINGS.md` and the last ~10 lines of `experiments/registry.jsonl`, before proposing anything.

## What this is

HEX Research (Ethan Tait, Hank Rugg), group project for a Fordham MSQF crypto / algo trading course. The thesis is a **BTC-hedged spread forecast** for alt perps (`docs/THESIS.md`). The current deliverable is **Milestone 1, due Mon 2026-11-09**: `reports/milestones/milestone-1/PLAN.md` is the source of truth for what to do next.

## How Ethan works (follow this)

- **Ethan makes the decisions.** For every open choice (the `D#` items in the plan, or anything new), give 2-3 options with a recommendation and the trade-off, ask him (AskUserQuestion when available), and log the answer in `docs/DECISIONS.md` before building on it. Don't pick silently.
- One plan step per session. Finish it, tick the checkbox in `PLAN.md`, say what's next.
- Equations in plain ASCII (`e_j(t) = r_j(t) - beta_j(t) * r_BTC(t)`); LaTeX doesn't render for him.
- Tie methodology back to his MSQF coursework and the lectures by name: IS/OOS and factor models (Quant Methods), PCA / Kalman / VAR (Time Series Econometrics), backtesting logic (Risk Management), Lecture 4/5/9 slides.
- Code comments: terse, lowercase, why not what. **No docstrings** (he strips them). No essay-style markdown in notebooks.
- **q is Ethan's.** Don't write q unless he asks; you can propose interfaces and review his q. Hank owns wiring his tick capture into the data slot.
- Don't commit or push unless asked. Ethan usually commits himself.

## Delegation

Project subagents live in `.claude/agents/`. Use them when the work fits; keep conclusions, not file dumps.

| Agent | Use it for |
|---|---|
| `data-auditor` | coverage, carryover, gaps, grid alignment; fills the data-chapter table |
| `feature-surveyor` | the feature-quality and collinearity survey (distributions, corr matrix, corr with target, lag profile) |
| `leakage-auditor` | fresh-eyes review of any diff that touches features, targets, normalizers, splits or the backtest. Give it the code, not your conclusion |
| `experiment-runner` | run one config through the walk-forward, append to the registry, report vs baselines |
| `research-critic` | read the registry + LEARNINGS, count trials, flag overfitting, propose the next 2-3 changes |

Skills in `.claude/skills/`: `/m1-step` (next plan step), `/iterate` (one improvement-loop iteration), `/retro` (distill new runs into LEARNINGS), `/holdout` (guarded, logged opening of the clean OOS).

## How the project learns from its own runs

- Every run that produces a metric appends one JSON line to `experiments/registry.jsonl` (schema in `experiments/README.md`), from code, including rejected and failed runs. Never edit or delete lines.
- `research/LEARNINGS.md` holds the distilled lessons. Lines get added through `/retro` or `/iterate`, and Ethan confirms each one.
- Before proposing a change, check both: don't re-run something already rejected unless the reason it failed has changed, and say how many trials have been run so far (multiple-testing risk).
- New data gotchas found during a run get added to the gotchas list below, with Ethan's OK.

## Repo map

- `docs/`: THESIS, DATA (data chapter), EVALUATION (pre-registered metrics), ARCHITECTURE (q -> Python -> Java contract), DECISIONS (log), SETUP
- `python/notset/`: package (io, features, models, eval); `python/scripts/`: one entry point per figure or result; `python/tests/`: alignment and look-ahead asserts
- `q/`: data layer (Ethan). `java/`: strategy replay (not needed for Milestone 1)
- `config/*.yaml`: one per experiment; `config/local.yaml` (gitignored) has machine paths
- `output/` (gitignored): figures and run artifacts. Chosen figures are copied into `reports/.../figures/`
- `data/` (gitignored): course archive in `data/raw/fordham`, ticks in `data/raw/tick`, HDB in `data/hdb`

## Research rules (from Lecture 9 and `docs/EVALUATION.md`)

- Splits: 2023 selection and survey, 2024 sliding-window walk-forward (the improvement loop lives here), **2025-01 to 2025-11 clean holdout, only via `/holdout`**.
- Every normalizer is trailing: z-scores, winsor bounds, betas, vol. No full-sample statistics in anything that feeds a forecast.
- Purge h bars between fit and test windows. Overlapping 5-min targets inflate t-stats: use daily metrics and day-block bootstrap.
- Linear (ridge) first. Collinearity threshold 0.7. 5-8 features. A naive baseline on every chart.
- Correlations above ~5% with a 1-5 min forward target are suspicious: check for look-ahead first.
- Costs on both legs of the hedge: about 5 bps taker per side plus half spread. Backtest stages: mid-to-mid -> fees + spread -> one-bar delay.
- Annualize with 525,600 minutes per year (24/7 market).

## Data gotchas (verified in the homeworks; keep this list current)

- `carryover >= 1`: the bin repeats the previous one (fake zero return), and the next bar carries the whole gap. `carryover == -1`: fields NaN. Mask the stale bar **and the bar after**. **Never forward-fill returns** across these runs (the course's sample script does, and it biased BTC-SOL EMA correlation from 0.72 to 0.63).
- `ts_end` is epoch ms UTC at the **end** of the bin; a naive group-by-date puts the last bar on the next day.
- Put all names on **one common 1-min grid** before shifting; per-symbol shifts turn missing days into fake multi-day returns.
- Book rows are snapshots just after `ts_end`: shift book features 1 bar.
- EMAs hold their value through stale runs; mask derived features where the name isn't live.
- The course's `ret_ema_N` example lags the N-min return an extra N bars, which destroys the signal. Build return EMAs from 1-min returns.
- Known missing days: all datasets 2025-11-26..28; `level1_1min` ETH+SOL 2024-01-13..14, SOL+XRP 2025-11-24.

## Environment

WSL2, conda env `notset` (Python 3.12, numpy, pandas, scipy, statsmodels, scikit-learn, matplotlib, pyyaml, pykx), KDB-X Community, OpenJDK 21. See `docs/SETUP.md`. Data paths come from `config/local.yaml`, never hardcoded.
