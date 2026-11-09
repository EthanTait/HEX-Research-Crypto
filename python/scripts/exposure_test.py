# hedge exposure test on the 2023 selection year (decisions d3b and the beta window).
# question 1: which trailing beta window (1, 7, 30 days) leaves the least common exposure in e_j
#             while staying stable?
# question 2: does a second leg, the volume-weighted index of the other alts, remove what the
#             btc hedge leaves behind? (the market-model vs two-factor residual, quant methods)
# outputs: output/tables/exposure_test.csv, exposure_two_factor.csv; output/figures/beta_windows.png
import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset import io, plot  # noqa: E402
from notset.config import BARS_PER_DAY, FOLLOWERS, SYMS, paths  # noqa: E402
from notset.features.base import log_ret, rolling_beta  # noqa: E402
from notset.features.index import rolling_beta2, vw_index  # noqa: E402

TABLES = paths()["output"] / "tables"
SHORT = {s: s.replace("USDT", "") for s in SYMS}


def residual_summary(e):
    # how much common movement is left among the three follower residuals
    c = e.corr()
    off = c.values[np.triu_indices(len(c), 1)]
    ev = np.linalg.eigvalsh(c.values)
    return {"resid_pair_corr_mean": off.mean(), "resid_pair_corr_max": off.max(), "resid_pc1_share": ev.max() / ev.sum()}


def one_factor(r, rb, w_days):
    w = w_days * BARS_PER_DAY
    beta = pd.DataFrame({j: rolling_beta(r[j], rb, w).shift(1) for j in FOLLOWERS})
    e = pd.DataFrame({j: r[j] - beta[j] * rb for j in FOLLOWERS})
    return beta, e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--end", default="2023-12-31")
    a = ap.parse_args()
    plot.style()
    l1 = io.panel("l1bar", SYMS, a.start, a.end, ["close_mid"])
    tr = io.panel("tradebar", SYMS, a.start, a.end, ["volume"])
    r = log_ret(l1["close_mid"], l1["carryover"])
    rb = r["BTCUSDT"]
    dv = tr["volume"] * l1["close_mid"]
    day = (r.index - pd.Timedelta(minutes=1)).date

    rows, betas = [], {}
    for w_days in (1, 7, 30):
        beta, e = one_factor(r, rb, w_days)
        betas[w_days] = beta
        # common sample across windows: from day 31 on, so the 30-day window is not penalised for warm-up
        m = e.index >= e.index[0] + pd.Timedelta(days=31)
        e, beta = e[m], beta[m]
        rs = residual_summary(e)
        for j in FOLLOWERS:
            bj = beta[j]
            b_daily = bj.groupby(np.asarray(day)[m]).first()
            rows.append({"window_days": w_days, "follower": j, "beta_mean": bj.mean(), "beta_std": bj.std(),
                         "beta_p05": bj.quantile(0.05), "beta_p95": bj.quantile(0.95),
                         "beta_abs_daily_change": b_daily.diff().abs().mean(),
                         "r2_hedge": 1 - e[j].var() / r[j][m].var(),
                         "corr_e_btc": e[j].corr(rb[m]), "n": int(e[j].notna().sum()), **rs})
    t = pd.DataFrame(rows).set_index(["window_days", "follower"])
    TABLES.mkdir(parents=True, exist_ok=True)
    t.to_csv(TABLES / "exposure_test.csv")
    print("== exposure_test (one factor: btc)\n", t.round(4).to_string())

    # two-factor: btc plus the volume-weighted index of the other alts (eth + the other two followers)
    rows2 = []
    for w_days in (1, 7, 30):
        w = w_days * BARS_PER_DAY
        e1, e2 = {}, {}
        for j in FOLLOWERS:
            idx = vw_index(r, dv, exclude=("BTCUSDT", j))
            b1, b2 = rolling_beta2(r[j], rb, idx, w)
            b1, b2 = b1.shift(1), b2.shift(1)
            e2[j] = r[j] - b1 * rb - b2 * idx
            e1[j] = r[j] - rolling_beta(r[j], rb, w).shift(1) * rb
            rows2.append({"window_days": w_days, "follower": j, "beta_btc": b1.mean(), "beta_index": b2.mean(),
                          "beta_index_std": b2.std(), "r2_one_factor": 1 - e1[j].var() / r[j].var(),
                          "r2_two_factor": 1 - e2[j].var() / r[j].var()})
        e1, e2 = pd.DataFrame(e1), pd.DataFrame(e2)
        m = e2.index >= e2.index[0] + pd.Timedelta(days=31)
        s1, s2 = residual_summary(e1[m]), residual_summary(e2[m])
        for row in rows2[-3:]:
            row.update({f"one_{k}": v for k, v in s1.items()})
            row.update({f"two_{k}": v for k, v in s2.items()})
    t2 = pd.DataFrame(rows2).set_index(["window_days", "follower"])
    t2.to_csv(TABLES / "exposure_two_factor.csv")
    print("\n== exposure_two_factor (btc + leave-one-out alt index)\n", t2.round(4).to_string())

    fig, axes = plt.subplots(3, 1, figsize=(10, 7.5), sharex=True)
    for ax, j in zip(axes, FOLLOWERS):
        for w_days, c in zip((1, 7, 30), (plot.SERIES[4], plot.SERIES[0], plot.SERIES[1])):
            b = betas[w_days][j].resample("1D").first()
            ax.plot(b.index, b, color=c, lw=1.2, label=f"{w_days}-day window")
        ax.set_title(f"{SHORT[j]}: trailing beta on BTC (value at 00:00 each day)")
        ax.set_ylabel("beta")
    axes[0].legend(ncol=3)
    fig.tight_layout()
    plot.save(fig, "beta_windows")


if __name__ == "__main__":
    main()
