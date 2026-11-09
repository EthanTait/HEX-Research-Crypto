# milestone 1 step 3: feature-quality and collinearity survey on the 2023 selection year.
# every [submit] item of the course sheet that concerns features is one function here.
# outputs: output/tables/*.csv and output/figures/*.png, referenced by name in the report
# usage: python python/scripts/survey.py [--start 2023-01-01 --end 2023-12-31]
import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset import io, plot  # noqa: E402
from notset.config import BARS_PER_DAY, FOLLOWERS, SYMS, paths  # noqa: E402
from notset.eval.metrics import daily_rank_ic  # noqa: E402
from notset.features import build as fb  # noqa: E402
from notset.features.base import ema, log_ret  # noqa: E402
from notset.features.index import vw_index  # noqa: E402

TABLES = paths()["output"] / "tables"
SHORT = {s: s.replace("USDT", "") for s in SYMS}


def save_table(df, name):
    TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES / f"{name}.csv")
    print(f"\n== {name}\n{df.round(4).to_string()}")


def feature_stats(d):
    # item: distribution per feature with mean, std, skew, kurtosis (+ nan share, tails, drift by quarter)
    q = pd.to_datetime(d["date"]).dt.quarter.values
    rows = []
    for f in fb.FEATURES:
        x = d[f]
        qs = x.groupby(q).agg(["mean", "std"])
        rows.append({"feature": f, "mean": x.mean(), "std": x.std(), "skew": x.skew(), "ex_kurt": x.kurt(),
                     "nan_pct": 100 * x.isna().mean(), "p0.1": x.quantile(0.001), "p99.9": x.quantile(0.999),
                     "q_std_ratio": qs["std"].max() / qs["std"].min(),
                     "q_mean_drift_sd": (qs["mean"].max() - qs["mean"].min()) / x.std()})
    t = pd.DataFrame(rows).set_index("feature")
    t["flag"] = np.where(t["mean"].abs() / t["std"] > 0.1, "off-center ", "") + \
        np.where(t["ex_kurt"] > 10, "fat-tails ", "") + np.where(t["q_std_ratio"] > 2, "drift", "")
    save_table(t, "feature_stats")

    fig, axes = plt.subplots(3, 5, figsize=(13, 7))
    for ax, f in zip(axes.flat, fb.FEATURES):
        x = d[f].dropna()
        lo, hi = x.quantile(0.005), x.quantile(0.995)
        ax.hist(x.clip(lo, hi), bins=60, color=plot.SERIES[0], alpha=0.85)
        ax.set_title(f"{f}  skew {x.skew():.1f}  kurt {x.kurt():.0f}", fontsize=8)
        ax.set_yticks([])
    fig.suptitle("Feature distributions, 2023, followers pooled (clipped at 0.5/99.5 pct for display)")
    fig.tight_layout()
    plot.save(fig, "feature_hist")
    return t


def feature_corr(d):
    # item: feature cross-correlation matrix; pairs above 0.7 are flagged
    x = d[fb.FEATURES]
    pear, spear = x.corr(), x.corr(method="spearman")
    save_table(pear, "feature_corr_pearson")
    save_table(spear, "feature_corr_spearman")
    pairs = []
    for i, a in enumerate(fb.FEATURES):
        for b in fb.FEATURES[i + 1:]:
            if max(abs(pear.loc[a, b]), abs(spear.loc[a, b])) > 0.7:
                pairs.append({"a": a, "b": b, "pearson": pear.loc[a, b], "spearman": spear.loc[a, b]})
    save_table(pd.DataFrame(pairs), "feature_corr_pairs_over_0.7")
    fig, ax = plt.subplots(figsize=(8, 7))
    im = plot.heatmap(ax, pear, title="Feature correlation (Pearson), 2023, followers pooled")
    fig.colorbar(im, ax=ax, shrink=0.8)
    plot.save(fig, "feature_corr")
    return pear, pairs


