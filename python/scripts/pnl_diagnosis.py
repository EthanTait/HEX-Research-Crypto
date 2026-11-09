# where does the pnl go? decomposition of a logged run's backtest, and what the forecast is worth
# per trade at longer holds, at the signal extremes, and with the btc hedge netted across followers.
# usage: python python/scripts/pnl_diagnosis.py --run <run_id>
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset.config import BARS_PER_DAY, FOLLOWERS, ROOT, load  # noqa: E402
from notset.eval import pnl  # noqa: E402
from notset.features import build as fb  # noqa: E402

TAB = ROOT / "output" / "tables"


def fwd_move_bps(e, h):
    # realized hedged move over t+1..t+h in bps; NaN if any bar in the window is masked
    return 1e4 * e[::-1].rolling(h, min_periods=h).sum()[::-1].shift(-1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    r = [json.loads(l) for l in (ROOT / "experiments" / "registry.jsonl").read_text().splitlines() if l.strip() and a.run in l][0]
    cfg = load(r["config"].split("/")[-1].replace(".yaml", ""))
    h, fee, band = cfg["target"]["horizon_bars"], cfg["costs"]["taker_bps"], cfg["costs"].get("trade_band", 0.0)
    d = fb.dataset("features", "2023-11-01", "2024-12-31", beta_days=cfg["beta"]["window_days"], hedge=cfg["hedge"])
    fc = pd.read_pickle(ROOT / "experiments" / "runs" / a.run / "forecast.pkl")
    ts = fc.index.get_level_values("ts_end")

    # 1. cost decomposition of the run's own backtest, per follower, bps per day
    rows, zs, ns, ds = [], {}, {}, {}
    for j in FOLLOWERS:
        dj = d.xs(j, level="sym").loc[ts.min():ts.max() + pd.Timedelta(minutes=h)]
        fj = fc.xs(j, level="sym").reindex(dj.index)
        n = pnl.positions(fj, h, band=band)
        dn = n.diff().abs().fillna(0)
        days = len(np.unique((dj.index - pd.Timedelta(minutes=1)).date))
        gross = 1e4 * (n * dj["e_book"].shift(-1).fillna(0)).sum() / days
        rows.append({"follower": j, "gross_bps_day": gross,
                     "fee_alt": 1e4 * (dn * fee * 1e-4).sum() / days,
                     "spread_alt": 1e4 * (dn * dj["hspread"].ffill()).sum() / days,
                     "fee_btc": 1e4 * (dn * dj["beta"].abs().ffill() * fee * 1e-4).sum() / days,
                     "spread_btc": 1e4 * (dn * dj["beta"].abs().ffill() * dj["hspread_btc"].ffill()).sum() / days,
                     "turnover_day": dn.sum() / days, "half_spread_bps": 1e4 * dj["hspread"].mean(),
                     "btc_half_spread_bps": 1e4 * dj["hspread_btc"].mean(), "beta_mean": dj["beta"].mean()})
        sd = fj.rolling(7 * BARS_PER_DAY, min_periods=BARS_PER_DAY).std()
        zs[j], ns[j], ds[j] = fj / sd, n, dj
    t1 = pd.DataFrame(rows).set_index("follower")
    t1["cost_total"] = t1[["fee_alt", "spread_alt", "fee_btc", "spread_btc"]].sum(axis=1)
    t1["gross_per_unit_traded_bps"] = t1["gross_bps_day"] / t1["turnover_day"]
    t1["cost_per_unit_traded_bps"] = t1["cost_total"] / t1["turnover_day"]
    print("== 1. where the money goes (bps of follower notional per day, 2024)\n", t1.round(2).to_string())
    t1.to_csv(TAB / "diag_cost_decomposition.csv")

    # 2. gross edge per unit, by signal extremity and holding horizon (sign-adjusted realized hedged move)
    rows = []
    for j in FOLLOWERS:
        z, dj = zs[j], ds[j]
        for hh in (1, 5, 15, 30, 60, 120):
            mv = fwd_move_bps(dj["e"], hh)
            for lo in (0, 1, 1.5, 2, 3):
                m = (z.abs() >= lo) & mv.notna()
                sel = np.sign(z[m]) * mv[m]
                rows.append({"follower": j, "h": hh, "z_min": lo, "mean_bps": sel.mean(), "median_bps": sel.median(),
                             "hit_rate": (sel > 0).mean(), "bars_per_day": m.sum() / 366, "t_stat": sel.mean() / sel.std() * np.sqrt(len(sel)) if len(sel) > 1 else np.nan})
    t2 = pd.DataFrame(rows)
    piv = t2.pivot_table(index=["follower", "z_min"], columns="h", values="mean_bps")
    print("\n== 2. sign-adjusted realized hedged move, bps, by |z| threshold (rows) and horizon (cols)\n", piv.round(2).to_string())
    print("\n   bars per day above the threshold:\n", t2[t2.h == 5].pivot(index="follower", columns="z_min", values="bars_per_day").round(0).to_string())
    t2.to_csv(TAB / "diag_edge_by_horizon.csv", index=False)

    # 3. signal persistence: autocorrelation of z, and run lengths of |z| >= 2 with the same sign
    rows = []
    for j in FOLLOWERS:
        z = zs[j].dropna()
        ac = {f"ac{k}": z.autocorr(k) for k in (1, 5, 15, 30, 60)}
        s = np.sign(z.where(z.abs() >= 2, 0))
        runs = (s != s.shift()).cumsum()
        rl = s[s != 0].groupby(runs[s != 0]).size()
        rows.append({"follower": j, **ac, "runs_per_day_z2": len(rl) / 366, "mean_run_len_bars": rl.mean(), "median_run_len_bars": rl.median()})
    t3 = pd.DataFrame(rows).set_index("follower")
    print("\n== 3. persistence of the forecast\n", t3.round(3).to_string())
    t3.to_csv(TAB / "diag_persistence.csv")

    # 4. netting the btc hedge across the three followers
    N = pd.DataFrame({j: ns[j] * ds[j]["beta"].ffill() for j in FOLLOWERS}).dropna()
    gross_exp, net_exp = N.abs().sum(axis=1), N.sum(axis=1).abs()
    gross_turn, net_turn = N.diff().abs().sum(axis=1), N.sum(axis=1).diff().abs()
    t4 = pd.Series({"mean_gross_btc_exposure": gross_exp.mean(), "mean_net_btc_exposure": net_exp.mean(),
                    "btc_turnover_gross_per_day": gross_turn.sum() / 366, "btc_turnover_net_per_day": net_turn.sum() / 366,
                    "pos_corr_sol_xrp": ns["SOLUSDT"].corr(ns["XRPUSDT"]), "pos_corr_sol_doge": ns["SOLUSDT"].corr(ns["DOGEUSDT"]), "pos_corr_xrp_doge": ns["XRPUSDT"].corr(ns["DOGEUSDT"])})
    print("\n== 4. one btc hedge for the book instead of three\n", t4.round(3).to_string())
    t4.to_csv(TAB / "diag_netting.csv")

    # 5. a hysteresis rule: enter at |z| >= z_in, exit when |z| < z_out or after max_hold bars; realized move per trade
    rows = []
    for j in FOLLOWERS:
        z, dj = zs[j].fillna(0).values, ds[j]
        eb = dj["e_book"].fillna(0).values
        for z_in, z_out, max_hold in [(2, 0.5, 30), (2, 0.5, 60), (2.5, 0.5, 60), (3, 1, 60), (2, 0, 120)]:
            pos, since, trades, held, pnls = 0, 0, 0, [], []
            cur = 0.0
            for i in range(len(z) - 1):
                if pos == 0:
                    if abs(z[i]) >= z_in:
                        pos, since, cur = int(np.sign(z[i])), 0, 0.0
                else:
                    cur += pos * eb[i + 1] * 1e4  # pnl over the bar after the decision
                    since += 1
                    if abs(z[i]) < z_out or np.sign(z[i]) == -pos or since >= max_hold:
                        trades += 1
                        held.append(since)
                        pnls.append(cur)
                        pos = 0
            pnls = np.array(pnls)
            rows.append({"follower": j, "z_in": z_in, "z_out": z_out, "max_hold": max_hold, "trades_per_day": trades / 366,
                         "mean_hold_bars": np.mean(held) if held else np.nan, "gross_bps_per_trade": pnls.mean() if len(pnls) else np.nan,
                         "hit_rate": (pnls > 0).mean() if len(pnls) else np.nan, "gross_bps_per_day": pnls.sum() / 366})
    t5 = pd.DataFrame(rows)
    print("\n== 5. hysteresis trades (enter |z|>=z_in, exit |z|<z_out or max_hold), gross of costs\n", t5.round(2).to_string())
    t5.to_csv(TAB / "diag_hysteresis.csv", index=False)
    print("\nround-trip cost per trade, bps: taker both legs = 2*(5+hs_alt) + 2*beta*(5+hs_btc); maker alt leg = 2*(2-hs_alt) + 2*beta*(5+hs_btc)")
    for j in FOLLOWERS:
        hs, hb, b = t1.loc[j, "half_spread_bps"], t1.loc[j, "btc_half_spread_bps"], abs(t1.loc[j, "beta_mean"])
        print(f"  {j}: taker {2 * (5 + hs) + 2 * b * (5 + hb):.1f}   maker-alt {2 * (2 - hs) + 2 * b * (5 + hb):.1f}   maker-alt + netted btc (1/3 of btc cost) {2 * (2 - hs) + 2 * b * (5 + hb) / 3:.1f}")


if __name__ == "__main__":
    TAB.mkdir(parents=True, exist_ok=True)
    main()
