import pandas as pd
import numpy as np
import vectorbt as vbt
import datetime
import warnings

warnings.filterwarnings('ignore')

# Helper times
t00_00 = datetime.time(0, 0)
t02_00 = datetime.time(2, 0)
t06_00 = datetime.time(6, 0)
t07_45 = datetime.time(7, 45)
t08_00 = datetime.time(8, 0)
t08_45 = datetime.time(8, 45)
t12_00 = datetime.time(12, 0)
t13_00 = datetime.time(13, 0)
t13_15 = datetime.time(13, 15)
t14_00 = datetime.time(14, 0)
t16_00 = datetime.time(16, 0)
t20_00 = datetime.time(20, 0)

print("Loading data...")
try:
    df = pd.read_parquet('C:/ProyectosQuant/EdgeLab/data/eurusd_ticks.parquet')
    df['mid'] = (df['bid'] + df['ask']) / 2
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    df_15m = df['mid'].resample('15min').ohlc()
    df_15m.dropna(inplace=True)
except Exception as e:
    print(f"Error loading data: {e}")
    print("Creating dummy data for testing...")
    dates = pd.date_range('2023-01-01', '2024-06-30', freq='15min')
    df_15m = pd.DataFrame(index=dates, data={
        'open': np.random.randn(len(dates)).cumsum()*0.001 + 1.08,
    })
    df_15m['high'] = df_15m['open'] + np.random.rand(len(dates))*0.002
    df_15m['low'] = df_15m['open'] - np.random.rand(len(dates))*0.002
    df_15m['close'] = df_15m['open'] + np.random.randn(len(dates))*0.001

print(f"Data loaded: {len(df_15m)} bars")

close = df_15m['close']
open_p = df_15m['open']
high = df_15m['high']
low = df_15m['low']

base_price = 1.08
pip_size = 0.0001
pip_pct = pip_size / base_price

# --- Strategy A: ARB (for correlation baseline) ---
print("Simulating ARB (for correlation baseline)...")
sma200 = vbt.MA.run(close, 200).ma
asian_mask = (close.index.time >= t00_00) & (close.index.time < t08_00)

asian_high = high.copy()
asian_high[~asian_mask] = np.nan
asian_high = asian_high.groupby(asian_high.index.date).transform('max').reindex(close.index).ffill()

asian_low = low.copy()
asian_low[~asian_mask] = np.nan
asian_low = asian_low.groupby(asian_low.index.date).transform('min').reindex(close.index).ffill()

euro_session = (close.index.time >= t08_45) & (close.index.time <= t12_00)

entries_arb = (close > asian_high) & (close > sma200) & euro_session
short_entries_arb = (close < asian_low) & (close < sma200) & euro_session

exits_arb = close.index.time >= t16_00
short_exits_arb = close.index.time >= t16_00

pf_arb = vbt.Portfolio.from_signals(
    close, 
    entries=entries_arb.shift(1).fillna(False).astype(bool),
    exits=exits_arb,
    short_entries=short_entries_arb.shift(1).fillna(False).astype(bool),
    short_exits=short_exits_arb,
    tp_stop=20 * pip_pct,
    sl_stop=50 * pip_pct,
    init_cash=10000,
    fees=0.0001,
    freq='15min'
)
returns_arb_daily = pf_arb.value().groupby(pf_arb.value().index.date).last().pct_change().dropna()

def get_sharpe(rets):
    if len(rets) < 2 or rets.std() == 0:
        return np.nan
    return np.sqrt(252) * rets.mean() / rets.std()

def run_backtest(name, entries, exits, short_entries, short_exits, tp_pips, sl_pips):
    pf = vbt.Portfolio.from_signals(
        close,
        entries=entries.shift(1).fillna(False).astype(bool),
        exits=exits,
        short_entries=short_entries.shift(1).fillna(False).astype(bool),
        short_exits=short_exits,
        tp_stop=tp_pips * pip_pct,
        sl_stop=sl_pips * pip_pct,
        init_cash=10000,
        fees=0.0001,
        freq='15min'
    )
    
    total_trades = pf.trades.count()
    try:
        win_rate = pf.trades.win_rate()
    except TypeError:
        win_rate = pf.trades.win_rate
        
    try:
        total_return = pf.total_return()
    except TypeError:
        total_return = pf.total_return
        
    try:
        max_dd = pf.max_drawdown()
    except TypeError:
        max_dd = pf.max_drawdown
    
    daily_rets = pf.value().groupby(pf.value().index.date).last().pct_change().dropna()
    sharpe = get_sharpe(daily_rets)
    
    mid_date = close.index[len(close) // 2].date()
    train_rets = daily_rets[daily_rets.index < mid_date]
    test_rets = daily_rets[daily_rets.index >= mid_date]
    
    train_sharpe = get_sharpe(train_rets)
    test_sharpe = get_sharpe(test_rets)
    
    print(f"\n--- {name} ---")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate*100:.2f}%" if pd.notnull(win_rate) else "Win Rate: NaN")
    print(f"Total Return: {total_return*100:.2f}%" if pd.notnull(total_return) else "Total Return: NaN")
    print(f"Sharpe: {sharpe:.2f}" if pd.notnull(sharpe) else "Sharpe: NaN")
    print(f"Max DD: {max_dd*100:.2f}%" if pd.notnull(max_dd) else "Max DD: NaN")
    print(f"Train Sharpe: {train_sharpe:.2f}" if pd.notnull(train_sharpe) else "Train Sharpe: NaN")
    print(f"Test Sharpe: {test_sharpe:.2f}" if pd.notnull(test_sharpe) else "Test Sharpe: NaN")
    
    corr = daily_rets.corr(returns_arb_daily)
    print(f"Correlation with ARB: {corr:.3f}")

