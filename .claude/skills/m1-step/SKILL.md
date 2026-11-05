---
name: m1-step
description: Pick up the next unfinished step of the Milestone 1 plan, put its open decisions to Ethan, log them, then do the step. Use at the start of a Milestone 1 working session.
disable-model-invocation: true
---

# Next Milestone 1 step

1. Read `reports/milestones/milestone-1/PLAN.md`, `docs/DECISIONS.md`, `research/LEARNINGS.md` and the tail of `experiments/registry.jsonl`.
2. Find the first step with unticked items. Tell Ethan in 2-3 lines which step it is, what it produces, and which `[submit]` items it covers.
3. For each open `D#` in that step: give 2-3 options, a recommendation and the trade-off, grounded in the lectures and his MSQF coursework. Ask with AskUserQuestion (up to 4 at once). Don't proceed past a decision he hasn't made.
4. Log every answer in `docs/DECISIONS.md` (newest at top: what, why, what was ruled out) and mark the `D#` as decided in `PLAN.md`.
5. Do the step. Delegate where it fits: `data-auditor` for step 2, `feature-surveyor` for step 3, `experiment-runner` for runs, and always `leakage-auditor` on any diff touching features, targets, normalizers, splits or the backtest before you report numbers.
6. Tick the boxes that are actually done in `PLAN.md`. Finish with: what was produced (files, figures), any number Ethan needs for the write-up, and the next step.

Don't commit or push unless Ethan asks.
