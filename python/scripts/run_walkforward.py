# one config through the sliding-window walk-forward: forecasts, daily rank ic vs the baselines,
# cost-staged pnl, figures, and one line in experiments/registry.jsonl (kept or not).
# usage: python python/scripts/run_walkforward.py --config spread_v0 [--split select|walk_forward]
#        [--alpha 1.0] [--change "..."] [--parent RUN_ID] [--verdict kept|rejected|baseline|n/a]
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset import plot  # noqa: E402
from notset.config import ROOT, load, paths  # noqa: E402
from notset.eval import pnl, registry  # noqa: E402
from notset.eval.metrics import daily_rank_ic, summarize_ic  # noqa: E402
from notset.eval.walkforward import evaluate, walk_forward  # noqa: E402
from notset.features import build as fb  # noqa: E402

SPLITS = {
    # dataset range (with warm-up for betas and the first fit window) and the forecast range
    "select": {"data": ("2023-01-01", "2023-12-31"), "test": ("2023-03-02", "2023-12-31")},
    "walk_forward": {"data": ("2023-11-01", "2024-12-31"), "test": ("2024-01-01", "2024-12-31")},
}


def baselines(d, cfg, idx):
    # forecasts that need no fitting, on the same rows the model forecast
    b = cfg["baselines"]
    out = {"zero": pd.Series(0.0, index=idx)}
    out["static_btc_leads"] = -d.loc[idx, "gap5"] if b["static_btc_leads"] == "neg_gap5" else d.loc[idx, b["static_btc_leads"]]
    out["best_feature"] = b["best_feature_sign"] * d.loc[idx, b["best_feature"]]
    return out


def pnl_all(forecast, d, h, fee_bps, band=0.0):
    # equal-weight average over the followers of the per-follower unit-notional backtest
    bts = []
    ts = forecast.index.get_level_values("ts_end")
    for j in forecast.index.get_level_values("sym").unique():
        dj = d.xs(j, level="sym").loc[ts.min():ts.max() + pd.Timedelta(minutes=h)]  # the forecast period only
        fj = forecast.xs(j, level="sym")
        bts.append(pnl.backtest(fj, dj, h, fee_bps, band))
    bt = sum(bts) / len(bts)
    dates = (bt.index - pd.Timedelta(minutes=1)).date
    res, _ = pnl.summarize(bt, dates)
    return res, bt


