# the candidate menu from PLAN.md step 3, one long panel (ts_end, follower) -> features + targets.
# every column is trailing; follower columns are masked where the follower isn't live, leader
# columns where the leader isn't live. book columns are shifted one bar (snapshot after ts_end).
# hedge="btc" is the pre-registered target; hedge="btc+index" adds a leave-one-out alt index (d3b)
import numpy as np
import pandas as pd

from .. import io
from ..config import BARS_PER_DAY, FOLLOWERS, SYMS
from .base import ema, ewm_vol, live, log_ret, rolling_beta
from .index import rolling_beta2, vw_weights
from .target import targets

L1_COLS = ["close_mid", "close_bid", "close_ask"]
TR_COLS = ["buy_volume", "sell_volume", "volume"]
BK_COLS = ["bid_size", "ask_size"]


def raw(d0, d1):
    # the three panels on the level1 grid. book is moved one bar later so that the row at
    # ts_end T holds the snapshot taken just after T-1min, the last one known at T
    l1 = io.panel("l1bar", SYMS, d0, d1, L1_COLS)
    tr = io.panel("tradebar", SYMS, d0, d1, TR_COLS)
    bk = io.panel("bookbar", SYMS, d0, d1, BK_COLS)
    idx = l1["close_mid"].index
    for c in list(bk):
        bk[c] = bk[c].shift(1, freq="1min").reindex(idx)
    return l1, tr, bk


def imbalance(a, b):
    s = a + b
    return ((a - b) / s).where(s > 0)


