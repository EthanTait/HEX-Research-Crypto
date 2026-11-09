# returns, liveness masks and the trailing building blocks every feature uses.
# everything here is causal: a value at row t uses rows <= t only
import numpy as np
import pandas as pd

from ..config import BARS_PER_DAY


def live(mid, carry):
    # d12: a bar is usable when it is not a carryover and has a price, and so was the bar before
    # (the return on the bar after a stale run spans the whole gap). missing rows are NaN -> false
    ok = (carry == 0) & mid.notna()
    return ok & ok.shift(1, fill_value=False)


def log_ret(mid, carry):
    r = np.log(mid).diff()
    return r.where(live(mid, carry))


def ema(x, span):
    # ewm skips NaN but holds its value through a stale run; callers mask with live()
    return x.ewm(span=span, adjust=False, ignore_na=True).mean()


def ewm_vol(r, halflife=BARS_PER_DAY):
    # trailing vol: ewm of squared returns, 1-day half-life, uses rows <= t
    return np.sqrt((r**2).ewm(halflife=halflife, adjust=False, ignore_na=True, min_periods=BARS_PER_DAY // 4).mean())


def rolling_beta(y, x, window):
    # ols slope of y on x over the trailing window, rows <= t. shift(1) at the call site for t-1
    m = y.notna() & x.notna()
    y, x = y.where(m), x.where(m)
    mp = max(window // 4, 60)
    mx = x.rolling(window, min_periods=mp).mean()
    my = y.rolling(window, min_periods=mp).mean()
    xx = (x * x).rolling(window, min_periods=mp).mean()
    xy = (x * y).rolling(window, min_periods=mp).mean()
    return (xy - mx * my) / (xx - mx * mx)


def fwd_sum(e, h):
    # sum of e over t+1..t+h; NaN if any of those bars is masked, so no sum straddles a gap.
    # reversed rolling at row t covers t..t+h-1, so shift(-1) moves it to t+1..t+h
    return e[::-1].rolling(h, min_periods=h).sum()[::-1].shift(-1)


def trailing_z(x, window=BARS_PER_DAY * 7, clip=5.0):
    # z-score against a trailing window (no full-sample statistics), clipped
    mu = x.rolling(window, min_periods=window // 4).mean()
    sd = x.rolling(window, min_periods=window // 4).std()
    return ((x - mu) / sd).clip(-clip, clip)
