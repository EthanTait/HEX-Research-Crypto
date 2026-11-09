# look-ahead and alignment asserts on synthetic series. run: python -m pytest python/tests
# or: python python/tests/test_alignment.py
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset.features.base import fwd_sum, live, log_ret, rolling_beta  # noqa: E402
from notset.features.target import hedged, targets  # noqa: E402


def test_live_masks_stale_bar_and_the_bar_after():
    mid = pd.Series([100.0, 101, 101, 101, 103, 104, 105])
    carry = pd.Series([0, 0, 1, 2, 0, 0, 0])
    assert live(mid, carry).tolist() == [False, True, False, False, False, True, True]


def test_live_masks_missing_row_and_the_bar_after():
    mid = pd.Series([100.0, 101, np.nan, 103, 104])
    carry = pd.Series([0, 0, 0, 0, 0])
    assert live(mid, carry).tolist() == [False, True, False, False, True]


def test_log_ret_is_nan_across_a_gap_never_filled():
    mid = pd.Series([100.0, 101, 101, 105, 106])
    carry = pd.Series([0, 0, 1, 0, 0])
    r = log_ret(mid, carry)
    assert np.isnan(r[2]) and np.isnan(r[3]) and np.isclose(r[4], np.log(106 / 105))


def test_fwd_sum_uses_t_plus_1_to_t_plus_h_only():
    e = pd.Series(np.arange(1.0, 11))
    s = fwd_sum(e, 3)
    assert s[0] == 2 + 3 + 4 and s[6] == 8 + 9 + 10 and np.isnan(s[7])


def test_fwd_sum_is_nan_when_any_bar_in_the_window_is_masked():
    e = pd.Series([1.0, 1, np.nan, 1, 1, 1, 1])
    s = fwd_sum(e, 2)
    assert np.isnan(s[0]) and np.isnan(s[1]) and s[2] == 2 and s[4] == 2


def test_beta_at_t_does_not_see_bar_t():
    rng = np.random.default_rng(0)
    x = pd.Series(rng.normal(size=3000))
    y = 0.8 * x + pd.Series(rng.normal(size=3000))
    b0 = rolling_beta(y, x, 500).shift(1)
    x2, y2 = x.copy(), y.copy()
    x2[1500], y2[1500] = 50.0, -50.0
    b1 = rolling_beta(y2, x2, 500).shift(1)
    assert np.allclose(b0[:1501].dropna(), b1[:1501].dropna())
    assert not np.isclose(b0[1501], b1[1501])


def test_target_at_t_depends_only_on_future_e_and_past_sigma():
    rng = np.random.default_rng(1)
    r = pd.DataFrame(rng.normal(size=(6000, 2)) * 1e-3, columns=["BTCUSDT", "SOLUSDT"])
    e, _ = hedged(r, "BTCUSDT", beta_days=1, followers=["SOLUSDT"])
    ys, sigma = targets(e, (5,))
    y = ys[5]["SOLUSDT"]
    r2 = r.copy()
    r2.loc[4000, "SOLUSDT"] += 0.05
    e2, _ = hedged(r2, "BTCUSDT", beta_days=1, followers=["SOLUSDT"])
    y2 = targets(e2, (5,))[0][5]["SOLUSDT"]
    # bars before 4000-5 cannot change; bars 3995..3999 change through the forward sum only
    assert np.allclose(y[:3995].dropna(), y2[:3995].dropna())
    assert not np.allclose(y[3995:4000], y2[3995:4000])


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
            print("ok", k)
