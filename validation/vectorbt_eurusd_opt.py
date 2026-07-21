import numpy as np
import pandas as pd
import vectorbt as vbt
import warnings
import gc
import itertools

warnings.filterwarnings('ignore')

data_path = 'C:/ProyectosQuant/EdgeLab/data/eurusd_ticks.parquet'
print(f"Leyendo {data_path}...")
df = pd.read_parquet(data_path)
df['mid'] = (df['bid'] + df['ask']) / 2.0
df.set_index('timestamp', inplace=True)

print("Resampleando a M15...")
ohlcv = df['mid'].resample('15min').ohlc()
ohlcv = ohlcv.ffill().dropna()

del df
gc.collect()

asian_range = ohlcv.between_time('00:00', '08:00')
asian_high = asian_range['high'].groupby(asian_range.index.date).max()
asian_low = asian_range['low'].groupby(asian_range.index.date).min()

asian_high_s = pd.Series(index=ohlcv.index, dtype=float)
asian_low_s = pd.Series(index=ohlcv.index, dtype=float)
for d in asian_high.index:
    asian_high_s[asian_high_s.index.date == d] = asian_high[d]
    asian_low_s[asian_low_s.index.date == d] = asian_low[d]

time_idx = ohlcv.between_time('08:00', '16:00', inclusive='left').index
exits = pd.Series(False, index=ohlcv.index)
daily_last_idx = exits[exits.index.isin(time_idx)].groupby(exits[exits.index.isin(time_idx)].index.date).last().index
exits.loc[daily_last_idx] = True

entry_times = ['08:00', '08:15', '08:30', '09:00']
tp_stops = [0.0020, 0.0040, 0.0060, 0.0080]
sl_stops = [np.nan, 0.0030, 0.0050]
sl_trails = [np.nan, 0.0020, 0.0040]

combinations = list(itertools.product(entry_times, tp_stops, sl_stops, sl_trails))
print(f"Optimizando {len(combinations)} permutaciones...")

all_stats = []

for idx, (et, tp, sl, trail) in enumerate(combinations):
    if idx % 20 == 0:
        print(f"Progreso: {idx}/{len(combinations)}")
        
    arr_long = pd.Series(False, index=ohlcv.index)
    arr_short = pd.Series(False, index=ohlcv.index)
    at_time = ohlcv.index.time == pd.to_datetime(et).time()
    
    arr_long[at_time & (ohlcv['close'] < asian_low_s)] = True
    arr_short[at_time & (ohlcv['close'] > asian_high_s)] = True
    
    pf = vbt.Portfolio.from_signals(
        close=ohlcv['close'],
        entries=arr_long,
        short_entries=arr_short,
        exits=exits,
        short_exits=exits,
        tp_stop=tp,
        sl_stop=sl,
        sl_trail=trail,
        price=ohlcv['open'].shift(-1),
        freq='15min',
        fees=0.0001
    )
    
    if pf.trades.count() > 0:
        row = {
            'Entry_Time': et,
            'TP': tp,
            'SL': sl,
            'Trail': trail,
            'Total Trades': pf.trades.count(),
            'Win Rate [%]': pf.trades.win_rate()*100,
            'Total Return [%]': pf.total_return()*100,
            'Sharpe Ratio': pf.sharpe_ratio(),
            'Max Drawdown [%]': pf.max_drawdown()*100
        }
        all_stats.append(row)

final_stats = pd.DataFrame(all_stats)
sorted_stats = final_stats.sort_values(by='Sharpe Ratio', ascending=False)

print("\n=== TOP 10 MEJORES COMBINACIONES (Ordenado por Sharpe) ===")
print(sorted_stats[['Entry_Time', 'TP', 'SL', 'Trail', 'Total Trades', 'Win Rate [%]', 'Total Return [%]', 'Sharpe Ratio']].head(10))

out_path = 'C:/ProyectosQuant/EdgeLab/validation/opt_results.csv'
sorted_stats.to_csv(out_path, index=False)
print(f"\nResultados guardados en {out_path}")
