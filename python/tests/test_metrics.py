# the vectorized daily rank ic must equal scipy's spearman computed day by day
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset.eval.metrics import daily_rank_ic  # noqa: E402


def test_daily_rank_ic_matches_scipy():
    rng = np.random.default_rng(3)
    n = 5000
    d = np.repeat(np.arange(10), n // 10)
    y = rng.normal(size=n)
    s = 0.1 * y + rng.normal(size=n)
    s[::7] = np.nan
    ic = daily_rank_ic(s, y, d)
    for day in range(10):
        m = (d == day) & ~np.isnan(s)
        assert np.isclose(ic[day], spearmanr(s[m], y[m]).statistic)


if __name__ == "__main__":
    test_daily_rank_ic_matches_scipy()
    print("ok")
