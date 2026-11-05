# java/ (strategy replay layer)

Event-driven replay of the hedged spread strategy: two legs, position state, decision delay, fees and spread per leg. Not needed for Milestone 1; created as a Maven project when the strategy needs state that is awkward to vectorize (see [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)).

```
java/
├── pom.xml
└── src/
    ├── main/java/notset/
    │   ├── feed/       # EventSource: time-ordered bars (now) or ticks (later) from q (javakdb) or exported files
    │   ├── engine/     # single-threaded event loop, simulated clock, delay model
    │   ├── exec/       # fill model, fees, spread per leg
    │   ├── strategy/   # Strategy interface: onBar / onQuote / onTrade -> orders
    │   └── report/     # fills + positions written back for evaluation in Python
    └── test/java/notset/
```

Rules
- Deterministic: single-threaded, and any randomness uses a seeded RNG.
- Parameters come from the same `config/*.yaml` that Python uses.
- First test: reproduce the vectorized Python PnL at zero delay and mid fills.
