# EVALUATION.md 5b: hedged position proportional to the forecast, held h bars, costs on every leg,
# three stages: mid-to-mid -> fees + half spread -> one-bar delay. long and short legs reported apart.
# a missing forecast means no new position (flat), and open positions are booked through stale
# bars on the unmasked e_book return, so nothing enters or exits for free around an outage
import numpy as np
import pandas as pd

from ..config import BARS_PER_DAY


def positions(forecast, h, scale_days=7, clip=3.0, band=0.0):
    # unit-notional position from the forecast: scaled by its own trailing std (past forecasts only),
    # zero inside the no-trade band (in sd units), clipped, then averaged over the h overlapping
    # holding periods -> net position N_t
    sd = forecast.rolling(scale_days * BARS_PER_DAY, min_periods=BARS_PER_DAY).std()
    z = forecast / sd
    pos = (z.where(z.abs() >= band, 0.0).clip(-clip, clip) / clip).fillna(0.0)
    return pos.rolling(h, min_periods=1).mean()


def cost_per_unit(dj, fee_bps=5.0):
    # round-trip-free cost of changing the position by one unit of follower notional:
    # follower leg, btc leg (|beta|), and the index legs (|beta2| * sum|w|) when the hedge has them
    fee = fee_bps * 1e-4
    c = (fee + dj["hspread"]) + dj["beta"].abs() * (fee + dj["hspread_btc"])
    if "beta2" in dj:
        c = c + dj["beta2"].abs() * (fee * dj["w_idx"] + dj["hspread_idx"])
    return c.ffill()


def backtest(forecast, dj, h, fee_bps=5.0, band=0.0):
    # forecast and dj (one follower's rows) share an index; dj has e_book and the spread columns
    n = positions(forecast.reindex(dj.index), h, band=band)
    e_next = dj["e_book"].shift(-1).fillna(0.0)  # the hedged move over the bar after the decision
    cost = cost_per_unit(dj, fee_bps).fillna(0.0)
    out = pd.DataFrame(index=dj.index)
    out["mid"] = n * e_next
    out["fees_spread"] = out["mid"] - n.diff().abs().fillna(0.0) * cost
    n1 = n.shift(1).fillna(0.0)  # decided at t, filled one bar later
    out["delay_1bar"] = n1 * e_next - n1.diff().abs().fillna(0.0) * cost
    out["long_leg"] = n.clip(lower=0) * e_next
    out["short_leg"] = n.clip(upper=0) * e_next
    out["position"] = n
    assert out[["mid", "fees_spread", "delay_1bar"]].notna().all().all()
    return out


def summarize(bt, dates):
    # per stage: cumulative pnl (bps of follower notional), annualized sharpe on daily pnl, turnover
    res = {"pnl_net_bps": {}, "sharpe": {}}
    daily = bt.groupby(np.asarray(dates)).sum()
    for s in ["mid", "fees_spread", "delay_1bar"]:
        res["pnl_net_bps"][s] = float(1e4 * bt[s].sum())
        mu, sd = daily[s].mean(), daily[s].std()
        res["sharpe"][s] = float(mu / sd * np.sqrt(365)) if sd > 0 else 0.0
    res["legs_bps"] = {"long": float(1e4 * bt["long_leg"].sum()), "short": float(1e4 * bt["short_leg"].sum())}
    res["turnover_per_day"] = float(bt["position"].diff().abs().sum() / max(len(daily), 1))
    res["n_days"] = int(len(daily))
    return res, daily
