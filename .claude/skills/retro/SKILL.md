---
name: retro
description: Distill experiment runs logged since the last retro (manual or automatic) into research/LEARNINGS.md and propose updates to CLAUDE.md gotchas. Use after a batch of runs, at the end of a working session, or before a milestone write-up.
disable-model-invocation: true
---

# Retro: learn from the registry

1. Find the last `<!-- retro: <run_id> -->` marker in `research/LEARNINGS.md`. Read every registry line after that run id.
2. Run the `research-critic` agent on the full registry for the overfitting view.
3. Draft, for Ethan to approve:
   - New LEARNINGS lines: patterns across runs (what reliably helps or hurts, parameter stability, which follower or period drives results), each citing run ids.
   - Lines that are now wrong and should be struck through with the run that contradicted them (never deleted).
   - New data or code gotchas for the `CLAUDE.md` list.
   - Any open question that should become a `D#` in the plan or an entry in `docs/DECISIONS.md` open questions.
4. Write only what Ethan approves, then add a new `<!-- retro: <last run_id> -->` marker.
