# coverage audit of the raw 1-min archive, straight from the files (no hdb needed)
# out: output/coverage/{files.csv, by_year.csv, cross.csv, coverage.md}
# usage: python python/scripts/coverage.py [--start 2023-01-01 --end 2025-11-30 --workers 8]
import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
DATASETS = {"level1_1min": "level1", "trade_1min": "trade", "book_1min": "book"}
MIN = 60_000


def paths():
    cfg = yaml.safe_load((ROOT / "config" / "local.yaml").read_text())["paths"]
    raw, out = Path(cfg["raw_fordham"]), Path(cfg["output"])
    raw = raw if raw.is_absolute() else ROOT / raw
    out = out if out.is_absolute() else ROOT / out
    return raw / "binance" / "futures" / "latest", out / "coverage"


def scan(task):
    ds, day, sym, path = task
    st = {"dataset": ds, "day": day, "sym": sym, "present": False}
    if not Path(path).exists():
        return st, None, None
    try:
        df = pd.read_csv(path, usecols=["ts_end", "bin_id", "carryover"])
    except Exception as e:
        st["error"] = repr(e)[:200]
        return st, None, None
    tsf = df["ts_end"].to_numpy(float)
    bad = ~np.isfinite(tsf)
    ts = np.where(bad, -1, tsf).astype(np.int64)
    co = df["carryover"].to_numpy(float)
    start = pd.Timestamp(day, tz="UTC").value // 1_000_000
    st.update(
        present=True,
        rows=len(df),
        ts_nan=int(bad.sum()),
        # offsets in minutes from file-date midnight: tells us which bars a file holds
        first_off=int((ts[0] - start) // MIN) if len(ts) else None,
        last_off=int((ts[-1] - start) // MIN) if len(ts) else None,
        off_grid=int((ts % MIN != 0).sum()),
        dup=int(len(ts) - np.unique(ts).size),
        nonmono=int((np.diff(ts) <= 0).sum()),
        bin_first=df["bin_id"].iloc[0] if len(df) else None,
        bin_last=df["bin_id"].iloc[-1] if len(df) else None,
        co_ge1=int((co >= 1).sum()),
        co_m1=int((co == -1).sum()),
        co_other=int(((co != 0) & ~(co >= 1) & (co != -1)).sum()),
        co_max=float(np.nanmax(co)) if len(co) else None,
    )
    return st, ts, np.nan_to_num(co, nan=-99).astype(np.int32)


def longest_run(flag):
    if not flag.any():
        return 0, -1
    d = np.diff(np.concatenate(([0], flag.astype(np.int8), [0])))
    s, e = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    i = int(np.argmax(e - s))
    return int(e[i] - s[i]), int(s[i])


def ranges(days):
    if not len(days):
        return "none"
    d = pd.to_datetime(sorted(days))
    out, s, p = [], d[0], d[0]
    for x in d[1:]:
        if (x - p).days != 1:
            out.append((s, p))
            s = x
        p = x
    out.append((s, p))
    return ", ".join(f"{a:%Y-%m-%d}" if a == b else f"{a:%Y-%m-%d}..{b:%m-%d}" for a, b in out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--end", default="2025-11-30")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    raw, out = paths()
    out.mkdir(parents=True, exist_ok=True)
    days = [d.strftime("%Y%m%d") for d in pd.date_range(a.start, a.end)]
    tasks = [
        (ds, day, sym, str(raw / ds / day / f"{sym}.{day}.{suf}.1min.csv.gz"))
        for ds, suf in DATASETS.items() for sym in SYMS for day in days
    ]
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(scan, tasks, chunksize=64))

    files = pd.DataFrame([r[0] for r in res])
    files["year"] = files["day"].str[:4]
    files.to_csv(out / "files.csv", index=False)
    if "error" in files and files["error"].notna().any():
        print("read errors:\n", files[files["error"].notna()][["dataset", "day", "sym", "error"]])

    # per (dataset, sym) concatenated series in file order
    ser = {}
    for st, ts, co in res:
        if ts is not None:
            ser.setdefault((st["dataset"], st["sym"]), []).append((ts, co))
    ser = {k: (np.concatenate([x[0] for x in v]), np.concatenate([x[1] for x in v])) for k, v in ser.items()}

    # year = file date year
    by_year = files.groupby(["dataset", "sym", "year"]).agg(
        days_expected=("day", "size"), days_present=("present", "sum"), bars=("rows", "sum"),
        co_ge1=("co_ge1", "sum"), co_m1=("co_m1", "sum"), co_other=("co_other", "sum"),
    ).reset_index()
    by_year.to_csv(out / "by_year.csv", index=False)

    yrs = sorted(files["year"].unique())
    rows = []
    for ds in DATASETS:
        for sym in SYMS:
            f = files[(files.dataset == ds) & (files.sym == sym)]
            y = by_year[(by_year.dataset == ds) & (by_year.sym == sym)].set_index("year")
            ts, co = ser.get((ds, sym), (np.array([], np.int64), np.array([], np.int32)))
            n, i = longest_run(co != 0)
            run = f"{n} from {pd.Timestamp(ts[i], unit='ms'):%Y-%m-%d %H:%M}" if n else "0"
            short = f[f.present & (f.rows != 1440)]
            rows.append({
                "Symbol": sym, "Dataset": ds,
                "Bars": int(f["rows"].sum()),
                "Days": f"{int(f.present.sum())}/{len(f)}",
                "Missing days": ranges(f[~f.present]["day"].tolist()),
                "Days != 1440 bars": len(short),
                "Carryover >= 1 (" + "/".join(yrs) + ")": " / ".join(str(int(y.co_ge1.get(k, 0))) for k in yrs),
                "Carryover == -1 (" + "/".join(yrs) + ")": " / ".join(str(int(y.co_m1.get(k, 0))) for k in yrs),
                "Longest stale run (bars)": run,
            })
    cov = pd.DataFrame(rows)

    # grid checks: same ts_end set across datasets (per sym) and across syms (per dataset)
    cross = []
    for (ds, sym), (ts, _) in ser.items():
        u = np.unique(ts)
        cross.append({"check": "self", "dataset": ds, "sym": sym, "vs": "",
                      "n": len(ts), "dup_ts": len(ts) - len(u),
                      "gap_minutes_inside_span": int((u[-1] - u[0]) // MIN + 1 - len(u)),
                      "first": str(pd.Timestamp(u[0], unit="ms")), "last": str(pd.Timestamp(u[-1], unit="ms"))})
    for sym in SYMS:
        for other in ["trade_1min", "book_1min"]:
            if ("level1_1min", sym) in ser and (other, sym) in ser:
                x, y_ = ser[("level1_1min", sym)][0], ser[(other, sym)][0]
                cross.append({"check": "datasets", "dataset": "level1_1min", "sym": sym, "vs": other,
                              "only_left": len(np.setdiff1d(x, y_)), "only_right": len(np.setdiff1d(y_, x))})
    for ds in DATASETS:
        for sym in SYMS[1:]:
            if (ds, "BTCUSDT") in ser and (ds, sym) in ser:
                x, y_ = ser[(ds, "BTCUSDT")][0], ser[(ds, sym)][0]
                cross.append({"check": "symbols", "dataset": ds, "sym": "BTCUSDT", "vs": sym,
                              "only_left": len(np.setdiff1d(x, y_)), "only_right": len(np.setdiff1d(y_, x))})
    cross = pd.DataFrame(cross)
    cross.to_csv(out / "cross.csv", index=False)

    # hand-built: to_markdown needs tabulate, which isn't in the env
    md = "\n".join(
        ["| " + " | ".join(cov.columns) + " |", "|" + "---|" * len(cov.columns)]
        + ["| " + " | ".join(str(v) for v in r) + " |" for r in cov.itertuples(index=False)]
    )
    (out / "coverage.md").write_text(md + "\n")
    print(md)
    print("\nfile window (first_off, last_off in minutes from file-date midnight) and bin_id range, counts:")
    print(files[files.present].groupby(["dataset", "first_off", "last_off", "bin_first", "bin_last"]).size().to_string())
    print("\nper-file anomalies (sum):")
    print(files.groupby("dataset")[["ts_nan", "off_grid", "dup", "nonmono", "co_other"]].sum().to_string())
    print("\ncross checks:")
    print(cross.to_string(index=False))


if __name__ == "__main__":
    main()
