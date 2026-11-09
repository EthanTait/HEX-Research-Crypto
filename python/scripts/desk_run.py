# the mock desk (notset.eval.desk) on a logged run's forecasts. selection year: a small parameter grid,
# every combination logged; walk-forward year: the chosen parameters, placebos, decision-delay profile,
# and sensitivities. every call appends one registry line.
# usage: python python/scripts/desk_run.py --run <run_id> --split select|walk_forward [--grid] [--params '{...}']
#        [--placebo-shift-days N] [--delay-bars K] [--no-demean] [--tag name] [--change "..."]
import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset import io, plot  # noqa: E402
from notset.config import FOLLOWERS, ROOT, SYMS, load  # noqa: E402
from notset.eval import desk, registry  # noqa: E402
from notset.features import build as fb  # noqa: E402
from notset.features.base import live  # noqa: E402

TAB = ROOT / "output" / "tables"
# dataset range (with warm-up) and the forecast range of each split; the desk runs on the forecast range only
RANGES = {"select": {"data": ("2023-01-01", "2023-12-31"), "test": ("2023-03-02", "2023-12-31")},
          "walk_forward": {"data": ("2023-11-01", "2024-12-31"), "test": ("2024-01-01", "2024-12-31")}}


def inputs(run_id, split, cfg, demean=True):
    # per follower: flow (masked where either the level1 bar or the trade bar is not live), close mid,
    # taker-side vwaps for fill pricing, book returns (unmasked, so a held position earns the real move),
    # trailing beta, close half spreads, and z on the 1-min grid
    d0, d1 = RANGES[split]["data"]
    t0, t1 = RANGES[split]["test"]
    d = fb.dataset("features", d0, d1, beta_days=cfg["beta"]["window_days"], hedge=cfg["hedge"])
    fc = pd.read_pickle(ROOT / "experiments" / "runs" / run_id / "forecast.pkl")
    l1 = io.panel("l1bar", SYMS, d0, d1, ["close_mid", "close_bid", "close_ask"])
    tr = io.panel("tradebar", SYMS, d0, d1, ["buy_volume", "sell_volume", "trade_count", "buy_vwap", "sell_vwap"])
    mid = l1["close_mid"]
    ok_l1 = live(mid, l1["carryover"])
    ok_tr = (tr["carryover"] == 0) & (tr["trade_count"] > 0)
    r_book = np.log(mid.ffill()).diff()
    hs = ((l1["close_ask"] - l1["close_bid"]) / (2 * mid)).ffill()
    grid = io.grid("l1bar", t0, t1)  # file dates t0..t1 -> ts_end t0 00:01 .. t1+1 00:00
    out = {}
    for j in FOLLOWERS:
        fj = fc.xs(j, level="sym")
        z = desk.zscore(fj, grid, demean=demean)
        dj = d.xs(j, level="sym")
        okj = ok_l1[j] & ok_tr[j]
        out[j] = pd.DataFrame({"buy": tr["buy_volume"][j].where(okj), "sell": tr["sell_volume"][j].where(okj),
                               "mid": mid[j].ffill(), "r_j": r_book[j], "r_b": r_book["BTCUSDT"],
                               "beta": dj["beta"].reindex(mid.index).ffill(), "hs_j": hs[j], "hs_b": hs["BTCUSDT"],
                               "bvwap": tr["buy_vwap"][j].where(okj), "svwap": tr["sell_vwap"][j].where(okj)}).reindex(grid), z
    days = len(np.unique((grid - pd.Timedelta(minutes=1)).date))
    return out, days


