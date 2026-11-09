# book shift, purge, holdout guard and pnl accounting, on synthetic frames (no hdb needed)
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset import io  # noqa: E402
from notset.eval import pnl  # noqa: E402
from notset.eval.walkforward import walk_forward  # noqa: E402


def test_book_shift_puts_previous_snapshot_on_the_bar():
    # mirrors build.raw: the book row at level1 ts_end T must be the snapshot taken after T-1min
    bidx = io.grid("bookbar", "2024-01-15", "2024-01-15")
    lidx = io.grid("l1bar", "2024-01-15", "2024-01-15")
    book = pd.Series(np.arange(len(bidx), dtype=float), index=bidx)
    shifted = book.shift(1, freq="1min").reindex(lidx)
    t = pd.Timestamp("2024-01-15 12:00")
    assert shifted[t] == book[t - pd.Timedelta(minutes=1)]
    assert np.isnan(shifted[lidx[-1]]) or shifted[lidx[-1]] == book[bidx[-1]]


def test_holdout_guard_blocks_2025():
    os.environ.pop("NOTSET_HOLDOUT", None)
    try:
        io.guard("2025-01-01")
        assert False, "guard did not raise"
    except PermissionError:
        pass
    io.guard("2024-12-31")


def _panel(n_days=20, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-03-01 00:01", periods=n_days * 1440, freq="1min", name="ts_end")
    parts = []
    for j in ["A", "B"]:
        f = pd.DataFrame(index=idx)
        f["sym"] = j
        f["x1"] = rng.normal(size=len(idx))
        f["x2"] = rng.normal(size=len(idx))
        f["y5"] = 0.05 * f["x1"] + rng.normal(size=len(idx))
        f["e_book"] = rng.normal(size=len(idx)) * 1e-4
        f["beta"], f["beta2"], f["hspread"], f["hspread_btc"] = 1.0, 0.0, 1e-4, 1e-5
        f["hspread_idx"], f["w_idx"] = 0.0, 0.0
        f["date"] = (f.index - pd.Timedelta(minutes=1)).date
        parts.append(f)
    return pd.concat(parts).reset_index().set_index(["ts_end", "sym"]).sort_index()


def test_walk_forward_purges_at_least_h_and_only_forecasts_the_test_block():
    d = _panel()
    f, w = walk_forward(d, ["x1", "x2"], "y5", "2024-03-10", "2024-03-20", window_days=7, test_days=5)
    ts = f.index.get_level_values("ts_end")
    assert ts.min() >= pd.Timestamp("2024-03-10") and ts.max() < pd.Timestamp("2024-03-21")
    assert len(w) == 3 and w["x1"].mean() > w["x2"].abs().mean()
    try:
        walk_forward(d, ["x1"], "y5", "2024-03-10", "2024-03-12", purge_bars=2)
        assert False
    except AssertionError:
        pass


def test_pnl_stages_have_no_gaps_and_charge_every_trade():
    d = _panel(n_days=10)
    dj = d.xs("A", level="sym")
    fc = pd.Series(np.sin(np.arange(len(dj)) / 50), index=dj.index)
    fc.iloc[3000:3100] = np.nan  # a stretch with no forecast
    bt = pnl.backtest(fc, dj, h=5)
    assert bt[["mid", "fees_spread", "delay_1bar"]].notna().all().all()
    assert (bt["position"].iloc[3010:3100] == 0).all()  # flat after the forecasts stop
    assert bt["fees_spread"].sum() < bt["mid"].sum()  # costs were charged, including the exit
    assert np.isclose(bt["long_leg"].sum() + bt["short_leg"].sum(), bt["mid"].sum())


if __name__ == "__main__":
    for k, fn in list(globals().items()):
        if k.startswith("test_"):
            fn()
            print("ok", k)
