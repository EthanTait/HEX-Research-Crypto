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

_(none yet)_

<!-- retro: none -->
