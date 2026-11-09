# a mock market-making desk with a book (ethan, 2026-11-07: "a desk that has a book, where hedging
# isn't always new"). the desk fills a share f of the market's observed taker flow passively, carries
# the alt inventory, beta-hedges it with btc only when the hedge drifts outside a band, and unwinds
# inventory beyond a limit at taker. the forecast does one thing: it shades the quotes, so the desk
# captures more of the flow on the side the forecast favours (optionally it also stretches the unwind
# limit on that side, capped). the value of the forecast is the pnl of this desk minus the same desk
# with no forecast, on the same flow. nothing here is a new round trip.
#
# v2 after the 2026-11-07 review: fills are priced at the bar's taker-side vwap and marked at the close
# (so intra-bar adverse selection is paid), fills are capped per bar, the limit stretch is capped at
# 1.5 L, the hedge and alt legs are attributed separately, and z is demeaned with a trailing window.
import numpy as np
import pandas as pd

from ..config import BARS_PER_DAY

DEFAULT = {"f": 0.02, "N0": 1e6, "L": 3.0, "T": 0.25, "s_inv": 0.5, "s_cap": 0.8, "cap_bar": 0.2, "stretch_max": 0.5,
           "k": 0.5, "s_max": 0.5, "z_in": 0.0, "tilt": 0.0, "fee_maker": 1.0, "fee_taker": 3.5, "fee_hedge": None}


def zscore(forecast, grid, days=7, demean=True):
    # forecast (indexed by ts_end, gaps where no forecast) -> z on the 1-min grid: trailing 7-day mean and
    # std on the grid (time, not rows), NaN -> 0, clipped. demeaning removes the slow component so the desk
    # acts on timing, not on a week-long lean
    f = forecast.reindex(grid)
    w, mp = days * BARS_PER_DAY, BARS_PER_DAY
    mu = f.rolling(w, min_periods=mp).mean() if demean else 0.0
    sd = f.rolling(w, min_periods=mp).std()
    return ((f - mu) / sd).fillna(0.0).clip(-5, 5)


def _lists(d, cols):
    return [np.nan_to_num(np.asarray(d[c], dtype=float)).tolist() for c in cols]


