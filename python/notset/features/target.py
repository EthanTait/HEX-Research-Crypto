# the thesis target (docs/THESIS.md definitions):
#   e_j(t)   = r_j(t) - beta_j(t) * r_BTC(t)      beta from bars <= t-1
#   S_j(t,h) = e_j(t+1) + ... + e_j(t+h)
#   y_j(t,h) = S_j(t,h) / sigma_e_j(t)            sigma trailing, 1-day half-life
import pandas as pd

from ..config import BARS_PER_DAY
from .base import ewm_vol, fwd_sum, rolling_beta


def hedged(r, hedge="BTCUSDT", beta_days=7, followers=None):
    # r: wide frame of log returns (ts_end x sym). returns (e, beta) wide frames for the followers
    followers = followers or [s for s in r.columns if s != hedge]
    w = beta_days * BARS_PER_DAY
    beta = pd.DataFrame({j: rolling_beta(r[j], r[hedge], w).shift(1) for j in followers})
    e = pd.DataFrame({j: r[j] - beta[j] * r[hedge] for j in followers})
    return e, beta


def targets(e, horizons=(1, 5, 15), halflife=BARS_PER_DAY):
    # dict h -> wide frame of y_j(t,h). sigma uses e up to t, the sum uses t+1..t+h only
    sigma = e.apply(ewm_vol, halflife=halflife)
    return {h: e.apply(fwd_sum, h=h) / sigma for h in horizons}, sigma
