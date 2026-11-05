# experiments/

`registry.jsonl` is the project's memory of every run: one JSON object per line, appended by code (`notset.eval`), never edited by hand. Failed and rejected runs are logged too, so the number of trials is always visible. Run artifacts (predictions, figures) go in `experiments/runs/<run_id>/`, which is gitignored.

## Line schema

```json
{
  "run_id": "2026-11-07T14:03:11Z_spread_v3",
  "parent_run_id": "2026-11-07T11:40:02Z_spread_v2",
  "config": "config/spread_v3.yaml",
  "git_hash": "abc1234",
  "dirty": false,
  "split": "walk_forward",
  "dates": {"start": "2024-01-01", "end": "2024-12-31"},
  "followers": ["SOLUSDT", "XRPUSDT", "DOGEUSDT"],
  "horizon_bars": 5,
  "change": "add follower-minus-BTC trade imbalance",
  "metrics": {
    "ic_median_daily": 0.0,
    "ic_ci95": [0.0, 0.0],
    "ic_pos_days_pct": 0.0,
    "pnl_net_bps": {"mid": 0.0, "fees_spread": 0.0, "delay_1bar": 0.0},
    "sharpe": {"mid": 0.0, "fees_spread": 0.0, "delay_1bar": 0.0},
    "by_follower": {"SOLUSDT": {"ic_median_daily": 0.0}}
  },
  "baselines": {"zero": {}, "static_btc_leads": {}, "best_feature": {}},
  "verdict": "kept | rejected | baseline | n/a",
  "status": "ok | failed",
  "notes": ""
}
```

`split` is one of `select` (2023), `walk_forward` (2024), `holdout` (2025, only via `/holdout`). Fields can be added later; existing ones keep their meaning.