def one(data, params, shift_days=0, delay_bars=0):
    # shift_days > 0: circular time-shift placebo (the desk is fed the forecast from shift_days earlier);
    # delay_bars > 0: the desk acts on a forecast that is delay_bars old
    res, curves = {}, {}
    for j, (dj, z) in data.items():
        if shift_days:
            z = pd.Series(np.roll(z.values, shift_days * 1440), index=z.index)
        if delay_bars:
            z = z.shift(delay_bars).fillna(0.0)
        w, b, n1, n0 = desk.run_pair(dj, z, params)
        gw, gb = desk.daily_frames(w, b)
        days = len(gw)
        res[j] = desk.summarize(w, b, n1, n0, days, L=params["L"], gw=gw, gb=gb)
        curves[j] = (w, b, gw, gb)
    sums = ["delta_pnl_per_day", "signal_net_per_day", "base_net_per_day", "signal_mtm_per_day", "base_mtm_per_day",
            "signal_spread_per_day", "base_spread_per_day", "signal_cost_hedge_per_day", "base_cost_hedge_per_day",
            "signal_cost_unwind_per_day", "base_cost_unwind_per_day", "fills_per_day", "hedge_trades_per_day", "unwinds_per_day",
            "base_hedge_trades_per_day", "delta_alt_leg_per_day", "delta_hedge_leg_per_day", "delta_spread_per_day",
            "delta_cost_hedge_per_day", "delta_cost_unwind_per_day"]
    tot = {k: float(sum(res[j][k] for j in res)) for k in sums}
    tot["delta_bps_of_fills"] = float(1e4 * tot["delta_pnl_per_day"] / tot["fills_per_day"]) if tot["fills_per_day"] else np.nan
    tot["delta_per_day_per_N0_of_limit_bps"] = float(1e4 * tot["delta_pnl_per_day"] / (params["L"] * len(res)))
    tot["inv_std_signal_mean"] = float(np.mean([res[j]["inv_std_signal"] for j in res]))
    tot["inv_std_base_mean"] = float(np.mean([res[j]["inv_std_base"] for j in res]))
    tot["inv_max_signal"] = float(max(res[j]["inv_max_signal"] for j in res))
    # per-day distribution of the summed difference over the three names, and the two desks' own sharpe
    dd = dw = db = None
    for j, (w, b, gw, gb) in curves.items():
        x, y_, zb = gw["net"] - gb["net"], gw["net"], gb["net"]
        dd = x if dd is None else dd.add(x, fill_value=0.0)
        dw = y_ if dw is None else dw.add(y_, fill_value=0.0)
        db = zb if db is None else db.add(zb, fill_value=0.0)
    boots = np.random.default_rng(0).choice(dd.values, size=(1000, len(dd)), replace=True).mean(axis=1)
    top5 = dd.abs().sort_values(ascending=False).head(5).index
    tot.update({"delta_daily_median": float(dd.median()), "delta_pos_days_pct": float(100 * (dd > 0).mean()),
                "delta_ci95_per_day": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))], "n_days": int(len(dd)),
                "delta_ex_top5_abs_days": float(dd.drop(top5).mean()), "top5_abs_delta_days": [str(x) for x in top5],
                "signal_sharpe_ann": float(dw.mean() / dw.std() * np.sqrt(365)), "base_sharpe_ann": float(db.mean() / db.std() * np.sqrt(365)),
                "delta_sharpe_ann": float(dd.mean() / dd.std() * np.sqrt(365))})
    # EVALUATION.md section 3: without the five highest btc-vol days (btc is the common factor; own-vol variant too)
    rb = next(iter(data.values()))[0]["r_b"]
    rv = (rb**2).groupby(np.asarray((rb.index - pd.Timedelta(minutes=1)).date)).sum()
    top5v = rv.sort_values(ascending=False).head(5).index
    tot["delta_ex_top5_btc_vol_days"] = float(dd.drop(top5v, errors="ignore").mean())
    tot["top5_btc_vol_days"] = [str(x) for x in top5v]
    return res, tot, curves


def figures(curves, name, params):
    plot.style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    total_w = total_b = None
    for j, (w, b, gw, gb) in curves.items():
        dw, db = gw["net"].cumsum(), gb["net"].cumsum()
        axes[0].plot(pd.to_datetime(dw.index), dw - db, color=plot.COLORS[j], label=j.replace("USDT", ""))
        total_w = dw if total_w is None else total_w + dw
        total_b = db if total_b is None else total_b + db
    axes[0].plot(pd.to_datetime(total_w.index), total_w - total_b, color="#0b0b0b", lw=1.8, label="all three")
    axes[0].axhline(0, color="#52514e", lw=0.8)
    axes[0].set_title("Value of the forecast: desk with skew minus the same desk without")
    axes[0].set_ylabel("cumulative, multiples of N0 (= $1M)")
    axes[0].legend()
    axes[1].plot(pd.to_datetime(total_b.index), total_b, color="#c3c2b7", lw=1.6, label="desk without the forecast")
    axes[1].plot(pd.to_datetime(total_w.index), total_w, color=plot.SERIES[0], lw=1.6, label="desk with the forecast")
    axes[1].axhline(0, color="#52514e", lw=0.8)
    axes[1].set_title("The desk's own net PnL, all three names (fills at vwap, inventory, hedges, unwinds)")
    axes[1].legend()
    fig.suptitle(f"Mock market-making desk: {100 * params['f']:.0f}% of taker flow, maker {params['fee_maker']:g} / taker {params['fee_taker']:g} bps, "
                 f"limit {params['L']:g} N0 (stretch <= {1 + params['stretch_max']:.1f}x), hedge band {params['T']:g}")
    fig.tight_layout()
    plot.save(fig, name)


