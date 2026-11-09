# writes python/notebooks/walkthrough.ipynb: the whole pipeline, step by step, light enough to run in
# a few minutes against the hdb and the cached results. outputs are stripped before commit (nbstripout).
# usage: python python/scripts/make_walkthrough.py && jupyter nbconvert --execute --to notebook --inplace python/notebooks/walkthrough.ipynb
import sys
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset.config import ROOT  # noqa: E402

OUT = ROOT / "python" / "notebooks" / "walkthrough.ipynb"

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))

md("""
# HEX Research, Milestone 1: the pipeline step by step

q hdb -> PyKX -> features and target -> walk-forward ridge -> metric -> improvement loop -> economics.
Run from the repo root in the `notset` env with the hdb built (`q/README.md`). Each step reads the same code the scripts use.
""")
code("""
import sys, json, warnings
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Image, display
warnings.filterwarnings("ignore")
ROOT = Path.cwd() if (Path.cwd() / "python" / "notset").exists() else Path.cwd().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from notset import io, plot
from notset.config import FOLLOWERS, SYMS, paths
from notset.features import build as fb
from notset.features.base import live, log_ret
from notset.features.target import hedged, targets
from notset.eval.walkforward import walk_forward, evaluate
from notset.eval import desk
plot.style()
FIG, TAB = paths()["output"] / "figures", paths()["output"] / "tables"
kx = io.q()  # mounts data/hdb through q/init.q; from here paths must be absolute
print(kx.q("tables[]"), "| q cwd:", kx.q("system \\"pwd\\""))
""")

md("""
## 1. Data layer: q owns storage, python only calls `bars[]` and `coverage[]`
""")
code("""
cov = io.coverage("l1bar", "2023-01-01", "2024-12-31")
cov.pivot(index="sym", columns="year", values=["bars", "co_ge1", "co_m1"])
""")
code("""
io.bars("l1bar", ["BTCUSDT", "SOLUSDT"], "2024-01-15", "2024-01-15", ["close_mid", "close_bid", "close_ask"]).head()
""")

md("""
## 2. Common grid, stale bars, returns
`live()` masks a carryover bar and the bar after it; nothing is forward-filled. The grid is the full minute range, so a missing day is NaN, not a compressed gap.
""")
code("""
p = io.panel("l1bar", SYMS, "2024-01-12", "2024-01-16", ["close_mid"])
mid, carry = p["close_mid"], p["carryover"]
ok = live(mid, carry)
r = log_ret(mid, carry)
pd.DataFrame({"bars": mid.shape[0], "nan mid": mid.isna().sum(), "carryover != 0": (carry != 0).sum(), "masked returns": r.isna().sum()}).T
""")

md("""
## 3. Target
`e_j(t) = r_j(t) - beta_j(t) * r_BTC(t)` with a trailing 7-day beta from bars <= t-1; `y_j(t,h) = sum e_j(t+1..t+h) / sigma_e_j(t)`.
""")
code("""
p = io.panel("l1bar", SYMS, "2024-01-01", "2024-02-29", ["close_mid"])
r = log_ret(p["close_mid"], p["carryover"])
e, beta = hedged(r, "BTCUSDT", beta_days=7, followers=FOLLOWERS)
ys, sigma = targets(e, (1, 5, 15))
pd.DataFrame({"beta mean": beta.mean(), "beta std": beta.std(), "y5 std": ys[5].std(), "y5 kurt": ys[5].kurt()})
""")

md("""
## 4. Features
The candidate menu (`notset.features.build`): leader EMAs as differences, catch-up gaps (sums of e_j), own EMA, trade and book imbalance, vol. All trailing, masked where the name is not live, book shifted one bar.
""")
code("""
d = fb.build("2024-02-01", "2024-02-14")
print(fb.FEATURES)
d.xs("SOLUSDT", level="sym")[["ret", "e", "y5"] + fb.FEATURES[:6]].describe().T[["count", "mean", "std"]]
""")

