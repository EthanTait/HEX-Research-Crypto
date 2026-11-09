# data access through q/lib only (d4: pykx on the hdb, no csv backend). never reads data/raw
import datetime as dt
import os

import numpy as np
import pandas as pd

from .config import ROOT, paths

_q = None


def q():
    # embedded q. loading the hdb moves the process cwd into data/hdb, which q needs for its
    # partition paths, so every path in python must be absolute (config.ROOT) from here on
    global _q
    if _q is None:
        import pykx as kx
        os.chdir(ROOT)
        kx.q("\\l q/init.q")
        _q = kx
    return _q


def _date(d):
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    if isinstance(d, (pd.Timestamp, dt.datetime)):
        d = d.date()
    return d


HOLDOUT_START = dt.date(2025, 1, 1)


def guard(d1):
    # the 2025 holdout is opened once, through /holdout, which sets NOTSET_HOLDOUT=1. nothing else may read it
    if _date(d1) >= HOLDOUT_START and os.environ.get("NOTSET_HOLDOUT") != "1":
        raise PermissionError(f"{d1} is in the 2025 holdout; only /holdout may read it")


def bars(tbl, syms, d0, d1, cols):
    # long rows as stored for file dates d0..d1; always has date, sym, ts_end, carryover
    guard(d1)
    kx = q()
    syms = [syms] if isinstance(syms, str) else list(syms)
    cols = [cols] if isinstance(cols, str) else list(cols)
    r = kx.q("bars", kx.SymbolAtom(tbl), kx.SymbolVector(syms), kx.DateAtom(_date(d0)), kx.DateAtom(_date(d1)), kx.SymbolVector(cols))
    df = r.pd()
    df["sym"] = df["sym"].astype(str)
    return df


def grid(tbl, d0, d1):
    # the full 1-min ts_end grid for file dates d0..d1. level1/trade bars end at 00:01..24:00,
    # book snapshots sit at 00:00..23:59 (docs/DATA.md "what a file holds")
    d0, d1 = pd.Timestamp(_date(d0)), pd.Timestamp(_date(d1))
    if tbl == "bookbar":
        return pd.date_range(d0, d1 + pd.Timedelta(days=1) - pd.Timedelta(minutes=1), freq="1min", name="ts_end")
    return pd.date_range(d0 + pd.Timedelta(minutes=1), d1 + pd.Timedelta(days=1), freq="1min", name="ts_end")


def panel(tbl, syms, d0, d1, cols):
    # dict col -> wide frame (ts_end x sym) on the common grid. missing bars are NaN, never filled
    df = bars(tbl, syms, d0, d1, cols)
    idx = grid(tbl, d0, d1)
    syms = [syms] if isinstance(syms, str) else list(syms)
    out = {}
    for c in ["carryover"] + [c for c in cols if c != "carryover"]:
        w = df.pivot(index="ts_end", columns="sym", values=c).reindex(index=idx, columns=syms)
        out[c] = w.astype(float) if c != "carryover" else w
    return out


def coverage(tbl, d0, d1):
    # counts only (rows, carryover flags), no prices: allowed on 2025 for the data chapter
    kx = q()
    return kx.q("coverage", kx.SymbolAtom(tbl), kx.DateAtom(_date(d0)), kx.DateAtom(_date(d1))).pd().reset_index()


def cache_path(name):
    p = paths()["output"] / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{name}.pkl"


def cached(name, build):
    # pickle cache under output/ (gitignored). delete the file to rebuild
    p = cache_path(name)
    if p.exists():
        return pd.read_pickle(p)
    obj = build()
    pd.to_pickle(obj, p)
    return obj
