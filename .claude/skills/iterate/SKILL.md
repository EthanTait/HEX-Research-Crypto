---
name: iterate
description: Run one iteration of the improvement loop (Milestone 1 step 5) - critic proposes, Ethan picks, leakage check, run on the 2024 walk-forward, keep or reject by the pre-agreed rule, log the lesson.
disable-model-invocation: true
---

# One improvement-loop iteration

The keep/reject rule is decision D10 in `reports/milestones/milestone-1/PLAN.md`. If D10 isn't logged in `docs/DECISIONS.md` yet, stop and settle it with Ethan first.

1. **Propose.** Run the `research-critic` agent. Show Ethan its 2-3 candidates (one line each plus the hypothesis) and the trial count so far. Ask him to pick one, or to suggest his own.
2. **Implement** exactly one change: a new config in `config/` (copy the current best, bump the name), plus code changes only if the change needs them.
3. **Check.** Run the `leakage-auditor` agent on the diff. Fix anything severe before running.
4. **Run.** Run the `experiment-runner` agent on the new config. The 2024 walk-forward only.
5. **Decide** by the D10 rule. Show the before/after table (median daily IC with CI, % days IC > 0, net PnL, Sharpe by cost stage) and the verdict: kept or rejected.
6. **Learn.** Draft one line for `research/LEARNINGS.md` (what changed, the result, the likely reason). Ethan confirms or edits it before it's written.
7. **Plot.** Regenerate the metric-across-iterations figure (every trial, kept and rejected, marked differently) with its script.

Never open the holdout here. Don't commit unless asked.
