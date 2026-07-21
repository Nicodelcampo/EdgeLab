import numpy as np
import pandas as pd
import vectorbt as vbt
import warnings
import gc

warnings.filterwarnings('ignore')

data_path = 'C:/ProyectosQuant/EdgeLab/data/eurusd_ticks.parquet'

print(f"Leyendo {data_path}...")
df = pd.read_parquet(data_path)

print("Preprocesando datos...")
df['mid'] = (df['bid'] + df['ask']) / 2.0
df.set_index('timestamp', inplace=True)

print("Resampleando a M15...")
ohlcv = df['mid'].resample('15min').ohlc()
ohlcv = ohlcv.ffill().dropna()

# Liberar memoria del tick data (muy grande)
del df
gc.collect()

print(f"Datos M15 generados: {len(ohlcv)} velas.")
print(ohlcv.head())

# =========================================================================
# LÓGICAS DE ENTRADA Y SALIDA (Time of Day 08:00 a 16:00 UTC)
# =========================================================================

# 1. Filtro temporal y salidas forzadas a las 16:00
time_idx = ohlcv.between_time('08:00', '16:00', inclusive='left').index

# Salida incondicional a la vela de las 16:00
exits = pd.Series(False, index=ohlcv.index)
daily_last_idx = exits[exits.index.isin(time_idx)].groupby(exits[exits.index.isin(time_idx)].index.date).last().index
exits.loc[daily_last_idx] = True

# 2. Señales Base (Variantes)
# a) Monte Carlo (Random)
np.random.seed(42)
rand_long = pd.Series(np.random.choice([True, False], size=len(ohlcv), p=[0.05, 0.95]), index=ohlcv.index)
rand_short = pd.Series(np.random.choice([True, False], size=len(ohlcv), p=[0.05, 0.95]), index=ohlcv.index)

rand_long[~rand_long.index.isin(time_idx)] = False
rand_short[~rand_short.index.isin(time_idx)] = False
rand_long = rand_long & ~exits
rand_short = rand_short & ~exits

# b) ToD Simple (Bias Constante): Comprar a las 08:15 siempre
tod_long = pd.Series(False, index=ohlcv.index)
tod_long[ohlcv.index.time == pd.to_datetime('08:15').time()] = True
tod_short = pd.Series(False, index=ohlcv.index)

# c) Asian Range Breakout (Tendencial)
asian_range = ohlcv.between_time('00:00', '08:00')
asian_high = asian_range['high'].groupby(asian_range.index.date).max()
asian_low = asian_range['low'].groupby(asian_range.index.date).min()

asian_high_s = pd.Series(index=ohlcv.index, dtype=float)
asian_low_s = pd.Series(index=ohlcv.index, dtype=float)
for d in asian_high.index:
    asian_high_s[asian_high_s.index.date == d] = asian_high[d]
    asian_low_s[asian_low_s.index.date == d] = asian_low[d]

arb_long = pd.Series(False, index=ohlcv.index)
arb_short = pd.Series(False, index=ohlcv.index)

at_0815 = ohlcv.index.time == pd.to_datetime('08:15').time()
arb_long[at_0815 & (ohlcv['close'] > asian_high_s)] = True
arb_short[at_0815 & (ohlcv['close'] < asian_low_s)] = True

# d) Asian Range Reversion (Stop Hunts)
arr_long = pd.Series(False, index=ohlcv.index)
arr_short = pd.Series(False, index=ohlcv.index)
arr_long[at_0815 & (ohlcv['close'] < asian_low_s)] = True
arr_short[at_0815 & (ohlcv['close'] > asian_high_s)] = True


# =========================================================================
# SIMULACIÓN (Portfolio)
# =========================================================================
print("\nEjecutando Backtests...")

tp_stop = 0.0036
sl_stop = np.nan 
fees = 0.0001
freq = '15min'

def run_backtest(name, entries, short_entries):
    pf = vbt.Portfolio.from_signals(
        close=ohlcv['close'],
        entries=entries,
        short_entries=short_entries,
        exits=exits,
        short_exits=exits,
        tp_stop=tp_stop,
        sl_stop=sl_stop,
        price=ohlcv['open'].shift(-1), 
        freq=freq,
        fees=fees
    )
    print(f"\n--- Resultados: {name} ---")
    try:
        print(f"Total Trades: {pf.trades.count()}")
        if pf.trades.count() > 0:
            print(f"Win Rate: {pf.trades.win_rate()*100:.2f}%")
            print(f"Total Return: {pf.total_return()*100:.2f}%")
            print(f"Sharpe Ratio: {pf.sharpe_ratio():.2f}")
            print(f"Max Drawdown: {pf.max_drawdown()*100:.2f}%")
        else:
            print("No trades generated.")
    except Exception as e:
        print("Error calculando metricas:", e)

run_backtest("Baseline Monte Carlo", rand_long, rand_short)
run_backtest("ToD Simple (Solo Comprar 08:15)", tod_long, tod_short)
run_backtest("Asian Range Breakout", arb_long, arb_short)
run_backtest("Asian Range Reversion", arr_long, arr_short)
