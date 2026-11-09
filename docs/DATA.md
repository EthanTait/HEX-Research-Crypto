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

### Known gaps (re-verified against the files, 2026-11-05)

Dates are **file dates**. 1,062 of 1,065 day folders exist in each dataset.

- All datasets: 2025-11-26, -27, -28 missing.
- `level1_1min`: ETH and SOL missing 2024-01-13 and -14; SOL and XRP missing 2025-11-24.
- `trade_1min` and `book_1min`: otherwise complete, all 5 names on one identical grid.

### What a file holds

Every file that exists has exactly 1,440 rows, `bin_id` 0..1439, no duplicate, non-monotonic or off-grid `ts_end` (all multiples of 60,000 ms). No exceptions in 15,924 files.

| Dataset | File dated D holds `ts_end` | `bin_id` k means |
|---|---|---|
| `level1_1min`, `trade_1min` | D 00:01 .. D+1 00:00 | the bar ending at D + (k+1) min |
| `book_1min` | D 00:00 .. D 23:59 | the snapshot at D + k min |

So for the same `bin_id`, book `ts_end` = level1 `ts_end` - 60,000 ms. **Join on `ts_end`, never on `bin_id`.** The day a level1 or trade bar belongs to is the date of (`ts_end` - 1 min), which is the file date and the HDB `date` partition (`DECISIONS.md`, 2026-11-05).

### Gotchas

- **`carryover`**: `>= 1` is a run counter (1, 2, 3, ...) on bins that repeat the previous bin (a fake zero return, and the next live bar carries the whole gap); `== -1` is a constant flag on bins whose price fields are NaN. Mask the stale bar **and the bar after** before any return. Never forward-fill returns across these runs.
- **`ts_end`** is epoch ms UTC marking the **end** of the bin. A naive group-by-date puts the last bar of a day on the next day.
- **One common grid** for all 5 names. Shifting per-symbol frames turns a missing day into a fake multi-day "1-min" return.
- **Book rows** are snapshots taken just after `ts_end` (median 0.6 s after, p99 4 s, max 15 s on live rows). Shift book features 1 bar before use.
- Trade and level1 bars align 1:1 on `ts_end`.

### Coverage table

Produced by `python/scripts/coverage.py` from the raw files (outputs in `output/coverage/`); 9 cells re-counted independently with `zcat | awk` by the `data-auditor`, all matching. Expected bars per series: 1,065 days x 1,440 = 1,533,600. Years are file-date years, shown as 2023 / 2024 / 2025. The longest run counts consecutive bars with `carryover != 0`.

| Symbol | Dataset | Bars | Missing days | Carryover >= 1 | Carryover == -1 | Longest stale run (bars) |
|---|---|---|---|---|---|---|
| BTCUSDT | level1_1min | 1,529,280 | 2025-11-26..28 | 118 / 2339 / 3278 | 0 / 0 / 1633 | 1440 from 2025-01-27 00:01 (all -1) |
| ETHUSDT | level1_1min | 1,526,400 | 2024-01-13..14, 2025-11-26..28 | 81 / 1798 / 1920 | 0 / 737 / 1635 | 1440 from 2025-01-27 00:01 (all -1) |
| SOLUSDT | level1_1min | 1,524,960 | 2024-01-13..14, 2025-11-24, 2025-11-26..28 | 69 / 2059 / 2709 | 0 / 358 / 1113 | 847 from 2024-07-16 00:01 |
| XRPUSDT | level1_1min | 1,527,840 | 2025-11-24, 2025-11-26..28 | 59 / 4683 / 2377 | 0 / 0 / 363 | 684 from 2024-07-04 12:37 |
| DOGEUSDT | level1_1min | 1,529,280 | 2025-11-26..28 | 72 / 1844 / 1350 | 0 / 0 / 3614 | 1440 from 2025-01-27 00:01 (all -1) |
| BTCUSDT | trade_1min | 1,529,280 | 2025-11-26..28 | 286 / 65 / 18 | 0 / 0 / 0 | 120 from 2023-01-23 20:40 |
| ETHUSDT | trade_1min | 1,529,280 | 2025-11-26..28 | 218 / 230 / 18 | 0 / 0 / 0 | 166 from 2024-10-07 21:15 |
| SOLUSDT | trade_1min | 1,529,280 | 2025-11-26..28 | 138 / 67 / 19 | 0 / 0 / 0 | 108 from 2023-01-24 21:55 |
| XRPUSDT | trade_1min | 1,529,280 | 2025-11-26..28 | 105 / 1418 / 18 | 0 / 0 / 0 | 1356 from 2024-11-30 00:02 |
| DOGEUSDT | trade_1min | 1,529,280 | 2025-11-26..28 | 140 / 1335 / 20 | 0 / 0 / 0 | 1266 from 2024-11-30 00:02 |
| BTCUSDT | book_1min | 1,529,280 | 2025-11-26..28 | 930 / 946 / 41 | 0 / 0 / 0 | 877 from 2024-01-24 12:40 |
| ETHUSDT | book_1min | 1,529,280 | 2025-11-26..28 | 898 / 948 / 55 | 0 / 0 / 0 | 877 from 2024-01-24 12:40 |
| SOLUSDT | book_1min | 1,529,280 | 2025-11-26..28 | 862 / 942 / 40 | 0 / 0 / 0 | 877 from 2024-01-24 12:40 |
| XRPUSDT | book_1min | 1,529,280 | 2025-11-26..28 | 873 / 945 / 42 | 0 / 0 / 0 | 877 from 2024-01-24 12:40 |
| DOGEUSDT | book_1min | 1,529,280 | 2025-11-26..28 | 875 / 948 / 47 | 0 / 0 / 0 | 876 from 2024-01-24 12:40 |

