# Signal Research Plan - Ethan Tait (as submitted, Oct 2026)

Kept as submitted. Where the project has moved on since, see `docs/DECISIONS.md` (2026-11-05): the TWAP execution metric and simulated parent orders are retired, and the target is now the BTC-hedged spread.

## Idea
- lead-lag between crypto perps: does one instrument move first and others follow
- not just "BTC leads": who leads might change over time / by coin
- want to split moves into market-wide vs coin-specific (idiosyncratic) and see which part has the lag

## Use case / who would use it
- main idea: execution desk working a big order in an alt perp (e.g. buy a large SOL position over an hour)
- signal would help decide how much to trade each minute vs a fixed schedule (TWAP)
  - trade more now if price is expected to move against us, less if it's expected to come to us
- signal doesn't need to make money on its own, just improve timing
- aware that execution desks normally work off tick data; we'd focus on the scheduling side (how much per minute), not order placement
- others who might care: market makers (skewing quotes; would need tick data), relative-value funds (follower vs leader spread)

## Final metric (thinking)
- execution improvement: slippage saved vs TWAP in bps, ideally looked at over a time period or per amount of capital (capital if the signal does not fire often; event based)
- backup / secondary: information content, i.e. OOS correlation of the signal with future returns vs a simple BTC-only version

## 1. Data
- would use tick data if available (trades + best bid/offer); if that's too hard to get, 1-min data is fine
- starting point: Binance USD-M perps we already have, BTC, ETH, SOL, XRP, DOGE, 1-min level1 / trade / book, 2023 to 2025
- would like (if possible, same format):
  - same coins' perps on Bybit / OKX / Hyperliquid, to see which exchange moves first
  - Binance spot for the same coins, to check perp vs spot
  - maybe funding rates, since the spot-perp gap jumps around funding times
- sampling: lead-lags are probably sub-minute, which is why tick would be ideal; 1-min should still work for minute-level effects and execution timing

## 2. What we're predicting
- follower's future mid return over the next ~1 / 5 / 15 min; mid to start, then work with spreads
- probably scaled by recent volatility so wild days don't dominate
- also the follower's move net of the leader (residual) as a check that it's more than just market beta
- false positives to watch for:
  - a leader's own bounce-back looking like a lead
  - stale / missing bars creating fake lags
  - timestamp differences across exchanges
  - funding-time jumps in the spot-perp gap
  - a few crash days driving the whole result
  - testing too many pairs / lags and finding something by chance
- complications: most co-movement probably happens within the same minute; relationships may change over time

## 3. Features (initial list, not final)
- leader past returns (BTC, ETH), EMA-smoothed like Lecture 4
- follower's move net of the leader (rolling beta), and how far it has "caught up"
- own past returns of leader and follower (short-term mean reversion as a control)
- trade imbalance and book imbalance (Lecture 4 versions), range -1 to 1
- if we get the data: price gap between exchanges, spot-perp basis
- some kind of rolling "who's leading" score per coin
- volatility / correlation regime as a filter
- checks: distributions (skew, tails), stability over time, correlation between features; probably ridge or PCA if they overlap a lot

## 4. Optimization / backtest
- signal as a weighted combo of transformed features (ridge regression, like the lecture)
- parameters to tune: EMA half-lives, beta window, ridge strength, plus execution settings (how aggressive the tilt is)
- sliding window: fit on ~2 months, test on the next week, roll forward (Lecture 5 approach)
- keep a final chunk of data untouched as a holdout
- overfit control: few features, check parameter stability, per-day results, rerun without the most volatile days, compare against a no-signal baseline

## 5. Deployment
- real-time feed of trades / quotes for leaders and followers (exchange websockets)
- rough pipeline idea: kdb+/q for data + signal, Java for execution logic, Python for research
- strategy idea: simulate large parent orders (random start times, buy/sell, different sizes and lengths) and compare TWAP vs signal-adjusted schedule
  - could cost each slice using the book data's fill prices at different notional sizes
  - compare against arrival price and TWAP (benchmark depends on the client in practice)
- no backtest yet; that's the project
- final slide: slippage saved vs TWAP, plus signal information content

## Open questions
- is tick data realistic to get, or do we stay at 1-min?
- is extra exchange / spot data available?
- what order sizes / horizons are realistic for the simulation?
- is the lead big enough at 1-min to matter?