def target_corr(d, horizons=(1, 5, 15)):
    # item: correlation of each feature with the forward target at several horizons, per follower.
    # pooled pearson and spearman, plus the pre-registered metric: median daily rank ic
    rows = []
    for j in FOLLOWERS:
        dj = d.xs(j, level="sym")
        for h in horizons:
            y = dj[f"y{h}"]
            for f in fb.FEATURES:
                m = dj[f].notna() & y.notna()
                ic = daily_rank_ic(dj[f][m], y[m], dj["date"][m])
                rows.append({"follower": j, "h": h, "feature": f, "pearson": dj[f][m].corr(y[m]),
                             "spearman": stats.spearmanr(dj[f][m], y[m]).statistic,
                             "ic_median_daily": ic.median(), "ic_pos_days_pct": 100 * (ic > 0).mean(), "n": int(m.sum())})
    t = pd.DataFrame(rows)
    t["suspicious"] = (t["h"] <= 5) & ((t["spearman"].abs() > 0.05) | (t["ic_median_daily"].abs() > 0.05))
    save_table(t.set_index(["follower", "h", "feature"]), "feature_target_corr")
    piv = t[t.h == 5].pivot(index="feature", columns="follower", values="ic_median_daily").loc[fb.FEATURES]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    yy = np.arange(len(piv))
    for k, j in enumerate(FOLLOWERS):
        ax.barh(yy + (k - 1) * 0.27, piv[j], height=0.25, color=plot.COLORS[j], label=SHORT[j])
    ax.set_yticks(yy, piv.index)
    ax.invert_yaxis()
    ax.axvline(0, color="#52514e", lw=0.8)
    ax.set_xlabel("median daily rank IC with y(t,5), 2023")
    ax.set_title("Feature vs 5-min hedged-spread target, per follower")
    ax.legend()
    plot.save(fig, "feature_target_ic_h5")
    return t


def btc_vs_eth(d0, d1):
    # item: correlation of btc returns and trade-based features with the corresponding eth features
    l1 = io.panel("l1bar", ["BTCUSDT", "ETHUSDT"], d0, d1, ["close_mid"])
    tr = io.panel("tradebar", ["BTCUSDT", "ETHUSDT"], d0, d1, ["buy_volume", "sell_volume", "volume"])
    r = log_ret(l1["close_mid"], l1["carryover"])
    tib = fb.imbalance(tr["buy_volume"], tr["sell_volume"])
    vol = tr["volume"].where(tr["volume"] > 0)
    relvol = np.log(vol / vol.ewm(halflife=BARS_PER_DAY, adjust=False, ignore_na=True, min_periods=60).mean())
    feats = {"ret_1min": r, "ret_ema3": r.apply(ema, span=3), "ret_ema15": r.apply(ema, span=15),
             "trade_imbalance": tib, "trade_imbalance_ema5": tib.apply(ema, span=5), "relvol": relvol,
             "volume_log": np.log(vol)}
    rows = [{"feature": k, "pearson": v["BTCUSDT"].corr(v["ETHUSDT"]),
             "spearman": v["BTCUSDT"].corr(v["ETHUSDT"], method="spearman")} for k, v in feats.items()]
    t = pd.DataFrame(rows).set_index("feature")
    save_table(t, "btc_vs_eth")
    return t


def cross_corr(d0, d1, spans=(1, 3, 10, 30, 60), chosen=3):
    # items: cross-correlation matrices across ema horizons; daily-averaged matrix for the chosen span;
    # the highest-vol day vs the long-run average
    l1 = io.panel("l1bar", SYMS, d0, d1, ["close_mid"])
    r = log_ret(l1["close_mid"], l1["carryover"])
    r.columns = [SHORT[c] for c in r.columns]
    mats = {s: (r if s == 1 else r.apply(ema, span=s)).corr() for s in spans}
    fig, axes = plt.subplots(1, len(spans), figsize=(3.2 * len(spans), 3.4))
    for ax, s in zip(axes, spans):
        plot.heatmap(ax, mats[s], vmin=0, vmax=1, cmap=plot.SEQUENTIAL, title=f"EMA span {s}" if s > 1 else "1-min returns")
    fig.suptitle("Cross-correlation of returns across EMA horizons, 2023 pooled")
    fig.tight_layout()
    plot.save(fig, "xcorr_ema_spans")
    long = pd.concat({s: m.stack() for s, m in mats.items()}, axis=1)
    long.columns = [f"span{s}" for s in spans]
    save_table(long, "xcorr_ema_spans")

    x = r.apply(ema, span=chosen) if chosen > 1 else r
    day = (x.index - pd.Timedelta(minutes=1)).date
    daily = {d: g.corr() for d, g in x.groupby(day) if g.notna().all(axis=1).sum() > 200}
    avg = sum(daily.values()) / len(daily)
    rv = (r["BTC"] ** 2).groupby(day).sum()
    hv = rv.idxmax()
    top5 = rv.sort_values(ascending=False).head(5)
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
    plot.heatmap(axes[0], avg, vmin=0, vmax=1, cmap=plot.SEQUENTIAL, title=f"Average of daily matrices (EMA {chosen}), 2023")
    plot.heatmap(axes[1], daily[hv], vmin=0, vmax=1, cmap=plot.SEQUENTIAL, title=f"Highest BTC-vol day {hv}")
    plot.heatmap(axes[2], daily[hv] - avg, vmin=-0.3, vmax=0.3, title="Difference (day - average)")
    fig.tight_layout()
    plot.save(fig, "xcorr_daily_vs_highvol")
    save_table(avg, f"xcorr_daily_avg_ema{chosen}")
    save_table(daily[hv], f"xcorr_highvol_day_{hv}")
    save_table(pd.DataFrame({"btc_realized_var": top5, "btc_vol_bps_per_min": 1e4 * np.sqrt(top5 / BARS_PER_DAY)}), "top5_vol_days")
    offd = lambda m: m.values[np.triu_indices(5, 1)].mean()
    print(f"mean pairwise corr: long-run {offd(avg):.3f}, high-vol day {hv} {offd(daily[hv]):.3f}")
    return avg, hv


