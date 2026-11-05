# Thesis: BTC-hedged spread forecast for alt perps

**Status:** chosen for Milestone 1 (2026-11-05). Earlier candidate ideas, including the TWAP execution-timing pitch, are in git history (`git log --diff-filter=D --name-only`).

**One line:** forecast the next few minutes of an alt perp's move *net of BTC* (its BTC-hedged spread), using what BTC, ETH and the alt itself have just done. The forecast tells a desk whether the alt is about to catch up to BTC or snap back.

## Why a spread and not a raw return

- Raw short-horizon returns are mostly common crypto factor and close to unpredictable. The hedged spread removes most of that factor, so what's left is the part a lead-lag effect could plausibly explain.
- It is interpretable: "SOL hasn't caught up to BTC's last move yet" is a sentence a desk understands.
- It avoids the bull-market trap (Lecture 9 "Alpha vs Beta"): a long-biased model looks good in 2023-2024 on raw returns. A hedged spread forecast can't win by holding beta.
- If the result turns out to carry over to raw returns, that's a bonus, not the target.

## Who would use it

| Buyer | How they use the forecast |
|---|---|
| Relative-value / stat-arb desk | Trade the spread directly: long alt, short beta * BTC (or the reverse), sized by the forecast |
| Execution desk holding hedged alt exposure | Decide whether to put on or take off the alt leg before or after the BTC hedge |
| Market maker in alts | Skew alt quotes when BTC has moved and the alt hasn't (needs tick data to verify; not a Milestone 1 claim) |

The deliverable is the **forecast**. A strategy that trades it is the demonstration that the forecast is worth something after costs (Lecture 9: "A rule backtest is not signal research. The deliverable is a forecast").

## Definitions (ASCII, 1-min bars)

```
r_i(t)      = log(mid_i(t)) - log(mid_i(t-1))       NaN on stale bars and the bar after
beta_j(t)   = trailing OLS beta of r_j on r_BTC, window W, using data up to t-1 only
e_j(t)      = r_j(t) - beta_j(t) * r_BTC(t)         hedged (residual) return of follower j
S_j(t,h)    = e_j(t+1) + ... + e_j(t+h)              forward hedged spread move over h bars
y_j(t,h)    = S_j(t,h) / sigma_e_j(t)                vol-scaled target; sigma_e_j trailing only
```

- Followers: SOL, XRP, DOGE. Leaders: BTC (hedge and leader) and ETH (leader). Whether ETH is also a follower is decision D3 in the Milestone 1 plan.
- Primary horizon h = 5 bars; 1 and 15 reported alongside. One horizon is optimized; the others show continuity (Lecture 9: variable horizons invite overfit).
- The betas may be delayed (Lecture 9): beta is estimated with lagged BTC terms as a check, and the lag structure is reported.

## Hypotheses

- **H1:** a combination of leader-move, catch-up and flow features predicts y_j(t,5) out of sample better than the best single feature (median daily rank IC).
- **H2:** the dynamic forecast beats a static "BTC leads, alt catches up by beta" forecast (Diebold-Mariano on OOS loss differentials, `EVALUATION.md` section 4).
- **H3:** after realistic costs on both legs, cumulative OOS PnL of the hedged position beats the baseline.
- **Null result:** the lead sits entirely inside the same 1-min bar (lag-0 cross-correlation), so bars can't see it. That is still a result and motivates the tick-data extension.

## Extensions (after Milestone 1)

- **Leadership rotation:** who leads whom per window, and whether that persists more than a circular time-shift null.
- **Market vs idiosyncratic flow:** split trade imbalance into the common part and each coin's own part, and test which part leads. Common flow is probably priced instantly; idiosyncratic flow may spread with a lag.
- **Tick data (Hank's capture):** the same target at second horizons, and a genuinely forward OOS period (late 2026) that the 1-min archive (ends 2025-11-30) never saw.
- **Cross-venue basis:** if the capture covers more than one exchange, the same-coin price gap between venues is a second spread target.

## Known traps

- Stale bars look like lags. Mask carryover bars and the bar after before any return.
- A follower's own bounce-back can look like catching up. Keep the follower's own past return as a control feature.
- Overlapping 5-min targets sampled every minute inflate t-stats. Use daily metrics, block bootstrap by day, or non-overlapping samples.
- A few crash days can carry the whole result. Report per-day IC and rerun without the top 5 vol days.
- Testing many pairs, lags and windows finds something by chance. Every run is logged in `experiments/registry.jsonl` so the number of trials is visible.

## Links to coursework

- Lecture 4/9: trade imbalance, EMA features, cross-correlation block structure, sliding-window optimization, collinearity, realistic backtest stages.
- HW3: 5-name common grid, rolling betas, `rel_value`, sqrt-volume index. The ideas carry over; the code is rebuilt inside this repo.
- MSQF Quant Methods: factor-model residuals and IS/OOS discipline. Time Series Econometrics: Kalman time-varying beta (extension), VAR for lead-lag. Risk Management: backtesting logic (Kupiec-style hit-rate checks) for forecast calibration.
