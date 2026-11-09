# milestone 1 steps 5-6: the loop metric across iterations (every trial, kept or not), the final
# plot v1 (cumulative OOS pnl by cost stage vs baselines) and the lecture-5 sorted-signal plot.
# usage: python python/scripts/final_plots.py --run <run_id of the final model>
import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset import plot  # noqa: E402
from notset.config import ROOT, load  # noqa: E402
from notset.eval import pnl  # noqa: E402
from notset.features import build as fb  # noqa: E402

REG = ROOT / "experiments" / "registry.jsonl"


def registry():
    return [json.loads(l) for l in REG.read_text().splitlines() if l.strip()]


def loop_plot(verdicts):
    runs = [r for r in registry() if r.get("split") == "walk_forward" and r.get("status") == "ok" and "metrics" in r and r["metrics"]]
    rows = []
    for r in runs:
        m = r["metrics"]
        rows.append({"run_id": r["run_id"], "config": r["config"].split("/")[-1].replace(".yaml", ""),
                     "change": r.get("change", ""), "ic": m["ic_median_daily"], "lo": m["ic_ci95"][0], "hi": m["ic_ci95"][1],
                     "pnl_delay": m["pnl_net_bps"]["delay_1bar"], "pnl_mid": m["pnl_net_bps"]["mid"],
                     "verdict": verdicts.get(r["run_id"], r.get("verdict", "n/a"))})
    t = pd.DataFrame(rows)
    t.to_csv(ROOT / "output" / "tables" / "loop_iterations.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    x = np.arange(len(t))
    for ax, col, lab in zip(axes, ["ic", "pnl_delay"], ["median daily rank IC (2024 OOS)", "net PnL after fees, spread and 1-bar delay, bps"]):
        for i, r in t.iterrows():
            kept = r["verdict"] in ("kept", "baseline")
            ax.scatter(i, r[col], s=60, color=plot.SERIES[0] if kept else "#c3c2b7", edgecolor="#0b0b0b", zorder=3)
        if col == "ic":
            ax.errorbar(x, t["ic"], yerr=[t["ic"] - t["lo"], t["hi"] - t["ic"]], fmt="none", ecolor="#52514e", capsize=3)
            b = [r for r in runs if r["config"].endswith("spread_v0.yaml")]
            if b:
                ax.axhline(b[0]["baselines"]["best_feature"]["ic_median_daily"], color=plot.SERIES[2], ls="--", lw=1, label="best standalone feature (-gap15)")
                ax.axhline(b[0]["baselines"]["static_btc_leads"]["ic_median_daily"], color=plot.SERIES[1], ls=":", lw=1, label="static BTC-leads (-gap5)")
                ax.legend(loc="lower right")
        ax.set_xticks(x, t["config"], rotation=20)
        ax.set_title(lab)
        ax.axhline(0, color="#52514e", lw=0.8)
    fig.suptitle("Improvement loop: every trial (filled = kept or baseline, grey = rejected)")
    fig.tight_layout()
    plot.save(fig, "loop_metric")
    print(t[["config", "ic", "lo", "hi", "pnl_mid", "pnl_delay", "verdict", "change"]].round(4).to_string())
    return t


def final_plot(run_id):
    r = [x for x in registry() if x["run_id"] == run_id][0]
    cfg = load(r["config"].split("/")[-1].replace(".yaml", ""))
    h = cfg["target"]["horizon_bars"]
    d = fb.dataset("features", "2023-11-01", "2024-12-31", beta_days=cfg["beta"]["window_days"], hedge=cfg["hedge"])
    fc = pd.read_pickle(ROOT / "experiments" / "runs" / run_id / "forecast.pkl")
    band = cfg["costs"].get("trade_band", 0.0)
    fee = cfg["costs"]["taker_bps"]
    ts = fc.index.get_level_values("ts_end")
    curves = {"model": fc, "static BTC-leads (-gap5)": -d.loc[fc.index, "gap5"], "best feature (-gap15)": -d.loc[fc.index, "gap15"]}
    daily = {}
    for name, f in curves.items():
        bts = []
        for j in f.index.get_level_values("sym").unique():
            dj = d.xs(j, level="sym").loc[ts.min():ts.max() + pd.Timedelta(minutes=h)]
            bts.append(pnl.backtest(f.xs(j, level="sym").dropna(), dj, h, fee, band))
        bt = sum(bts) / len(bts)
        daily[name] = 1e4 * bt.groupby((bt.index - pd.Timedelta(minutes=1)).date).sum().cumsum()
    colors = dict(zip(curves, [plot.SERIES[0], plot.SERIES[1], plot.SERIES[2]]))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
    for name, c in daily.items():
        axes[0].plot(pd.to_datetime(c.index), c["mid"], color=colors[name], label=name)
    axes[0].set_title("Stage 1: mid-to-mid, no costs")
    for name, c in daily.items():
        axes[1].plot(pd.to_datetime(c.index), c["fees_spread"], color=colors[name], ls="--", label=f"{name}, fees + spread" if name == "model" else None)
        axes[1].plot(pd.to_datetime(c.index), c["delay_1bar"], color=colors[name], ls=":", label=f"{name}, + 1-bar delay")
    axes[1].set_title("Stages 2-3: after 5 bps taker fee + half spread on both legs, and 1-bar delay")
    for ax in axes:
        ax.axhline(0, color="#52514e", lw=0.8)
        ax.set_ylabel("cumulative hedged PnL, bps of follower notional")
        ax.legend(fontsize=7)
    fig.suptitle(f"Final plot v1: {cfg['name']} on the 2024 walk-forward OOS, hedged position proportional to the forecast, held {h} bars, no-trade band {band} sd")
    fig.tight_layout()
    plot.save(fig, "final_pnl_v1")
    out = pd.DataFrame({f"{k}:{s}": v[s] for k, v in daily.items() for s in ["mid", "fees_spread", "delay_1bar"]})
    out.to_csv(ROOT / "output" / "tables" / "final_pnl_curves.csv")

    # lecture 5 sorted-signal plot: forecast quantile bins vs the realized 5-bar hedged move
    y = d.loc[fc.index, f"y{h}"]
    s = d.loc[fc.index, "sigma_e"]
    realized_bps = 1e4 * y * s
    q = pd.qcut(fc.rank(method="first"), 20, labels=False)
    g = pd.DataFrame({"q": q, "y": y, "bps": realized_bps, "f": fc}).dropna().groupby("q").agg(fc_mean=("f", "mean"), y_mean=("y", "mean"), bps_mean=("bps", "mean"), n=("y", "size"))
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    axes[0].bar(g.index, g["y_mean"], color=plot.SERIES[0])
    axes[0].set_title("mean realized y(t,5) (vol-scaled) by forecast vigintile")
    axes[1].bar(g.index, g["bps_mean"], color=plot.SERIES[0])
    axes[1].set_title("mean realized 5-bar hedged move, bps, by forecast vigintile")
    for ax in axes:
        ax.axhline(0, color="#52514e", lw=0.8)
        ax.set_xlabel("forecast vigintile (0 = most negative, 19 = most positive)")
    fig.suptitle("Sorted signal, 2024 OOS: does the forecast order the outcome?")
    fig.tight_layout()
    plot.save(fig, "sorted_signal")
    g.to_csv(ROOT / "output" / "tables" / "sorted_signal.csv")
    print(g.round(4).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--verdicts", default="{}", help="json run_id -> verdict, for runs logged before the decision")
    a = ap.parse_args()
    plot.style()
    (ROOT / "output" / "tables").mkdir(parents=True, exist_ok=True)
    loop_plot(json.loads(a.verdicts))
    final_plot(a.run)
