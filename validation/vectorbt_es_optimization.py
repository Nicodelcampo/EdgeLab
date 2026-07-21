"""
ES Futures - ARB Strategy Optimization & News Filter
====================================================
Adapts the Asian Range Breakout logic for S&P 500 (ES).
- 1 point = $50 = 4 ticks.
- Dynamic timezone handling for NY Open (13:30/14:30 UTC).
- News filter (volatility spikes)
- Parameter grid search (TP/SL).
"""

import numpy as np
import pandas as pd
import vectorbt as vbt
import warnings
import gc
from datetime import timedelta

warnings.filterwarnings('ignore')
print("Cargando datos de ES (M1)...")
data_path = 'C:/Users/nicoc/OneDrive/Documentos/DataMining/data/es_continuous_m1.parquet'

df = pd.read_parquet(data_path)
df['mid'] = df['close'] # En ES usamos close directamente si no hay bid/ask
# El index ya está en datetime y verificamos que es UTC. 
# Lo forzamos a timezone UTC para el manejo de DST.
df.index = df.index.tz_localize('UTC')

print("Resampleando a M15...")
ohlcv = df['mid'].resample('15min').ohlc().ffill().dropna()
del df
gc.collect()

# Definimos el Rango Overnight (00:00 a 13:00 UTC) -> Captura la noche entera hasta antes del open NY.
print("\nCalculando Overnight Range (00:00 - 13:00 UTC)...")
overnight_candles = ohlcv.between_time('00:00', '13:00', inclusive='both')
overnight_high = overnight_candles['high'].groupby(overnight_candles.index.date).max()
overnight_low = overnight_candles['low'].groupby(overnight_candles.index.date).min()

on_high_s = pd.Series(np.nan, index=ohlcv.index, dtype=float)
on_low_s = pd.Series(np.nan, index=ohlcv.index, dtype=float)
for d in overnight_high.index:
    mask = ohlcv.index.date == d
    on_high_s[mask] = overnight_high[d]
    on_low_s[mask] = overnight_low[d]

# SMA 200
print("Calculando SMA 200...")
sma_200 = ohlcv['close'].rolling(200).mean()

# Filtro de Noticias Macro (REMOVIDO para igualar NT8 y evitar lookahead)
# daily_ranges = (ohlcv['high'] - ohlcv['low']).groupby(ohlcv.index.date).max()
# threshold = daily_ranges.quantile(0.85)
# news_days = daily_ranges[daily_ranges > threshold].index
# is_normal_day = ~pd.Series(ohlcv.index.date, index=ohlcv.index).isin(news_days)
# print(f"Umbral de volatilidad: {threshold:.2f} puntos en 15m. Días excluidos: {len(news_days)}")

# Generación de Señales con múltiples ventanas
# Ventanas: 13:30 (NY Open), 14:00, 14:30
# Usamos el convertidor a NY Time para que se adapte al DST automáticamente.
ohlcv_ny = ohlcv.index.tz_convert('America/New_York')
windows = ['09:30', '10:00', '10:30'] # Hora local de NY
signals = {}

for w in windows:
    # Máscara de tiempo en NY local
    at_time = (ohlcv_ny.time == pd.to_datetime(w).time())
    
    # Se remueve is_normal_day.values para igualar la lógica de NT8
    cond_long = at_time & (ohlcv['close'].values > on_high_s.values) & (ohlcv['close'].values > sma_200.values)
    cond_short = at_time & (ohlcv['close'].values < on_low_s.values) & (ohlcv['close'].values < sma_200.values)
    
    signals[w] = {
        'long': pd.Series(cond_long, index=ohlcv.index),
        'short': pd.Series(cond_short, index=ohlcv.index)
    }
    print(f"Ventana NY {w}: {cond_long.sum()} Longs, {cond_short.sum()} Shorts")

# Consolidamos las señales de las ventanas en una sola serie para la optimización global
all_longs = signals['09:30']['long'] | signals['10:00']['long'] | signals['10:30']['long']
all_shorts = signals['09:30']['short'] | signals['10:00']['short'] | signals['10:30']['short']

# Exits a las 15:45 NY time (15 mins antes del cierre de contado)
at_exit_time = ohlcv_ny.time == pd.to_datetime('15:45').time()
exits = pd.Series(at_exit_time, index=ohlcv.index)

# Optimización Grid Search
# ES 1 punto = $50. Un tick = 0.25 puntos.
print("\n--- INICIANDO GRID SEARCH DE TP/SL ---")
tp_points = [5, 10, 15, 20] # puntos enteros
sl_points = [10, 15, 25, 40]

# Preparamos las combinaciones
entries = all_longs
short_entries = all_shorts
close_price = ohlcv['close']
exec_price = ohlcv['open'].shift(-1) # Mismo anti-lookahead
fees_points = 0.50 # 2 ticks de spread/comision por trade

results = []

for tp in tp_points:
    for sl in sl_points:
        # vbt Portfolio maneja tp/sl como pct si se le pasa float, pero si le pasamos
        # sl_stop=sl y stop_type='fixed' calcula distancia absoluta, 
        # pero es más facil usar delta en pts. VectorBT no soporta stop_type='fixed' en from_signals directo para deltas a menos que usemos una formula.
        # Alternativa: Usar tp_stop y sl_stop como %. Como el ES cotiza ~5000, 10 pts es 0.20%.
        # Calculamos dinámicamente:
        # Generamos matrices de stops dinámicos basados en pct del exec_price
        # Esto es: tp_pct = tp_points / exec_price
        
        pf = vbt.Portfolio.from_signals(
            close=close_price,
            entries=entries,
            short_entries=short_entries,
            exits=exits,
            short_exits=exits,
            tp_stop=tp / exec_price, 
            sl_stop=sl / exec_price,
            price=exec_price,
            freq='15min',
            fees=fees_points / exec_price, # Fees dinámicas para simular 0.5 puntos
            init_cash=50000,
        )
        
        ret = pf.total_return() * 100
        wr = pf.trades.win_rate() * 100
        count = pf.trades.count()
        sharpe = pf.sharpe_ratio() if count > 0 else 0
        dd = pf.max_drawdown() * 100
        
        results.append({
            'TP': tp,
            'SL': sl,
            'Trades': count,
            'WinRate': wr,
            'Return': ret,
            'Sharpe': sharpe,
            'MaxDD': dd
        })

res_df = pd.DataFrame(results).sort_values('Sharpe', ascending=False)
print("\nTop 5 Combinaciones (Ordenadas por Sharpe Ratio):")
print(res_df.head(5).to_string(index=False))

res_df.to_csv('C:/ProyectosQuant/EdgeLab/validation/es_optimization_results.csv', index=False)
print("Resultados guardados en validation/es_optimization_results.csv")