def build(d0, d1, beta_days=7, horizons=(1, 5, 15), hedge="btc"):
    l1, tr, bk = raw(d0, d1)
    mid, carry = l1["close_mid"], l1["carryover"]
    ok = live(mid, carry)
    r = log_ret(mid, carry)
    rb = r["BTCUSDT"]
    w = beta_days * BARS_PER_DAY
    dv = tr["volume"] * mid

    # hedged return e_j and its betas, from bars <= t-1. the index leg is the dollar-volume
    # weighted return of the other alts (not btc, not j), weights known at t-1
    e, beta, beta2, widx, hsidx = {}, {}, {}, {}, {}
    # booking returns: unmasked log-mid changes so that a position held through a stale run or a
    # gap earns the real move on the catch-up bar. never used for features or targets
    r_book = np.log(mid.ffill()).diff()
    hs_raw = ((l1["close_ask"] - l1["close_bid"]) / (2 * mid)).ffill()
    e_book = {}
    for j in FOLLOWERS:
        if hedge == "btc":
            b1 = rolling_beta(r[j], rb, w).shift(1)
            e[j], beta[j], beta2[j] = r[j] - b1 * rb, b1, 0.0 * b1
            widx[j], hsidx[j] = 0.0 * b1, 0.0 * b1
            e_book[j] = r_book[j] - b1.ffill() * r_book["BTCUSDT"]
        elif hedge == "btc+index":
            wj = vw_weights(dv, exclude=("BTCUSDT", j))
            idx = (wj * r[wj.columns]).sum(axis=1, min_count=len(wj.columns))
            b1, b2 = rolling_beta2(r[j], rb, idx, w)
            b1, b2 = b1.shift(1), b2.shift(1)
            e[j], beta[j], beta2[j] = r[j] - b1 * rb - b2 * idx, b1, b2
            widx[j] = wj.abs().sum(axis=1)  # sum of |weights|, for the fee on the index legs
            hsidx[j] = (wj.abs() * hs_raw[wj.columns]).sum(axis=1)  # weighted half spread of the index legs
            idx_book = (wj * r_book[wj.columns]).sum(axis=1, min_count=len(wj.columns))
            e_book[j] = r_book[j] - b1.ffill() * r_book["BTCUSDT"] - b2.ffill() * idx_book
        else:
            raise ValueError(hedge)
    e, beta, beta2 = pd.DataFrame(e), pd.DataFrame(beta), pd.DataFrame(beta2)
    ys, sigma = targets(e, horizons)

    # leader features (same for every follower), masked where the leader is not live
    re_ = r["ETHUSDT"]
    lead = pd.DataFrame({
        "btc_ema3": ema(rb, 3),
        "btc_ema3_15": ema(rb, 3) - ema(rb, 15),
        "btc_ema15_60": ema(rb, 15) - ema(rb, 60),
        "eth_ema3": ema(re_, 3),
        "eth_ema3_15": ema(re_, 3) - ema(re_, 15),
        "btc_vol": np.log(ewm_vol(rb)),
    })
    # eth's move net of btc over the same window: the leader feature that is not collinear with btc's
    lead["eth_btc_ema3_15"] = lead["eth_ema3_15"] - lead["btc_ema3_15"]
    bcols = ["btc_ema3", "btc_ema3_15", "btc_ema15_60", "btc_vol"]
    lead[bcols] = lead[bcols].where(ok["BTCUSDT"], np.nan)
    ecols = ["eth_ema3", "eth_ema3_15", "eth_btc_ema3_15"]
    lead[ecols] = lead[ecols].where(ok["ETHUSDT"] & ok["BTCUSDT"], np.nan)

    tib = imbalance(tr["buy_volume"], tr["sell_volume"]).apply(ema, span=5)
    tib_btc = tib["BTCUSDT"].where(ok["BTCUSDT"])
    # book imbalance from the shifted snapshot, masked where that snapshot was itself a carryover
    bib = imbalance(bk["bid_size"], bk["ask_size"]).where(bk["carryover"] == 0).apply(ema, span=5)
    vol = tr["volume"].where(tr["volume"] > 0)  # zero-volume bars would give log(0)
    relvol = np.log(vol / vol.ewm(halflife=BARS_PER_DAY, adjust=False, ignore_na=True, min_periods=60).mean())

    parts = []
    for j in FOLLOWERS:
        okj = ok[j]
        f = pd.DataFrame(index=mid.index)
        f["sym"] = j
        f["ret"] = r[j]
        f["e"] = e[j]
        f["beta"] = beta[j]
        f["beta2"] = beta2[j]
        f["sigma_e"] = sigma[j]
        f["e_book"] = e_book[j]
        f["hspread"] = hs_raw[j]
        f["hspread_btc"] = hs_raw["BTCUSDT"]
        f["hspread_idx"] = hsidx[j]
        f["w_idx"] = widx[j]
        for h in horizons:
            f[f"y{h}"] = ys[h][j]
        for c in lead:
            f[c] = lead[c]
        f["gap5"] = e[j].rolling(5, min_periods=5).sum()
        f["gap15"] = e[j].rolling(15, min_periods=15).sum()
        f["gap60"] = e[j].rolling(60, min_periods=60).sum()
        f["own_ema3"] = ema(r[j], 3)
        f["own_ema3_15"] = ema(r[j], 3) - ema(r[j], 15)
        f["tib"] = tib[j]
        f["tib_diff"] = tib[j] - tib_btc
        f["bib"] = bib[j]
        f["relvol"] = relvol[j]
        own = ["gap5", "gap15", "gap60", "own_ema3", "own_ema3_15", "tib", "tib_diff", "bib", "relvol"]
        f[own] = f[own].where(okj, np.nan)
        parts.append(f)
    out = pd.concat(parts)
    out.index.name = "ts_end"
    # the bar's day is the day it starts in (file date), so the midnight bar stays with its day
    out["date"] = (out.index - pd.Timedelta(minutes=1)).date
    return out.reset_index().set_index(["ts_end", "sym"]).sort_index()


FEATURES = ["btc_ema3", "btc_ema3_15", "btc_ema15_60", "eth_ema3", "eth_ema3_15", "eth_btc_ema3_15", "btc_vol",
            "gap5", "gap15", "gap60", "own_ema3", "own_ema3_15", "tib", "tib_diff", "bib", "relvol"]
VERSION = 2  # bump when build() changes its columns, so cached panels are rebuilt


def dataset(name, d0, d1, **kw):
    # cache key carries every parameter and the build version, so a different hedge or window
    # never returns a stale panel
    key = "_".join([name, f"v{VERSION}", str(d0), str(d1)] + [f"{k}={kw[k]}" for k in sorted(kw)])
    return io.cached(key, lambda: build(d0, d1, **kw))
