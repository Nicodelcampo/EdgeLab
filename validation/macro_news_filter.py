import numpy as np
import pandas as pd
import vectorbt as vbt
import warnings

warnings.filterwarnings('ignore')

print("Cargando datos...")
data_path = 'C:/ProyectosQuant/EdgeLab/data/eurusd_ticks.parquet'
df = pd.read_parquet(data_path)
df['mid'] = (df['bid'] + df['ask']) / 2.0
df.set_index('timestamp', inplace=True)
ohlcv = df['mid'].resample('15min').ohlc().ffill().dropna()

# 1. Identificar días de alta volatilidad (News Days)
# Calculamos el rango máximo de cualquier vela de 15m durante la sesión europea/americana
daily_ranges = (ohlcv['high'] - ohlcv['low']).groupby(ohlcv.index.date).max() * 10000 # pips
# Consideramos "Día de Noticias Macro" a los días en el top 15% de volatilidad
threshold = daily_ranges.quantile(0.85)
news_days = daily_ranges[daily_ranges > threshold].index
print(f"Umbral de volatilidad para ser considerado 'Día Macro': {threshold:.1f} pips en 15 mins")
print(f"Total días: {len(daily_ranges)}, Días Macro excluidos: {len(news_days)}")

# 2. Asian Range
asian_candles = ohlcv.between_time('00:00', '07:45', inclusive='both')
asian_high = asian_candles['high'].groupby(asian_candles.index.date).max()
asian_low = asian_candles['low'].groupby(asian_candles.index.date).min()

asian_high_s = pd.Series(np.nan, index=ohlcv.index, dtype=float)
asian_low_s = pd.Series(np.nan, index=ohlcv.index, dtype=float)
for d in asian_high.index:
    mask = ohlcv.index.date == d
    asian_high_s[mask] = asian_high[d]
    asian_low_s[mask] = asian_low[d]

# 3. SMA 200
sma_200 = ohlcv['close'].rolling(200).mean()

# 4. Señales
entry_windows = ['08:45', '09:00', '11:00', '12:00']
signals = {}

# Filtro para excluir trades en News Days
is_normal_day = ~pd.Series(ohlcv.index.date, index=ohlcv.index).isin(news_days)

for et in entry_windows:
    at_time = (ohlcv.index.time == pd.to_datetime(et).time()) & is_normal_day
    
    cond_long = at_time & (ohlcv['close'] > asian_high_s) & (ohlcv['close'] > sma_200)
    cond_short = at_time & (ohlcv['close'] < asian_low_s) & (ohlcv['close'] < sma_200)
    
    signals[et] = {
        'long': cond_long,
        'short': cond_short
    }

# 5. Exits (15:45)
time_idx = ohlcv.between_time('08:00', '16:00', inclusive='left').index
exits = pd.Series(False, index=ohlcv.index)
daily_groups = pd.Series(range(len(time_idx)), index=time_idx).groupby(time_idx.date)
for d, group in daily_groups:
    exits.loc[group.index[-1]] = True

# 6. Backtest Combinado
TP = 0.002  # 20 pips
SL = 0.005  # 50 pips
FEES = 0.0001
exec_price = ohlcv['open'].shift(-1)

print("\n--- RESULTADOS EXCLUYENDO EL 15% DE DÍAS MÁS VOLÁTILES (NOTICIAS MACRO) ---")
portfolios = []
for et in entry_windows:
    pf = vbt.Portfolio.from_signals(
        close=ohlcv['close'],
        entries=signals[et]['long'],
        short_entries=signals[et]['short'],
        exits=exits,
        short_exits=exits,
        tp_stop=TP,
        sl_stop=SL,
        price=exec_price,
        freq='15min',
        fees=FEES,
        init_cash=10000,
    )
    portfolios.append(pf)

combined_equity = sum(p.value() for p in portfolios) / 4.0 * 4
combined_returns = combined_equity.pct_change().fillna(0)
total_ret = (combined_equity.iloc[-1] / combined_equity.iloc[0] - 1) * 100
sharpe = combined_returns.mean() / combined_returns.std() * np.sqrt(96 * 252)
max_dd = ((combined_equity / combined_equity.cummax()) - 1).min() * 100
total_trades = sum(p.trades.count() for p in portfolios)

print(f"Total Trades (Filtrados): {total_trades}")
print(f"Retorno Total: {total_ret:+.2f}%")
print(f"Sharpe Ratio:  {sharpe:.2f}")
print(f"Max Drawdown:  {max_dd:.2f}%")
