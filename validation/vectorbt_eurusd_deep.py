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

print(f"Rango de datos: {ohlcv.index[0]} a {ohlcv.index[-1]}")
print(f"Total velas M15: {len(ohlcv)}")

# =========================================================================
# FEATURES COMUNES
# =========================================================================

# Asian Range
asian_range = ohlcv.between_time('00:00', '08:00')
asian_high = asian_range['high'].groupby(asian_range.index.date).max()
asian_low = asian_range['low'].groupby(asian_range.index.date).min()
asian_mid_daily = (asian_high + asian_low) / 2.0

asian_high_s = pd.Series(index=ohlcv.index, dtype=float)
asian_low_s = pd.Series(index=ohlcv.index, dtype=float)
asian_mid_s = pd.Series(index=ohlcv.index, dtype=float)
for d in asian_high.index:
    mask = ohlcv.index.date == d
    asian_high_s[mask] = asian_high[d]
    asian_low_s[mask] = asian_low[d]
    asian_mid_s[mask] = asian_mid_daily[d]

# SMAs
sma_50 = ohlcv['close'].rolling(50).mean()
sma_100 = ohlcv['close'].rolling(100).mean()
sma_200 = ohlcv['close'].rolling(200).mean()

# Exits (16:00)
time_idx = ohlcv.between_time('08:00', '16:00', inclusive='left').index
exits = pd.Series(False, index=ohlcv.index)
daily_last_idx = exits[exits.index.isin(time_idx)].groupby(
    exits[exits.index.isin(time_idx)].index.date
).last().index
exits.loc[daily_last_idx] = True

# =========================================================================
# ESTRATEGIAS DE ALTA FRECUENCIA
# =========================================================================
strategies = {}

# Ventana de operación: múltiples entradas posibles durante la sesión
session_times = ['08:15', '08:30', '08:45', '09:00', '09:15', '09:30',
                 '10:00', '10:30', '11:00', '12:00', '13:00', '14:00']

for sma_name, sma_s in [('SMA50', sma_50), ('SMA100', sma_100), ('SMA200', sma_200)]:

    # --- A) SMA Momentum: comprar/vender en cada vela de sesión si SMA confirma ---
    # Entrada en CUALQUIER vela de 08:15 a 14:00 si close > SMA (long) o < SMA (short)
    # Esto genera MUCHOS trades (1 por día en cada vela elegible)
    for et in session_times:
        at_time = ohlcv.index.time == pd.to_datetime(et).time()
        
        # Variante 1: SMA puro (solo dirección macro)
        key = f"SMAM_{sma_name}_{et}"
        l = pd.Series(False, index=ohlcv.index)
        s = pd.Series(False, index=ohlcv.index)
        l[at_time & (ohlcv['close'] > sma_s)] = True
        s[at_time & (ohlcv['close'] < sma_s)] = True
        strategies[key] = (l, s)
        
        # Variante 2: SMA + precio encima del midpoint asiático (filtro leve)
        key = f"SMAM_AMID_{sma_name}_{et}"
        l = pd.Series(False, index=ohlcv.index)
        s = pd.Series(False, index=ohlcv.index)
        l[at_time & (ohlcv['close'] > sma_s) & (ohlcv['close'] > asian_mid_s)] = True
        s[at_time & (ohlcv['close'] < sma_s) & (ohlcv['close'] < asian_mid_s)] = True
        strategies[key] = (l, s)
        
        # Variante 3: Asian Range Breakout + SMA (el edge probado, pero a múltiples horas)
        key = f"ARB_{sma_name}_{et}"
        l = pd.Series(False, index=ohlcv.index)
        s = pd.Series(False, index=ohlcv.index)
        l[at_time & (ohlcv['close'] > asian_high_s) & (ohlcv['close'] > sma_s)] = True
        s[at_time & (ohlcv['close'] < asian_low_s) & (ohlcv['close'] < sma_s)] = True
        strategies[key] = (l, s)