# --- Strategy B: London Close Fade ---
open_08 = open_p.where(open_p.index.time == t08_00).groupby(open_p.index.date).transform('first').reindex(close.index).ffill()
close_14 = close.where(close.index.time == t14_00).groupby(close.index.date).transform('first').reindex(close.index).ffill()
london_move = close_14 - open_08

bb = vbt.BBANDS.run(close, window=20, alpha=2)
london_window = (close.index.time >= t14_00) & (close.index.time <= t16_00)

entries_B = (london_move < -30 * pip_size) & (close < bb.lower) & london_window
short_entries_B = (london_move > 30 * pip_size) & (close > bb.upper) & london_window
time_stop_B = close.index.time >= t20_00

run_backtest("Strategy B: London Close Fade", entries_B, time_stop_B, short_entries_B, time_stop_B, tp_pips=15, sl_pips=30)

# --- Strategy C: Asian Session Range Reversion (RSI) ---
rsi = vbt.RSI.run(close, window=14).rsi
atr = vbt.ATR.run(high, low, close, window=14).atr
atr_40_thresh = atr.rolling(30*96, min_periods=96).quantile(0.4)
low_vol = atr < atr_40_thresh

asian_window = (close.index.time >= t02_00) & (close.index.time <= t06_00)
rsi_cross_below_30 = (rsi < 30) & (rsi.shift(1) >= 30)
rsi_cross_above_70 = (rsi > 70) & (rsi.shift(1) <= 70)

entries_C = rsi_cross_below_30 & low_vol & asian_window
short_entries_C = rsi_cross_above_70 & low_vol & asian_window
time_stop_C = close.index.time >= t07_45

run_backtest("Strategy C: Asian Range Reversion", entries_C, time_stop_C, short_entries_C, time_stop_C, tp_pips=10, sl_pips=20)

# --- Strategy D: NY Open Momentum ---
pre_ny_window = (close.index.time >= t12_00) & (close.index.time <= t13_00)
pre_ny_high = high.where(pre_ny_window).groupby(high.index.date).transform('max').reindex(close.index).ffill()
pre_ny_low = low.where(pre_ny_window).groupby(low.index.date).transform('min').reindex(close.index).ffill()
pre_ny_range = pre_ny_high - pre_ny_low

valid_range = (pre_ny_range >= 10 * pip_size) & (pre_ny_range <= 40 * pip_size)
ny_window = close.index.time == t13_15

entries_D = (close > pre_ny_high) & valid_range & ny_window
short_entries_D = (close < pre_ny_low) & valid_range & ny_window
time_stop_D = close.index.time >= t20_00

run_backtest("Strategy D: NY Open Momentum", entries_D, time_stop_D, short_entries_D, time_stop_D, tp_pips=25, sl_pips=40)

# --- Strategy E: Friday Reversal ---
df_15m['week_id'] = df_15m.index.isocalendar().year.astype(str) + '_' + df_15m.index.isocalendar().week.astype(str)
monday_open = df_15m.groupby('week_id')['open'].transform('first')

friday_14_window = (close.index.dayofweek == 4) & (close.index.time == t14_00)
weekly_move = close - monday_open

entries_E = (weekly_move < -80 * pip_size) & friday_14_window
short_entries_E = (weekly_move > 80 * pip_size) & friday_14_window
time_stop_E = (close.index.dayofweek == 4) & (close.index.time >= t20_00)

run_backtest("Strategy E: Friday Reversal", entries_E, time_stop_E, short_entries_E, time_stop_E, tp_pips=20, sl_pips=40)

print("\nDone.")
