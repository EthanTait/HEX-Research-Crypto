# volume-weighted index of the names (course sheet item) and the two-factor hedge used by the
# d3b comparison. weights are trailing dollar volume, lagged one bar
import numpy as np
import pandas as pd

from ..config import BARS_PER_DAY


def vw_weights(dollar_vol, exclude=()):
    # weights known at t: 1-day ewm of dollar volume up to t-1, normalised over the included names
    cols = [c for c in dollar_vol.columns if c not in exclude]
    w = dollar_vol[cols].ewm(halflife=BARS_PER_DAY, adjust=False, ignore_na=True, min_periods=60).mean().shift(1)
    return w.div(w.sum(axis=1), axis=0)


def vw_index(r, dollar_vol, exclude=()):
    w = vw_weights(dollar_vol, exclude)
    return (w * r[w.columns]).sum(axis=1, min_count=len(w.columns))


def rolling_beta2(y, x1, x2, window):
    # two-regressor rolling ols (closed form), rows <= t. shift(1) at the call site
    m = y.notna() & x1.notna() & x2.notna()
    y, x1, x2 = y.where(m), x1.where(m), x2.where(m)
    mp = max(window // 4, 60)
    rm = lambda s: s.rolling(window, min_periods=mp).mean()
    m1, m2, my = rm(x1), rm(x2), rm(y)
    s11, s22, s12 = rm(x1 * x1) - m1 * m1, rm(x2 * x2) - m2 * m2, rm(x1 * x2) - m1 * m2
    s1y, s2y = rm(x1 * y) - m1 * my, rm(x2 * y) - m2 * my
    det = s11 * s22 - s12 * s12
    return (s22 * s1y - s12 * s2y) / det, (s11 * s2y - s12 * s1y) / det