# =========================================================================
# WALK-FORWARD: SPLIT EN 2 MITADES
# =========================================================================
mid_date = ohlcv.index[len(ohlcv)//2]
print(f"\nWalk-Forward split: Train hasta {mid_date.date()}, Test desde {mid_date.date()}")

ohlcv_train = ohlcv[:mid_date]
ohlcv_test = ohlcv[mid_date:]

# =========================================================================
# GRID SEARCH (sobre datos completos + walk-forward)
# =========================================================================
tp_stops = [0.0020, 0.0030, 0.0050]
sl_stops = [0.0030, 0.0050]

print(f"\nTotal estrategias: {len(strategies)}")
print(f"TP x SL combos: {len(tp_stops)} x {len(sl_stops)} = {len(tp_stops)*len(sl_stops)}")
total = len(strategies) * len(tp_stops) * len(sl_stops)
print(f"Total permutaciones: {total}")

all_stats = []
count = 0

for strat_name, (entries, short_entries) in strategies.items():
    if count % 50 == 0:
        print(f"Progreso: {count}/{total} perms procesadas...")
    
    for tp, sl in itertools.product(tp_stops, sl_stops):
        count += 1
        
        # Full period
        pf = vbt.Portfolio.from_signals(
            close=ohlcv['close'], entries=entries, short_entries=short_entries,
            exits=exits, short_exits=exits, tp_stop=tp, sl_stop=sl,
            price=ohlcv['open'].shift(-1), freq='15min', fees=0.0001
        )
        
        tc = pf.trades.count()
        if tc < 15:
            continue
        
        # Train period
        pf_train = vbt.Portfolio.from_signals(
            close=ohlcv_train['close'],
            entries=entries[:mid_date], short_entries=short_entries[:mid_date],
            exits=exits[:mid_date], short_exits=exits[:mid_date],
            tp_stop=tp, sl_stop=sl,
            price=ohlcv_train['open'].shift(-1), freq='15min', fees=0.0001
        )
        
        # Test period
        pf_test = vbt.Portfolio.from_signals(
            close=ohlcv_test['close'],
            entries=entries[mid_date:], short_entries=short_entries[mid_date:],
            exits=exits[mid_date:], short_exits=exits[mid_date:],
            tp_stop=tp, sl_stop=sl,
            price=ohlcv_test['open'].shift(-1), freq='15min', fees=0.0001
        )
        
        row = {
            'Strategy': strat_name,
            'TP': tp, 'SL': sl,
            # Full
            'Trades': tc,
            'WinRate': pf.trades.win_rate()*100,
            'Return': pf.total_return()*100,
            'Sharpe': pf.sharpe_ratio(),
            'MaxDD': pf.max_drawdown()*100,
            # Train
            'Train_Trades': pf_train.trades.count(),
            'Train_Return': pf_train.total_return()*100,
            'Train_Sharpe': pf_train.sharpe_ratio(),
            # Test
            'Test_Trades': pf_test.trades.count(),
            'Test_Return': pf_test.total_return()*100,
            'Test_Sharpe': pf_test.sharpe_ratio(),
        }
        all_stats.append(row)

final = pd.DataFrame(all_stats)

# Calcular trades por día
total_days = (ohlcv.index[-1] - ohlcv.index[0]).days
final['Trades_Per_Day'] = final['Trades'] / total_days

# Filtrar: Sharpe > 0 en FULL Y en TEST (out-of-sample)
robust = final[(final['Sharpe'] > 0) & (final['Test_Sharpe'] > 0)].copy()

# Ordenar por Sharpe del TEST (out-of-sample) que es lo que realmente importa
robust = robust.sort_values('Test_Sharpe', ascending=False)

print("\n" + "="*90)
print("TOP 15 ESTRATEGIAS ROBUSTAS (Sharpe>0 en Train Y Test, Ordenado por Test_Sharpe)")
print("="*90)
cols = ['Strategy','TP','SL','Trades','Trades_Per_Day','WinRate','Return','Sharpe',
        'Train_Sharpe','Test_Sharpe','Test_Return','MaxDD']
print(robust[cols].head(15).to_string())

# También filtrar las que tienen >= 0.5 trades/día (1 cada 2 días)
freq_robust = robust[robust['Trades_Per_Day'] >= 0.5].sort_values('Test_Sharpe', ascending=False)
print("\n" + "="*90)
print("TOP 15 ALTA FRECUENCIA (>=1 trade cada 2 días, Sharpe>0 en Train Y Test)")
print("="*90)
print(freq_robust[cols].head(15).to_string())

out_path = 'C:/ProyectosQuant/EdgeLab/validation/walkforward_results.csv'
final.sort_values('Test_Sharpe', ascending=False).to_csv(out_path, index=False)
print(f"\nResultados completos guardados en {out_path}")
