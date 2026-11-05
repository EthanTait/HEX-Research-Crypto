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

- [ ] `schema/bars.q`: the three 1-min tables, course column names kept
- [ ] `load/bars.q`: course archive -> `data/hdb/`
- [ ] `lib/bars.q`: `bars[tbl; syms; d0; d1; cols]`, `coverage[tbl; d0; d1]`

## Tick slot (Hank's capture, later)

- [ ] `schema/tick.q`: `trade`, `quote` adjusted to the capture's actual fields
- [ ] `load/tick.q`

## Rules

- Research code calls functions in `lib/`, not ad-hoc queries against raw tables.
- Paths come from `config/`, never hardcoded.
- Never write into `data/raw/`.