### Audit findings (2026-11-05, full archive)

Ranked by how much they could bias a BTC-leads-alts forecast at 1-5 min.

1. **Level1 staleness is mostly not simultaneous across names.** On the minutes where all 5 names have a level1 row (1,524,960), 16,929 have at least one name stale (1.1%). In only 1,508 of those (8.9%) are all 5 stale; in the other 91.1% a subset is stale while the rest are live. A stale alt next to a live BTC is a fake zero return followed by a catch-up bar, which looks like a lead or a lag. The first live bar after a stale run is 2-3x the normal size (BTC median |ret| 8.3 bps vs 2.7; SOL 14.5 vs 5.9).
2. **It is concentrated in 2024-25 and in whole-day outages**, which matters because 2024 is the walk-forward and 2025 the holdout. Examples: SOL 2024-07-04 and 2024-07-16; BTC 2024-04-25; DOGE 2025-01-16; BTC, ETH, DOGE all day 2025-01-27 (`carryover == -1`, NaN prices); several names 2025-03-15. 2023 has 59-118 stale level1 bars per name.
3. **Measured effect on correlations is small in aggregate.** Masking stale bars moves the contemporaneous BTC-alt 1-min correlation by 0.002 to 0.006 (e.g. SOL 0.6653 -> 0.6709) and the one-bar lead and lag correlations by less than 0.0005. Mask anyway: the effect is concentrated in a few days, and daily metrics see those days.
4. **When level1 is stale, trade and book are almost always live.** 99% of level1 stale minutes have a live trade bar (`trade_count > 0`) and a live book row in the same minute, for every name. That points to a gap in the level1 recording, not a market halt. Whether the target uses trade or book prices on those bars is an open decision (D12 in the plan).
5. **`carryover` does not mean the same thing in each dataset.**
   - level1 `>= 1`: `close_mid`, `close_bid`, `close_ask` identical to the previous row and `tick_count == 0`, in 100% of rows. level1 `== -1`: mid, bid/ask, sizes, spread and volatility fields are all NaN; `ts_end`, `bin_id`, `tick_count` (0) are present.
   - trade `>= 1`: `trade_count == 0` in 100%. For BTC, ETH, SOL `close_price` repeats. For XRP and DOGE it is NaN in 85-88% of stale rows (the 2024-11-30 runs of 1,356 and 1,266 bars), so a naive diff gives NaN there, not zero.
   - The flag can start one bar late: the first empty trade bar of the 2024-11-30 XRP and DOGE runs has `carryover == 0`, `trade_count == 0` and a NaN price. Mask on `trade_count == 0` or a NaN price as well as on `carryover`.
   - book `>= 1`: `bid_price` and `ask_price` repeat and `ts_book` is frozen at the last live snapshot. 77% of stale book minutes are stale for all 5 names at once (two episodes dominate: 877 bars from 2024-01-24 12:40, 715 bars from 2023-04-20 08:40), so book staleness removes depth features for hours but adds little fake lead-lag.
6. **XRP level1 is choppy, not worse in total.** It has 237 stale episodes against 82-114 for the others (median length 9 bars vs 2), with 2,940 stale bars in 2024-01 alone, but the fewest stale minutes of the 5 over the full sample (4,862 vs 6,171-7,368).
7. **`ts_book`** is not a usable lag measure on stale rows (it is carried, up to 14.6 h old), and under 0.1% of live book rows (1,114 of 1,529,280 for BTC) have `ts_book` slightly before `ts_end` (median 64 ms, worst 44 s).
8. **`ramp_up`** is a running minute counter that resets at some file boundaries, not a flag. Its meaning is unconfirmed (needs the course's data description); about 37% of level1 rows have `ramp_up < 1440`.

Not checked: whether fields other than mid, bid/ask and `tick_count` are carried on stale level1 rows; depth, fill-size and VWAP columns in the book (crossed books, staleness); stale runs that straddle a missing day.

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
