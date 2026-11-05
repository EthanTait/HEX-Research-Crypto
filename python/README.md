# python/ (research layer)

```
python/
├── notset/        # importable package
│   ├── io.py      # data access: PyKX wrappers around q/lib (temporary CSV backend if D4 says so)
│   ├── features/  # feature construction and transforms
│   ├── models/    # ridge first; Kalman beta, VAR later
│   └── eval/      # EVALUATION.md protocol: walk-forward, daily rank IC, bootstrap, DM, PnL stages
├── scripts/       # reproducible entry points, one per result or figure
├── tests/         # look-ahead and alignment asserts
└── notebooks/     # exploration only; clear outputs before committing
```

Rules
- If a notebook cell gets reused, move it into `notset/`.
- Every figure in `reports/` is produced by a script in `scripts/`, with the config file and git hash recorded.
- Every run with a metric appends to `experiments/registry.jsonl`.
- Figures go to `output/` (gitignored). Copy the chosen ones into `reports/.../figures/`.
- Comment style: terse, lowercase, why not what. No docstrings.
