# q/ (data layer)

**Written by Ethan.** Claude can propose and review q here, but doesn't write it unless asked. The contract Python relies on is in [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

```
q/
├── schema/    # table definitions: l1bar, tradebar, bookbar (1-min, now); trade, quote (ticks, later)
├── load/      # raw .csv.gz -> partitioned HDB
├── lib/       # query functions research calls: bars, coverage, ... (grid, markout, flow for ticks)
└── init.q     # loads schema + lib, mounts data/hdb; entry point for PyKX and the IDE
```

## Milestone 1 slots

- [x] `schema/bars.q`: the three 1-min tables, course column names kept (2026-11-06)
- [x] `load/bars.q`: course archive -> `data/hdb/` (run from the repo root: `q q/load/bars.q`, then `loadAll[`l1bar;2023.01.01;2025.11.30]` and the same for `tradebar`, `bookbar`; about 7.5 min, 6.8 GB)
- [x] `lib/bars.q`: `bars[tbl; syms; d0; d1; cols]`, `coverage[tbl; d0; d1]`
- [x] `init.q`: `q q/init.q` from the repo root mounts the hdb (and moves the process into `data/hdb`, so use absolute paths after it)
- `lib/cfg.q` reads `config/local.yaml` (flat `key: value` lines under `paths:`), so no path is hardcoded

Acceptance (passes 2026-11-06): the q `coverage[]` table equals `output/coverage/by_year.csv` from `python/scripts/coverage.py` on every (sym, year) cell for all three tables.

## Tick slot (Hank's capture, later)

- [ ] `schema/tick.q`: `trade`, `quote` adjusted to the capture's actual fields
- [ ] `load/tick.q`

## Rules

- Research code calls functions in `lib/`, not ad-hoc queries against raw tables.
- Paths come from `config/`, never hardcoded.
- Never write into `data/raw/`.
