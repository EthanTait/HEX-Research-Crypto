# Tick study (separate deliverable, decided 2026-11-09)

Hank has been capturing tick data (trades and quotes) since mid-October 2026 and will have about two months by the end of the course. This is a **separate pathway** from the 1-minute thesis: it does not feed the improvement loop, it does not touch the 2024 walk-forward or the 2025 holdout, and it is an extra deliverable only if it holds. If it does not hold, the 1-minute result stands on its own.

## Question

Does the BTC-hedged spread forecast work **quote by quote**, the way the desk we pitched it to would run it, rather than on 1-minute bars? Two parts:

1. **Forward test of the frozen 1-minute model.** Aggregate the ticks to 1-minute bars in q (same schema as `l1bar` / `tradebar`), run the frozen `spread_v3` model and the mock desk exactly as on 2024. The capture is a period the archive never saw, so this is the cleanest out-of-sample check we can make. About 60 daily observations: enough for a sign and a CI, not for tuning.
2. **Event-time version.** Recompute the features and the target on the quote stream (returns from mid updates, catch-up gap over the last N quotes or seconds, trade imbalance over a rolling window), score the forecast at second horizons, and run the desk in event time through the Java replay engine (`docs/ARCHITECTURE.md`, layer 3). The lag profile at second horizons is the first result: on 1-minute bars the BTC lead sits at lag 0, and this is where we find out whether ticks can see it.

## Rules

- Nothing here changes a decision made on the 1-minute data. Model, features and desk parameters are frozen before the first tick is read for part 1.
- Part 1 is opened once and logged, like the 2025 holdout (`/holdout` with the tick config).
- Part 2 is exploratory and says so: its own survey, its own registry lines (`split: tick`).
- Hank owns the data slot (`q/schema/tick.q`, `q/load/tick.q`, `docs/DATA.md` section 2); the pipeline code is shared.

## Layout (to be filled once the capture is described: venue, symbols, tables, dates, format)

```
reports/tick-study/
├── README.md               <- this file
└── PLAN.md                 <- steps, once the capture is described
config/holdout_tick.yaml    <- dates and the frozen model
q/schema/tick.q, q/load/tick.q, q/lib/tick.q   <- trade, quote, bars1m, grid, markout
```