def index_hist(d0, d1):
    # item: volume-weighted index of the 5 names; return histograms of the index and each name on one plot
    l1 = io.panel("l1bar", SYMS, d0, d1, ["close_mid"])
    tr = io.panel("tradebar", SYMS, d0, d1, ["volume"])
    r = log_ret(l1["close_mid"], l1["carryover"])
    dv = tr["volume"] * l1["close_mid"]
    idx = vw_index(r, dv)
    series = {"index": idx, **{s: r[s] for s in SYMS}}
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.linspace(-60, 60, 121)
    for k, v in series.items():
        ax.hist(1e4 * v.dropna().clip(-60e-4, 60e-4), bins=bins, histtype="step", lw=1.4, density=True,
                color=plot.COLORS[k], label=SHORT.get(k, k))
    ax.set_yscale("log")
    ax.set_xlabel("1-min log return, bps (clipped at +/-60)")
    ax.set_ylabel("density (log)")
    ax.set_title("Return distributions, 2023: volume-weighted index and each name")
    ax.legend()
    plot.save(fig, "index_return_hist")
    t = pd.DataFrame({k: {"std_bps": 1e4 * v.std(), "skew": v.skew(), "ex_kurt": v.kurt(), "n": v.notna().sum()}
                      for k, v in series.items()}).T
    save_table(t, "index_return_stats")
    return t


def lag_profile(d, kmax=15):
    # item: corr(r_BTC(t-k), e_j(t)) and corr(r_BTC(t-k), r_j(t)) for k = 0..kmax, per follower
    l1 = io.panel("l1bar", ["BTCUSDT"], str(d["date"].min()), str(d["date"].max()), ["close_mid"])
    rb = log_ret(l1["close_mid"], l1["carryover"])["BTCUSDT"]
    rows = []
    for j in FOLLOWERS:
        dj = d.xs(j, level="sym")
        for k in range(kmax + 1):
            x = rb.shift(k).reindex(dj.index)
            rows.append({"follower": j, "k": k, "corr_raw": x.corr(dj["ret"]), "corr_hedged": x.corr(dj["e"])})
    t = pd.DataFrame(rows)
    save_table(t.set_index(["follower", "k"]), "lag_profile")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=False)
    for ax, col, title in zip(axes, ["corr_raw", "corr_hedged"], ["corr(r_BTC(t-k), r_j(t))", "corr(r_BTC(t-k), e_j(t))  (hedged)"]):
        for j in FOLLOWERS:
            tj = t[t.follower == j]
            ax.plot(tj["k"], tj[col], marker="o", ms=3, color=plot.COLORS[j], label=SHORT[j])
        ax.axhline(0, color="#52514e", lw=0.8)
        ax.set_xlabel("lag k (minutes)")
        ax.set_title(title)
    axes[0].legend()
    fig.suptitle("Lag profile of BTC returns vs follower, 2023")
    fig.tight_layout()
    plot.save(fig, "lag_profile")
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--end", default="2023-12-31")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    plot.style()
    d = fb.dataset("features", a.start, a.end)
    print("dataset", d.shape)
    steps = {"stats": lambda: feature_stats(d), "corr": lambda: feature_corr(d), "target": lambda: target_corr(d),
             "btceth": lambda: btc_vs_eth(a.start, a.end), "xcorr": lambda: cross_corr(a.start, a.end),
             "index": lambda: index_hist(a.start, a.end), "lag": lambda: lag_profile(d)}
    for k, f in steps.items():
        if not a.only or k in a.only.split(","):
            f()


if __name__ == "__main__":
    main()
