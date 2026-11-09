/ raw 1-min archive -> table contract. column names are the course's, in file order
.schema.syms:`BTCUSDT`DOGEUSDT`ETHUSDT`SOLUSDT`XRPUSDT

/ table -> raw folder and file suffix
.schema.ds:`l1bar`tradebar`bookbar!`level1_1min`trade_1min`book_1min
.schema.suf:`l1bar`tradebar`bookbar!`level1`trade`book

/ one parse char per raw column, for 0:. ts_end is "F": the text is 1705276860000.0 and "J" gives null
.schema.types:`l1bar`tradebar`bookbar!("FIIIJF",22#"F";"FIII",(6#"J"),13#"F";"FJIII",58#"F")

/ expected header per table. the loader refuses a file whose header differs
.schema.cols:()!()
.schema.cols[`l1bar]:`ts_end`bin_id`carryover`ramp_up`tick_count`l3_updates`open_mid`first_mid`close_mid`min_mid`max_mid`close_bid`close_ask`close_bid_size`close_ask_size`max_bid`min_ask`ask_up_ret`ask_down_ret`bid_up_ret`bid_down_ret`median_spread`mean_spread`min_spread`max_spread`mean_bid_size`mean_ask_size`tick_volatility
.schema.cols[`tradebar]:`ts_end`bin_id`carryover`ramp_up`trade_count`buy_trade_count`sell_trade_count`taker_trade_count`taker_buy_trade_count`taker_sell_trade_count`open_price`first_price`close_price`min_price`max_price`median_price`volume`buy_volume`sell_volume`vwap`buy_vwap`sell_vwap`trade_volatility
.schema.cols[`bookbar]:`ts_end`ts_book`bin_id`carryover`ramp_up`bid_price`ask_price`bid_size`ask_size`bid_1bps_fill_size`ask_1bps_fill_size`bid_3bps_fill_size`ask_3bps_fill_size`bid_10bps_fill_size`ask_10bps_fill_size`bid_30bps_fill_size`ask_30bps_fill_size`bid_100bps_fill_size`ask_100bps_fill_size`bid_1_fill_size`bid_1_fill_vwap`ask_1_fill_size`ask_1_fill_vwap`bid_10_fill_size`bid_10_fill_vwap`ask_10_fill_size`ask_10_fill_vwap`bid_100_fill_size`bid_100_fill_vwap`ask_100_fill_size`ask_100_fill_vwap`bid_1000_fill_size`bid_1000_fill_vwap`ask_1000_fill_size`ask_1000_fill_vwap`bid_10000_fill_size`bid_10000_fill_vwap`ask_10000_fill_size`ask_10000_fill_vwap`bid_1K_fill_dsize`bid_1K_fill_dvwap`ask_1K_fill_dsize`ask_1K_fill_dvwap`bid_10K_fill_dsize`bid_10K_fill_dvwap`ask_10K_fill_dsize`ask_10K_fill_dvwap`bid_100K_fill_dsize`bid_100K_fill_dvwap`ask_100K_fill_dsize`ask_100K_fill_dvwap`bid_1000K_fill_dsize`bid_1000K_fill_dvwap`ask_1000K_fill_dsize`ask_1000K_fill_dvwap`bid_10000K_fill_dsize`bid_10000K_fill_dvwap`ask_10000K_fill_dsize`ask_10000K_fill_dvwap`bid_100000K_fill_dsize`bid_100000K_fill_dvwap`ask_100000K_fill_dsize`ask_100000K_fill_dvwap