def simulate(buy, sell, mid, r_j, r_b, beta, hs_j, hs_b, z, p, use_signal=True, bvwap=None, svwap=None):
    # arrays on the 1-min grid. decisions at t use z[t]; they act on the fills and prices of bar t+1.
    # units: inventory, hedge and pnl in multiples of N0 dollars; fees in bps of notional.
    # plain python floats and lists: numpy scalar indexing made this loop 20x slower
    f, N0, L, T = p["f"], p["N0"], p["L"], p["T"]
    fm, ft = p["fee_maker"] * 1e-4, p["fee_taker"] * 1e-4
    fh = (p["fee_hedge"] if p.get("fee_hedge") is not None else p["fee_taker"]) * 1e-4  # btc hedge fee (taker unless stated)
    k, s_max, s_inv, s_cap, tilt, z_in = p["k"], p["s_max"], p["s_inv"], p["s_cap"], p["tilt"], p.get("z_in", 0.0)
    cap_bar, stretch_max = p.get("cap_bar", 1e9), p.get("stretch_max", 0.5)
    buy, sell, mid, r_j, r_b, hs_j, hs_b, z = (np.asarray(x, dtype=float).tolist() for x in (buy, sell, mid, r_j, r_b, hs_j, hs_b, z))
    beta = np.nan_to_num(np.asarray(beta, dtype=float), nan=1.0).tolist()
    n = len(mid)
    # fill prices: the desk buys from taker sellers at the taker-sell vwap and sells to taker buyers at the
    # taker-buy vwap; marked at the close mid. where a vwap is missing fall back to mid -/+ half spread
    if bvwap is None or svwap is None:
        pb = [mid[t] - hs_j[t] * mid[t] for t in range(n)]
        ps = [mid[t] + hs_j[t] * mid[t] for t in range(n)]
    else:
        bv, sv = (np.asarray(x, dtype=float).tolist() for x in (bvwap, svwap))
        pb = [sv[t] if sv[t] == sv[t] and sv[t] > 0 else mid[t] - hs_j[t] * mid[t] for t in range(n)]
        ps = [bv[t] if bv[t] == bv[t] and bv[t] > 0 else mid[t] + hs_j[t] * mid[t] for t in range(n)]
    inv = [0.0] * n
    pnl_alt = [0.0] * n      # inventory marked over the bar
    pnl_hedge = [0.0] * n    # btc hedge marked over the bar
    spread = [0.0] * n       # realized spread on the bar's fills (vwap to close) net of the maker fee
    cost_hedge = [0.0] * n   # taker fee + half spread on btc hedge trades
    cost_unwind = [0.0] * n  # taker fee + half spread on alt unwinds
    fills = [0.0] * n
    hedge_n = unwind_n = 0
    I = H = 0.0              # alt inventory, btc hedge (both in alt-notional units; H ~ beta * I)
    s = 0.0                  # quote skew decided at t-1, in [-s_cap, s_cap]: +1 = capture only taker sells (desk buys)
    fN = f / N0
    for t in range(1, n):
        # 1. mark the book over bar t with the positions held since t-1
        pnl_alt[t] = I * r_j[t]
        pnl_hedge[t] = -H * r_b[t]
        # 2. fills during bar t, capped per side; flow in dollars at the fill price, scaled to desk units
        m = mid[t]
        qb = fN * (1.0 + s) * sell[t] * pb[t]     # taker sells -> the desk buys
        qs = fN * (1.0 - s) * buy[t] * ps[t]      # taker buys -> the desk sells
        if qb > cap_bar:
            qb = cap_bar
        if qs > cap_bar:
            qs = cap_bar
        I += qb - qs
        fills[t] = qb + qs
        # realized spread: bought below the close mid earns, sold above it earns; fee on both
        spread[t] = qb * (m - pb[t]) / pb[t] + qs * (ps[t] - m) / ps[t] - fm * (qb + qs)
        # 3. unwind beyond the limit at taker; the limit is stretched on the forecast's side, at most to 1.5 L
        zt = z[t] if use_signal else 0.0
        act = use_signal and (zt >= z_in or zt <= -z_in)
        st = min(tilt * (zt if zt > 0.0 else -zt), stretch_max) if act else 0.0
        lim_long = L * (1.0 + st) if zt > 0.0 else L
        lim_short = L * (1.0 + st) if zt < 0.0 else L
        if I > lim_long:
            cost_unwind[t] = (I - lim_long) * (ft + hs_j[t])
            I = lim_long
            unwind_n += 1
        elif I < -lim_short:
            cost_unwind[t] = (-lim_short - I) * (ft + hs_j[t])
            I = -lim_short
            unwind_n += 1
        # 4. beta hedge inside a band: not every inventory change is a new btc trade
        want = beta[t] * I
        dh = want - H
        if dh > T or dh < -T:
            cost_hedge[t] = abs(dh) * (fh + hs_b[t])
            H = want
            hedge_n += 1
        # 5. quotes for the next bar: inventory skew (both desks) plus the forecast skew (signal desk),
        #    the latter only outside the dead zone |z| < z_in
        x = I / L
        s = -(1.0 if x > 1.0 else -1.0 if x < -1.0 else x) * s_inv
        if act:
            ks = k * zt
            s += s_max if ks > s_max else -s_max if ks < -s_max else ks
        s = s_cap if s > s_cap else -s_cap if s < -s_cap else s
        inv[t] = I
    out = pd.DataFrame({"pnl_alt": pnl_alt, "pnl_hedge": pnl_hedge, "spread": spread, "cost_hedge": cost_hedge,
                        "cost_unwind": cost_unwind, "fills": fills, "inv": inv})
    out["pnl_mtm"] = out["pnl_alt"] + out["pnl_hedge"]
    out["net"] = out["pnl_mtm"] + out["spread"] - out["cost_hedge"] - out["cost_unwind"]
    return out, {"hedge_trades": hedge_n, "unwinds": unwind_n}


def run_pair(data, z, p):
    # the same flow through the desk with and without the forecast; returns both frames and the counts
    args = _lists(data, ["buy", "sell", "mid", "r_j", "r_b"])
    beta = np.asarray(data["beta"], dtype=float)
    hs_j, hs_b = _lists(data, ["hs_j", "hs_b"])
    vw = {}
    if "bvwap" in data and "svwap" in data:
        vw = {"bvwap": np.asarray(data["bvwap"], dtype=float), "svwap": np.asarray(data["svwap"], dtype=float)}
    zz = np.asarray(z, dtype=float)
    with_sig, n1 = simulate(*args, beta, hs_j, hs_b, zz, p, True, **vw)
    base, n0 = simulate(*args, beta, hs_j, hs_b, zz, p, False, **vw)
    with_sig.index = base.index = data.index
    return with_sig, base, n1, n0