def run(a):
    cfg = load(a.config)
    sp = SPLITS[a.split]
    h = cfg["target"]["horizon_bars"]
    alpha = a.alpha if a.alpha is not None else cfg["model"]["alpha"]
    run_id = registry.new_id(f"{cfg['name']}_{a.split}_a{alpha:g}")
    line = {"run_id": run_id, "parent_run_id": a.parent, "config": f"config/{a.config}.yaml", "split": a.split,
            "dates": {"start": sp["test"][0], "end": sp["test"][1]}, "followers": cfg["followers"], "horizon_bars": h,
            "hedge": cfg["hedge"], "features": cfg["features"], "alpha": alpha, "change": a.change,
            "target_clip": cfg["model"].get("target_clip"), "trade_band": cfg["costs"].get("trade_band", 0.0),
            "metrics": {}, "baselines": {}, "verdict": a.verdict, "status": "ok", "notes": ""}
    t0 = time.time()
    try:
        horizons = tuple(sorted(set(cfg["target"]["report_horizons"]) | {h}))
        d = fb.dataset("features", *sp["data"], beta_days=cfg["beta"]["window_days"], hedge=cfg["hedge"], horizons=horizons)
        wf = cfg["walk_forward"]
        band = cfg["costs"].get("trade_band", 0.0)
        fc, w = walk_forward(d, cfg["features"], f"y{h}", *sp["test"], window_days=wf["window_days"],
                             test_days=wf["test_days"], purge_bars=wf.get("purge_bars"), alpha=alpha,
                             target_clip=cfg["model"].get("target_clip"))
        fc = fc.dropna()
        res, ic = evaluate(fc, d, f"y{h}")
        for hh in cfg["target"]["report_horizons"]:
            if hh != h:
                res[f"ic_median_daily_h{hh}"] = float(daily_rank_ic(fc, d.loc[fc.index, f"y{hh}"], d.loc[fc.index, "date"]).median())
        pres, bt = pnl_all(fc, d, h, cfg["costs"]["taker_bps"], band)
        res.update(pres)
        line["metrics"] = res
        line["weights"] = {"mean": w.mean().round(4).to_dict(), "std": w.std().round(4).to_dict(), "refits": int(len(w))}
        curves = {"model": bt}
        for name, f in baselines(d, cfg, fc.index).items():
            if name == "zero":
                line["baselines"][name] = {"ic_median_daily": 0.0, "pnl_net_bps": {"mid": 0.0, "fees_spread": 0.0, "delay_1bar": 0.0}}
                continue
            f = f.dropna()
            bres, _ = evaluate(f, d, f"y{h}")
            bp, bbt = pnl_all(f, d, h, cfg["costs"]["taker_bps"], band)
            line["baselines"][name] = {k: bres[k] for k in ["ic_median_daily", "ic_ci95", "ic_pos_days_pct"]} | {k: bp[k] for k in ["pnl_net_bps", "sharpe"]}
            curves[name] = bbt
        figures(run_id, cfg["name"], a.split, curves, ic, w)
        rd = ROOT / "experiments" / "runs" / run_id
        rd.mkdir(parents=True, exist_ok=True)
        fc.to_pickle(rd / "forecast.pkl")
        w.to_csv(rd / "weights.csv")
        line["notes"] = f"{time.time() - t0:.0f}s, {len(fc)} forecasts, {res['n_days']} days"
    except Exception as e:
        line["status"], line["notes"] = "failed", f"{type(e).__name__}: {e}"
        traceback.print_exc()
    registry.append(line)
    print(json.dumps({k: line[k] for k in ["run_id", "status", "metrics", "baselines", "weights", "notes"] if k in line}, indent=1, default=float))
    return line


def figures(run_id, name, split, curves, ic, w):
    plot.style()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    styles = {"mid": "-", "fees_spread": "--", "delay_1bar": ":"}
    colors = {"model": plot.SERIES[0], "static_btc_leads": plot.SERIES[1], "best_feature": plot.SERIES[2]}
    for cname, bt in curves.items():
        daily = bt.groupby((bt.index - pd.Timedelta(minutes=1)).date).sum()
        for stage, ls in styles.items():
            lab = f"{cname} ({stage})" if cname == "model" else (cname if stage == "mid" else None)
            if cname != "model" and stage != "delay_1bar":
                continue
            ax.plot(pd.to_datetime(daily.index), 1e4 * daily[stage].cumsum(), ls=ls, color=colors.get(cname, "#52514e"), label=lab or f"{cname} (delay_1bar)")
    ax.axhline(0, color="#52514e", lw=0.8)
    ax.set_ylabel("cumulative hedged pnl, bps of follower notional (avg over followers)")
    ax.set_title(f"{name} {split}: cumulative OOS pnl by cost stage vs baselines (baselines after costs and delay)")
    ax.legend(ncol=2)
    plot.save(fig, f"pnl_{name}_{split}")

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    axes[0].hist(ic, bins=40, color=plot.SERIES[0])
    axes[0].axvline(ic.median(), color="#0b0b0b", lw=1)
    axes[0].set_title(f"daily rank IC, median {ic.median():.3f}, {100 * (ic > 0).mean():.0f}% days > 0")
    for k, c in enumerate(w.columns):
        axes[1].plot(w.index, w[c], lw=1.2, color=plot.SERIES[k % len(plot.SERIES)], label=c)
    axes[1].axhline(0, color="#52514e", lw=0.8)
    axes[1].set_title("ridge weights per refit (standardized features)")
    axes[1].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    plot.save(fig, f"ic_weights_{name}_{split}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="spread_v0")
    ap.add_argument("--split", default="walk_forward", choices=list(SPLITS))
    ap.add_argument("--alpha", type=float, default=None)
    ap.add_argument("--change", default="")
    ap.add_argument("--parent", default=None)
    ap.add_argument("--verdict", default="n/a")
    run(ap.parse_args())
