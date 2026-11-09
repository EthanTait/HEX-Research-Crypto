# EVALUATION.md section 2: per-day rank ic, day-block bootstrap. one day = one observation,
# because overlapping 5-min targets sampled every minute are not independent
import numpy as np
import pandas as pd


def daily_rank_ic(signal, target, dates, min_obs=30):
    # spearman inside each day = pearson of within-day ranks. vectorized: rank by day, then the
    # correlation from per-day sums (no python loop over days)
    df = pd.DataFrame({"s": np.asarray(signal, dtype=float), "y": np.asarray(target, dtype=float), "d": np.asarray(dates)}).dropna()
    g = df.groupby("d")
    rs, ry = g["s"].rank(), g["y"].rank()
    df = pd.DataFrame({"d": df["d"].values, "rs": rs.values, "ry": ry.values})
    df["rs2"], df["ry2"], df["rsy"] = df.rs**2, df.ry**2, df.rs * df.ry
    a = df.groupby("d").agg(n=("rs", "size"), rs=("rs", "sum"), ry=("ry", "sum"), rs2=("rs2", "sum"), ry2=("ry2", "sum"), rsy=("rsy", "sum"))
    a = a[a.n >= min_obs]
    cov = a.rsy / a.n - (a.rs / a.n) * (a.ry / a.n)
    vs = a.rs2 / a.n - (a.rs / a.n) ** 2
    vy = a.ry2 / a.n - (a.ry / a.n) ** 2
    ic = cov / np.sqrt(vs * vy)
    ic.name = "ic"
    return ic.dropna()


def summarize_ic(ic, n_boot=1000, seed=0):
    # median, share of positive days, and a day-block bootstrap ci on the median
    ic = ic.dropna()
    rng = np.random.default_rng(seed)
    boots = np.median(rng.choice(ic.values, size=(n_boot, len(ic)), replace=True), axis=1)
    return {"ic_median_daily": float(ic.median()), "ic_mean_daily": float(ic.mean()),
            "ic_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "ic_se": float(boots.std()), "ic_pos_days_pct": float(100 * (ic > 0).mean()), "n_days": int(len(ic))}
