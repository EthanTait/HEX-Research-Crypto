# config/

One YAML file per experiment, read by q, Python and Java. Machine-specific paths go in `local.yaml` (gitignored).

Example shape for Milestone 1 (fields will settle as decisions D3-D9 are made):

```yaml
name: spread_v0
leaders: [BTCUSDT, ETHUSDT]
followers: [SOLUSDT, XRPUSDT, DOGEUSDT]
hedge: BTCUSDT
dates:
  select: {start: 2023-01-01, end: 2023-12-31}     # feature selection and survey
  walk_forward: {start: 2024-01-01, end: 2024-12-31}
  holdout: {start: 2025-01-01, end: 2025-11-30}    # opened once, logged
target: {horizon_bars: 5, report_horizons: [1, 5, 15], vol_scale: true}
beta: {window_days: TBD}
walk_forward: {window_days: TBD, refit_hours: TBD, purge_bars: 5}
features: [TBD]
model: {type: ridge, alpha: TBD}
costs: {taker_bps: 5.0, half_spread: observed, legs: 2}
```

`local.yaml` example (not committed):

```yaml
paths: {raw_fordham: /path/to/fordham, hdb: data/hdb, output: output}
```

Results record the config file name and git commit hash that produced them.
