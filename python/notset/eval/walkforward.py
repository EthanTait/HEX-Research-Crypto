# sliding-window walk-forward (d8): fit ridge on the trailing window, purge h bars, forecast the next
# test block, slide. one model pooled over the followers, target already vol-scaled.
# everything a forecast touches is computed from the fit window or earlier (lecture 9 / quant methods)
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from ..config import BARS_PER_DAY
from .metrics import daily_rank_ic, summarize_ic

HOLDOUT_START = pd.Timestamp("2025-01-01")


def standardize(train, test, clip=5.0):
    # d7: fit-window mean and std only, clipped at 5 sd
    mu, sd = train.mean(), train.std().replace(0, np.nan)
    return ((train - mu) / sd).clip(-clip, clip), ((test - mu) / sd).clip(-clip, clip)


def walk_forward(d, features, target, start, end, window_days=60, test_days=7, purge_bars=None, alpha=1.0, target_clip=None):
    # d: long panel indexed (ts_end, sym) with a 'date' column. returns forecasts for rows in [start, end]
    # alpha is the per-row ridge penalty on standardized features (X'X/n ~ I), so alpha=1 halves a
    # lone coefficient; sklearn wants the sum-of-squares scale, hence alpha * n
    h = int(target[1:])
    purge_bars = h if purge_bars is None else purge_bars
    assert purge_bars >= h, "purge must cover the target horizon"
    ts = d.index.get_level_values("ts_end")
    start, end = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    assert end <= HOLDOUT_START + pd.Timedelta(minutes=1), "2025 is the holdout; only /holdout may run it"
    out, weights = [], []
    t0 = start
    while t0 < end:
        t1 = min(t0 + pd.Timedelta(days=test_days), end)
        fit = (ts >= t0 - pd.Timedelta(days=window_days)) & (ts < t0 - pd.Timedelta(minutes=purge_bars))
        tst = (ts >= t0) & (ts < t1)
        tr = d.loc[fit, features + [target]].dropna()
        te = d.loc[tst, features]
        if len(tr) < BARS_PER_DAY:
            t0 = t1
            continue
        xtr, xte = standardize(tr[features], te)
        # the target is already vol-scaled, so a fixed clip needs no statistics; it stops a few
        # crash minutes from steering a least-squares fit that is judged on ranks
        ytr = tr[target].clip(-target_clip, target_clip) if target_clip else tr[target]
        m = Ridge(alpha=alpha * len(xtr)).fit(xtr.values, ytr.values)
        f = pd.Series(m.predict(xte.fillna(0).values), index=te.index, name="forecast")
        f[xte.isna().any(axis=1)] = np.nan  # a missing feature means no forecast, not a zero-filled one
        out.append(f)
        weights.append(pd.Series(m.coef_, index=features, name=t0))
        t0 = t1
    return pd.concat(out), pd.DataFrame(weights)


def evaluate(forecast, d, target="y5"):
    # pre-registered metric: median daily rank ic pooled over followers, plus per follower
    y = d.loc[forecast.index, target]
    dates = d.loc[forecast.index, "date"]
    ic = daily_rank_ic(forecast, y, dates)
    res = summarize_ic(ic)
    res["by_follower"] = {}
    for j in forecast.index.get_level_values("sym").unique():
        m = forecast.index.get_level_values("sym") == j
        icj = daily_rank_ic(forecast[m], y[m], dates[m])
        res["by_follower"][j] = {"ic_median_daily": float(icj.median()), "ic_pos_days_pct": float(100 * (icj > 0).mean())}
    return res, ic