def line_base(a, reg, cfg, base, t0):
    return {"run_id": None, "parent_run_id": a.run, "config": reg["config"], "split": a.split,
            "dates": {"start": RANGES[a.split]["test"][0], "end": RANGES[a.split]["test"][1]}, "followers": FOLLOWERS,
            "horizon_bars": cfg["target"]["horizon_bars"], "desk_version": 2, "desk_params": base, "demean_z": not a.no_demean,
            "placebo_shift_days": a.placebo_shift_days, "delay_bars": a.delay_bars, "verdict": "n/a", "status": "ok", "notes": f"{time.time() - t0:.0f}s"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", default="walk_forward", choices=list(RANGES))
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--params", default="{}")
    ap.add_argument("--change", default="")
    ap.add_argument("--tag", default="", help="figure and table name suffix")
    ap.add_argument("--placebo-shift-days", type=int, default=0, help="circular time-shift placebo of the forecast")
    ap.add_argument("--delay-bars", type=int, default=0, help="act on a forecast this many bars old")
    ap.add_argument("--no-demean", action="store_true", help="z without the trailing-mean removal")
    a = ap.parse_args()
    TAB.mkdir(parents=True, exist_ok=True)
    reg = [json.loads(l) for l in (ROOT / "experiments" / "registry.jsonl").read_text().splitlines() if l.strip() and a.run in l][0]
    cfg = load(reg["config"].split("/")[-1].replace(".yaml", ""))
    t0 = time.time()
    data, days = inputs(a.run, a.split, cfg, demean=not a.no_demean)
    print(f"inputs ready {time.time() - t0:.0f}s, {days} days")
    base = {**desk.DEFAULT, **json.loads(a.params)}
    if a.grid:
        rows = []
        grid = [(k, s_max, z_in, tilt) for k in (0.25, 0.5) for s_max in (0.6, 0.8) for z_in in (0.0, 1.5, 2.0) for tilt in (0.0, 0.3)]
        for k, s_max, z_in, tilt in grid:
            p = {**base, "k": k, "s_max": s_max, "z_in": z_in, "tilt": tilt}
            res, tot, _ = one(data, p)
            rows.append({"k": k, "s_max": s_max, "z_in": z_in, "tilt": tilt, **{f"{j[:3]}_delta": res[j]["delta_pnl_per_day"] for j in res}, **{kk: v for kk, v in tot.items() if not isinstance(v, list)}})
            print(f"k={k} s_max={s_max} z_in={z_in} tilt={tilt}: delta/day {tot['delta_pnl_per_day']:+.4f} ({tot['delta_bps_of_fills']:+.2f} bps of fills) ci [{tot['delta_ci95_per_day'][0]:+.4f}, {tot['delta_ci95_per_day'][1]:+.4f}] | alt leg {tot['delta_alt_leg_per_day']:+.4f} hedge leg {tot['delta_hedge_leg_per_day']:+.4f} spread {tot['delta_spread_per_day']:+.4f} costs {-(tot['delta_cost_hedge_per_day'] + tot['delta_cost_unwind_per_day']):+.4f} | {time.time() - t0:.0f}s")
        t = pd.DataFrame(rows)
        t.to_csv(TAB / f"desk_grid_{a.split}_v2.csv", index=False)
        best = t.sort_values("delta_pnl_per_day", ascending=False).iloc[0]
        print("\nbest on", a.split, ":", best[["k", "s_max", "z_in", "tilt", "delta_pnl_per_day", "delta_bps_of_fills"]].to_dict())
        line = line_base(a, reg, cfg, base, t0)
        line.update({"run_id": registry.new_id(f"desk2_grid_{a.split}"), "change": a.change or f"mock desk v2 parameter grid (k, s_max, z_in, tilt), {len(grid)} trials",
                     "metrics": {"grid": t.round(6).to_dict(orient="records"), "best": {kk: float(best[kk]) for kk in ["k", "s_max", "z_in", "tilt", "delta_pnl_per_day", "delta_bps_of_fills"]}},
                     "baselines": {"same_desk_no_forecast": {"net_per_day": float(best["base_net_per_day"])}}})
        registry.append(line)
        return
    res, tot, curves = one(data, base, a.placebo_shift_days, a.delay_bars)
    print(json.dumps({"total": tot, "by_follower": res}, indent=1, default=float))
    tag = f"desk2_{a.split}" + (f"_{a.tag}" if a.tag else "")
    if not a.placebo_shift_days and not a.delay_bars:
        figures(curves, tag, base)
    pd.DataFrame(res).T.to_csv(TAB / f"{tag}.csv")
    pd.Series({k: v for k, v in tot.items() if not isinstance(v, list)}).to_csv(TAB / f"{tag}_total.csv")
    line = line_base(a, reg, cfg, base, t0)
    line.update({"run_id": registry.new_id(f"desk2_{a.split}"), "change": a.change or "mock desk v2 with the chosen parameters",
                 "metrics": {"total": tot, "by_follower": res}, "baselines": {"same_desk_no_forecast": {"net_per_day": tot["base_net_per_day"]}}})
    registry.append(line)


if __name__ == "__main__":
    main()