md("""
## 5. Survey on 2023 (selection year)
Produced by `python/scripts/survey.py` and `exposure_test.py`; the tables are read back here.
""")
code("""
t = pd.read_csv(TAB / "feature_target_corr.csv")
piv = t[t.h == 5].pivot(index="feature", columns="follower", values="ic_median_daily")
piv.loc[[f for f in fb.FEATURES if f in piv.index]].round(3)
""")
code("""
lag = pd.read_csv(TAB / "lag_profile.csv")
lag.pivot(index="k", columns="follower", values="corr_raw").iloc[:6].round(3)
""")
code("""
for name in ["feature_target_ic_h5", "lag_profile", "beta_windows"]:
    display(Image(filename=str(FIG / f"{name}.png"), width=900))
""")

md("""
## 6. Walk-forward ridge and the pre-registered metric
60-day fit, purge h bars, 7-day test, weekly refit; features standardized on the fit window and clipped at 5 sd; target clipped at 5 in the fit (loop iteration 1). Metric: median daily rank IC, one day = one observation. Here on two months so it runs in seconds; the full-year runs are in the registry.
""")
code("""
features = ["btc_ema3_15", "gap15", "gap60", "own_ema3", "tib", "tib_diff", "btc_vol"]
d = fb.dataset("features", "2023-11-01", "2024-12-31", beta_days=7, hedge="btc")  # cached panel
fc, w = walk_forward(d, features, "y5", "2024-02-01", "2024-03-31", window_days=60, test_days=7, alpha=1.0, target_clip=5.0)
res, ic = evaluate(fc.dropna(), d, "y5")
print({k: res[k] for k in ["ic_median_daily", "ic_ci95", "ic_pos_days_pct", "n_days"]})
w.round(3).T
""")
code("""
fig, ax = plt.subplots(figsize=(7, 3))
ax.hist(ic, bins=25, color=plot.SERIES[0]); ax.axvline(ic.median(), color="k"); ax.set_title("daily rank IC, Feb-Mar 2024"); plt.show()
""")

md("""
## 7. Improvement loop: every trial, kept or not
Rule D10: keep a change only if the median daily IC improves by more than its bootstrap s.e. and net PnL is not worse.
""")
code("""
reg = [json.loads(l) for l in (ROOT / "experiments" / "registry.jsonl").read_text().splitlines() if l.strip()]
rows = [{"config": r["config"].split("/")[-1], "split": r["split"], "ic": r["metrics"].get("ic_median_daily"), "ci": r["metrics"].get("ic_ci95"),
         "pos_days": r["metrics"].get("ic_pos_days_pct"), "change": r.get("change", "")[:60]}
        for r in reg if r.get("status") == "ok" and "metrics" in r and "ic_median_daily" in r.get("metrics", {})]
pd.DataFrame(rows).round(4)
""")
code("""
display(Image(filename=str(FIG / "loop_metric.png"), width=950))
""")

md("""
## 8. Economics
A standalone hedged trade cannot pay taker fees (fees are 90-97% of the cost; the edge is 1-2 bps and accrues over two hours). The buyer is a desk with a book; the mock desk's value of the forecast is the difference between the same desk with and without it.
""")
code("""
pd.read_csv(TAB / "diag_cost_decomposition.csv", index_col=0).round(2)
""")
code("""
desks = [r for r in reg if r["run_id"].split("_", 1)[1].startswith("desk2_") and r["split"] == "walk_forward" and "total" in r.get("metrics", {})]
pd.DataFrame([{"change": r["change"][:55], "delta/day": r["metrics"]["total"]["delta_pnl_per_day"], "bps of fills": r["metrics"]["total"]["delta_bps_of_fills"],
               "per N0 of limit": r["metrics"]["total"].get("delta_per_day_per_N0_of_limit_bps"), "days>0 %": r["metrics"]["total"]["delta_pos_days_pct"],
               "ci": r["metrics"]["total"]["delta_ci95_per_day"]} for r in desks]).round(4)
""")
code("""
display(Image(filename=str(FIG / "final_pnl_v1.png"), width=950))
display(Image(filename=str(FIG / "desk2_walk_forward_chosen.png"), width=950))
""")

md("""
## 9. What is next
- 2025 holdout: opened once, through `/holdout`, when the method is frozen.
- Hank's tick capture: load into the q tick slot, aggregate to 1-min bars, run the same pipeline as a forward test; lag profile at second horizons.
- Desk: fill model with queue position; rebate fee schedule; the 60-minute forecast if the holdout confirms it.
""")

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}})
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print("wrote", OUT, len(cells), "cells")
