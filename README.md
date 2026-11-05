# notset-algo-trading-project

**HEX Research** (Ethan Tait, Hank Rugg): group project for *Blockchain, Cryptocurrency and Algorithmic Trading*, Fordham MSQF, Fall 2026.

> **Status: Milestone 1 (due Mon Nov 9).** Plan: [`reports/milestones/milestone-1/PLAN.md`](reports/milestones/milestone-1/PLAN.md).

## The thesis in one paragraph

Forecast the next few minutes of an alt perp's move **net of BTC** (its BTC-hedged spread) from what BTC, ETH and the alt itself have just done. Does SOL still have to catch up to BTC's last move, or is it about to snap back? It's a forecast a relative-value or execution desk can act on, and the hedge keeps it from winning by holding beta in a bull market. Details: [`docs/THESIS.md`](docs/THESIS.md).

| | |
|---|---|
| Data now | Binance USD-M perps, 1-min bars, BTC ETH SOL XRP DOGE, 2023-01 to 2025-11 |
| Data later | Hank's tick capture (slot in [`docs/DATA.md`](docs/DATA.md)) |
| Target | Forward 5-min BTC-hedged spread of SOL / XRP / DOGE, vol-scaled |
| Fit metric | Median daily rank IC, sliding-window walk-forward |
| Judging metric | Cumulative OOS net PnL of the hedged position vs baseline, costs on both legs |
| Stack | kdb+/q (data) -> Python (research) -> Java (strategy replay) |

## Repository layout

```
notset-algo-trading-project/
├── CLAUDE.md            <- context and rules for Claude Code sessions
├── .claude/             <- project subagents and skills (see CLAUDE.md)
├── docs/
│   ├── THESIS.md        <- what we predict, for whom, definitions, traps
│   ├── DATA.md          <- data chapter: what we have, gaps, tick slot
│   ├── EVALUATION.md    <- metrics and anti-overfitting rules, pre-registered
│   ├── ARCHITECTURE.md  <- q -> Python -> Java contract
│   ├── DECISIONS.md     <- dated decision log
│   └── SETUP.md         <- WSL2, KDB-X Community, PyKX, JDK, VS Code, Claude Code
├── research/
│   └── LEARNINGS.md     <- what each run taught us; read before proposing the next one
├── experiments/         <- registry.jsonl: one line per run (config, git hash, metrics)
├── q/                   <- data layer (Ethan)
├── python/              <- research package, scripts, notebooks
├── java/                <- strategy replay engine
├── config/              <- one YAML per experiment, read by all three layers
├── reports/             <- research plans, milestones, paper, slides
└── data/                <- LOCAL ONLY, gitignored
```

## Course deliverables

| Deliverable | Type | Due |
|---|---|---|
| Research Plan | Individual | Oct 7 (submitted) |
| **Group Milestone 1** | Group | **Mon Nov 9** |
| Group Milestone 2 | Group | Nov 18 |
| Presentation slides | Group | Dec 2 |
| Presentation | Group | Dec 9 or Dec 16 |
| Research paper | Group | Dec 16 |

## Team

| Role | Scope | Who |
|---|---|---|
| CRO | Data cleaning, models, optimization, backtest | Ethan Tait |
| CTO | GitHub, development, data acquisition/formatting, production | Hank Rugg |
| COO | Presentation, paper, organization, logistics | shared |

## Getting started

1. Environment: [`docs/SETUP.md`](docs/SETUP.md)
2. Thesis and plan: [`docs/THESIS.md`](docs/THESIS.md), then [`reports/milestones/milestone-1/PLAN.md`](reports/milestones/milestone-1/PLAN.md)
3. Rules: [`CONTRIBUTING.md`](CONTRIBUTING.md), [`docs/EVALUATION.md`](docs/EVALUATION.md)
