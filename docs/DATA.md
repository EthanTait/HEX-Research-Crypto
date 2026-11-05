# Data

**No market data is ever committed.** The repo is public and the course data is not ours to redistribute. `data/` is gitignored except for its README.

This is the data chapter for Milestone 1 (step 2 of the plan). Numbers marked _TBD_ are filled in from the actual files, not from memory.

## 1. What we have: course 1-min archive

Binance USD-M perpetual futures, **1-minute bars**, 2023-01-01 to 2025-11-30. Symbols: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT.

| Dataset | File suffix | Content |
|---|---|---|
| `level1_1min` | `.level1.1min.csv.gz` | top of book: open/close/min/max mid, close bid/ask + sizes, spread stats, tick volatility |
| `trade_1min` | `.trade.1min.csv.gz` | OHLC trade prices, buy/sell volume, VWAPs, taker counts, trade volatility |
| `book_1min` | `.book.1min.csv.gz` | depth snapshot: fill size / VWAP at bps offsets and notional levels |

Raw path shape (as delivered):

```
<raw>/binance/futures/latest/<dataset>/<YYYYMMDD>/<SYMBOL>.<YYYYMMDD>.<suffix>.csv.gz
```

### Known gaps (verified during the homeworks; re-check in the coverage table)

- All datasets: 2025-11-26, -27, -28 missing.
- `level1_1min`: ETH and SOL missing 2024-01-13 and -14; SOL and XRP missing 2025-11-24.
- `trade_1min` and `book_1min`: otherwise complete.

### Gotchas

- **`carryover`**: `>= 1` means the bin repeats the previous bin (a fake zero return, and the next bar carries the whole gap); `== -1` means most fields are NaN. Mask the stale bar **and the bar after** before any return. Never forward-fill returns across these runs.
- **`ts_end`** is epoch ms UTC marking the **end** of the bin. A naive group-by-date puts the last bar of a day on the next day.
- **One common grid** for all 5 names. Shifting per-symbol frames turns a missing day into a fake multi-day "1-min" return.
- **Book rows** are snapshots taken just after `ts_end`. Shift book features 1 bar before use.
- Join datasets on `ts_end`. Trade and level1 bars align 1:1.

### Coverage table (fill in, step 2)

| Symbol | Dataset | Bars | Missing days | Carryover >= 1 | Carryover == -1 |
|---|---|---|---|---|---|
| _TBD_ | | | | | |

## 2. Hank's tick capture (slot, to wire up)

Hank has been recording tick data for the last 3-4 weeks. Details are not known yet; fill this in with him.

| Field | Value |
|---|---|
| Venue(s) | _TBD_ |
| Symbols | _TBD_ |
| Tables (trades / BBO / L2) | _TBD_ |
| Date range | _TBD_ (late 2026: a forward period the 1-min archive never saw) |
| Timestamp semantics (exchange vs receive time, units) | _TBD_ |
| File format and where it is stored | _TBD_ |
| Known gaps / reconnects | _TBD_ |

The q tables it would load into are sketched in `docs/ARCHITECTURE.md` (`trade`, `quote`). Adjust the schema to the files once we see them.

## 3. Outside data (decision D5)

Available on request from the course: funding rates, open interest, liquidations, Hyperliquid trades, other venues (Bybit, OKX). None requested yet.

## Local layout (not committed)

```
data/
├── README.md        <- the only tracked file
├── raw/
│   ├── fordham/     <- course 1-min archive, exactly as delivered (read-only)
│   └── tick/        <- Hank's capture
└── hdb/             <- kdb partitioned database built by q/load/
```

`config/local.yaml` (gitignored) points at wherever `raw/fordham` actually lives on each machine.