def day_key(index):
    # the bar's day is the day it starts in (file date), as everywhere else in the project
    return np.asarray((index - pd.Timedelta(minutes=1)).date)


def daily_frames(with_sig, base):
    # one groupby per desk: every daily statistic reads from these
    key = day_key(with_sig.index)
    return with_sig.groupby(key).sum(), base.groupby(key).sum()


def daily(frame, col):
    return frame[col].groupby(day_key(frame.index)).sum()


def summarize(with_sig, base, n1, n0, days, L=3.0, seed=0, gw=None, gb=None):
    # dollars per day at the stated desk size, bps of the desk's gross fills, per unit of risk budget,
    # the per-day distribution of the difference (one day = one observation), the legs, and the risk
    if gw is None:
        gw, gb = daily_frames(with_sig, base)
    d = with_sig["net"].sum() - base["net"].sum()
    gross_fills = base["fills"].sum()
    dw, db = gw["net"], gb["net"]
    dd = dw - db
    rng = np.random.default_rng(seed)
    boots = rng.choice(dd.values, size=(1000, len(dd)), replace=True).mean(axis=1)
    top5 = dd.abs().sort_values(ascending=False).head(5).index
    out = {"delta_pnl_per_day": float(d / days), "delta_bps_of_fills": float(1e4 * d / gross_fills) if gross_fills else np.nan,
           "delta_per_day_per_N0_of_limit_bps": float(1e4 * d / days / L),
           "delta_daily_mean": float(dd.mean()), "delta_daily_median": float(dd.median()), "delta_pos_days_pct": float(100 * (dd > 0).mean()),
           "delta_ci95_per_day": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))], "n_days": int(len(dd)),
           "delta_ex_top5_abs_days": float(dd.drop(top5).mean()), "top5_abs_delta_days": [str(x) for x in top5],
           "delta_alt_leg_per_day": float((with_sig["pnl_alt"].sum() - base["pnl_alt"].sum()) / days),
           "delta_hedge_leg_per_day": float((with_sig["pnl_hedge"].sum() - base["pnl_hedge"].sum()) / days),
           "delta_spread_per_day": float((with_sig["spread"].sum() - base["spread"].sum()) / days),
           "delta_cost_hedge_per_day": float((with_sig["cost_hedge"].sum() - base["cost_hedge"].sum()) / days),
           "delta_cost_unwind_per_day": float((with_sig["cost_unwind"].sum() - base["cost_unwind"].sum()) / days),
           "signal_net_per_day": float(with_sig["net"].sum() / days), "base_net_per_day": float(base["net"].sum() / days),
           "signal_sharpe_ann": float(dw.mean() / dw.std() * np.sqrt(365)) if dw.std() > 0 else 0.0,
           "base_sharpe_ann": float(db.mean() / db.std() * np.sqrt(365)) if db.std() > 0 else 0.0,
           "signal_mtm_per_day": float(with_sig["pnl_mtm"].sum() / days), "base_mtm_per_day": float(base["pnl_mtm"].sum() / days),
           "signal_spread_per_day": float(with_sig["spread"].sum() / days), "base_spread_per_day": float(base["spread"].sum() / days),
           "signal_cost_hedge_per_day": float(with_sig["cost_hedge"].sum() / days), "base_cost_hedge_per_day": float(base["cost_hedge"].sum() / days),
           "signal_cost_unwind_per_day": float(with_sig["cost_unwind"].sum() / days), "base_cost_unwind_per_day": float(base["cost_unwind"].sum() / days),
           "fills_per_day": float(gross_fills / days), "inv_std_signal": float(with_sig["inv"].std()), "inv_std_base": float(base["inv"].std()),
           "inv_max_signal": float(with_sig["inv"].abs().max()), "inv_max_base": float(base["inv"].abs().max()),
           "hedge_trades_per_day": n1["hedge_trades"] / days, "unwinds_per_day": n1["unwinds"] / days,
           "base_hedge_trades_per_day": n0["hedge_trades"] / days, "base_unwinds_per_day": n0["unwinds"] / days}
    return out
