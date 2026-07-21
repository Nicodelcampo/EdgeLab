import numpy as np
import pandas as pd
import vectorbt as vbt
import warnings
import gc
from scipy import stats as sp_stats

warnings.filterwarnings('ignore')

print("=" * 80)
print("DEEP DIVE: ES 10:00 AM NY WINDOW")
print("=" * 80)

data_path = 'C:/Users/nicoc/OneDrive/Documentos/DataMining/data/es_continuous_m1.parquet'
df = pd.read_parquet(data_path)
df.index = df.index.tz_localize('UTC')

ohlcv = df[['open','high','low','close']].resample('15min').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
}).ffill().dropna()

vol_m15 = df['volume'].resample('15min').sum()
ohlcv['volume'] = vol_m15.reindex(ohlcv.index).fillna(0)
del df; gc.collect()

ohlcv_ny = ohlcv.index.tz_convert('America/New_York')
is_pre_rth = ohlcv_ny.time < pd.to_datetime('09:30').time()
overnight_candles = ohlcv[is_pre_rth]

ny_dates = pd.Series(ohlcv_ny.date, index=ohlcv.index)
on_dates = pd.Series(ohlcv_ny[is_pre_rth].date, index=overnight_candles.index)

overnight_high = overnight_candles['high'].groupby(on_dates).max()
overnight_low  = overnight_candles['low'].groupby(on_dates).min()

on_high_s = pd.Series(np.nan, index=ohlcv.index, dtype=float)
on_low_s  = pd.Series(np.nan, index=ohlcv.index, dtype=float)
for d in overnight_high.index:
    mask = ny_dates == d
    on_high_s[mask] = overnight_high[d]
    on_low_s[mask]  = overnight_low[d]

sma_200 = ohlcv['close'].rolling(200).mean()

# News filter
daily_max_range = (ohlcv['high'] - ohlcv['low']).groupby(ny_dates).max()
threshold = daily_max_range.quantile(0.85)
news_days = set(daily_max_range[daily_max_range > threshold].index)
is_normal = ~ny_dates.isin(news_days)

# ONLY 10:00 AM WINDOW
w = '10:00'
at_time = ohlcv_ny.time == pd.to_datetime(w).time()

cond_long  = at_time & (ohlcv['close'].values > on_high_s.values) & (ohlcv['close'].values > sma_200.values)
cond_short = at_time & (ohlcv['close'].values < on_low_s.values)  & (ohlcv['close'].values < sma_200.values)

longs_f  = pd.Series(cond_long & is_normal.values, index=ohlcv.index)
shorts_f = pd.Series(cond_short & is_normal.values, index=ohlcv.index)

at_exit = ohlcv_ny.time == pd.to_datetime('15:45').time()
exits = pd.Series(at_exit, index=ohlcv.index)
exec_price = ohlcv['open'].shift(-1)

print(f"Total signals at {w} (filtered): {longs_f.sum()} longs, {shorts_f.sum()} shorts")

# PARAMETER GRID SEARCH
print("\n--- PARAMETER GRID SEARCH ---")
tp_grid = np.arange(2, 13, 1)  # 2 to 12 points
sl_grid = np.arange(10, 51, 5) # 10 to 50 points
FEES_PTS = 0.50

results = []
for tp in tp_grid:
    for sl in sl_grid:
        pf = vbt.Portfolio.from_signals(
            close=ohlcv['close'], entries=longs_f, short_entries=shorts_f,
            exits=exits, short_exits=exits,
            tp_stop=tp / exec_price, sl_stop=sl / exec_price,
            price=exec_price, freq='15min', fees=FEES_PTS / exec_price, init_cash=50000,
        )
        if pf.trades.count() > 0:
            results.append({
                'TP': tp, 'SL': sl, 'Trades': pf.trades.count(),
                'WinRate': pf.trades.win_rate()*100, 'Return': pf.total_return()*100,
                'Sharpe': pf.sharpe_ratio(), 'PF': pf.trades.profit_factor()
            })

df_res = pd.DataFrame(results)
top_5 = df_res.sort_values('Sharpe', ascending=False).head(5)
print("\nTop 5 Configurations (by Sharpe):")
print(top_5.to_string(index=False))

# WALK-FORWARD FOR BEST PARAMS (TP=9, SL=40)
print("\n--- WALK-FORWARD FOR BEST NT8 PARAMS (TP=9, SL=40) ---")
total_bars = len(ohlcv)
third = total_bars // 3
periods = [
    ("P1 TRAIN", ohlcv.index[0], ohlcv.index[third]),
    ("P2 VALID", ohlcv.index[third], ohlcv.index[2*third]),
    ("P3 TEST ", ohlcv.index[2*third], ohlcv.index[-1]),
]

for name, start, end in periods:
    mask = (ohlcv.index >= start) & (ohlcv.index < end)
    pf = vbt.Portfolio.from_signals(
        close=ohlcv['close'][mask], entries=longs_f[mask], short_entries=shorts_f[mask],
        exits=exits[mask], short_exits=exits[mask],
        tp_stop=9 / exec_price[mask], sl_stop=40 / exec_price[mask],
        price=exec_price[mask], freq='15min', fees=FEES_PTS / exec_price[mask], init_cash=50000,
    )
    tc = pf.trades.count()
    if tc > 0:
        print(f"  {name} ({start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}): Trades={tc}, WR={pf.trades.win_rate()*100:.1f}%, Ret={pf.total_return()*100:+.2f}%, Sharpe={pf.sharpe_ratio():.2f}")
    else:
        print(f"  {name}: 0 trades")
