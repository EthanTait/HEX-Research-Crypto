---
name: holdout
description: Guarded, logged evaluation on the clean 2025 holdout. Only when Ethan explicitly asks to open the holdout, with the model frozen.
disable-model-invocation: true
---

# Open the holdout (once)

Lecture 9: "The holdout is used up the moment you look at it."

1. Count registry lines with `"split": "holdout"`. Tell Ethan how many times the holdout has been opened so far and for which configs.
2. Confirm with AskUserQuestion: which config is frozen, and that nothing will be tuned on the result. Stop if he doesn't confirm.
3. Check that the config and code are committed (clean `git status` for `python/notset/` and `config/`). Record the git hash.
4. Run the frozen config on 2025-01-01 to 2025-11-30 with `split: holdout`. The registry line must carry `"split": "holdout"`.
5. Report the same table as the walk-forward, next to the walk-forward numbers, and the cumulative net PnL chart vs the baseline. No changes to the model afterwards; any follow-up idea goes into LEARNINGS as untested.
