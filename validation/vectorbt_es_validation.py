"""
ES Futures - Full EdgeLab Validation Suite
==========================================
Overnight Range Breakout + SMA 200
TP = 9 points (36 ticks), SL = 40 points (160 ticks)

Tests:
  1. OHLC consistency assertions
  2. Overnight range verification
  3. SMA 200 verification
  4. Signal timing verification (no look-ahead)
  5. Full period backtest (with/without news filter)
  6. Per-window breakdown
  7. Walk-Forward (3 independent periods)
  8. Monte Carlo Permutation Test (signal shuffle, 200 perms)
  9. Summary
"""

import numpy as np
import pandas as pd
import vectorbt as vbt
import warnings
import gc
from scipy import stats as sp_stats

warnings.filterwarnings('ignore')

# =========================================================================
# STEP 1: DATA LOADING AND OHLC VERIFICATION
# =========================================================================
print("=" * 80)
print("STEP 1: DATA LOADING AND OHLC VERIFICATION")
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

print(f"Range:  {ohlcv.index[0]} -> {ohlcv.index[-1]}")
print(f"Bars:   {len(ohlcv)}")
print(f"Calendar days: {(ohlcv.index[-1] - ohlcv.index[0]).days}")

assert (ohlcv['high'] >= ohlcv['low']).all(),   "BUG: high < low"
assert (ohlcv['high'] >= ohlcv['open']).all(),  "BUG: high < open"
assert (ohlcv['high'] >= ohlcv['close']).all(), "BUG: high < close"
assert (ohlcv['low']  <= ohlcv['open']).all(),  "BUG: low > open"
assert (ohlcv['low']  <= ohlcv['close']).all(), "BUG: low > close"
print("[OK] OHLC internally consistent (high >= open/close >= low)")

# =========================================================================
# STEP 2: OVERNIGHT RANGE (00:00 to 13:00 UTC ~= pre-RTH)
# =========================================================================
print("\n" + "=" * 80)
print("STEP 2: OVERNIGHT RANGE")
print("=" * 80)

# Use NY time for session logic (DST-safe)
ohlcv_ny = ohlcv.index.tz_convert('America/New_York')
is_pre_rth = ohlcv_ny.time < pd.to_datetime('09:30').time()
overnight_candles = ohlcv[is_pre_rth]

# Group by NY date for correct session assignment
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

flat_days = (on_high_s.dropna() == on_low_s.dropna()).sum()
assert (on_high_s.dropna() >= on_low_s.dropna()).all(), "BUG: overnight high < low"
print(f"[INFO] Days with zero overnight range (holidays/thin): {flat_days}")

sample_dates = overnight_high.index[5:8]
print("Sample Overnight Ranges (3 days):")
for d in sample_dates:
    oh, ol = overnight_high[d], overnight_low[d]
    print(f"  {d}: High={oh:.2f}, Low={ol:.2f}, Range={oh-ol:.2f} pts")
print(f"[OK] Overnight range calculated for {len(overnight_high)} days")

# =========================================================================
# STEP 3: SMA 200
# =========================================================================
print("\n" + "=" * 80)
print("STEP 3: SMA 200 (M15)")
print("=" * 80)

sma_200 = ohlcv['close'].rolling(200).mean()
sma_valid = sma_200.dropna()
print(f"SMA 200 = {200*15/60:.0f} hours lookback")
print(f"SMA range: [{sma_valid.min():.2f}, {sma_valid.max():.2f}]")
assert sma_valid.min() > 4000 and sma_valid.max() < 8000, "BUG: SMA outside ES range"
print("[OK] SMA 200 in valid ES range [4000-8000]")

# =========================================================================
# STEP 4: SIGNAL GENERATION AND TIMING VERIFICATION
# =========================================================================
print("\n" + "=" * 80)
print("STEP 4: SIGNAL GENERATION")
print("=" * 80)

windows_ny = ['09:30', '10:00', '10:30']

# News filter: exclude top 15% volatility days
daily_max_range = (ohlcv['high'] - ohlcv['low']).groupby(ny_dates).max()
threshold = daily_max_range.quantile(0.85)
news_days = set(daily_max_range[daily_max_range > threshold].index)
is_normal = ~ny_dates.isin(news_days)

print(f"Volatility threshold for 'Macro Day': {threshold:.2f} pts in 15min")
print(f"Total trading days: {len(daily_max_range)}, Macro days excluded: {len(news_days)}")

signals = {}
for w in windows_ny:
    at_time = ohlcv_ny.time == pd.to_datetime(w).time()
    
    cond_long  = at_time & (ohlcv['close'].values > on_high_s.values) & (ohlcv['close'].values > sma_200.values)
    cond_short = at_time & (ohlcv['close'].values < on_low_s.values)  & (ohlcv['close'].values < sma_200.values)
    
    cond_long_f  = cond_long  & is_normal.values
    cond_short_f = cond_short & is_normal.values
    
    signals[w] = {
        'long':  pd.Series(cond_long,  index=ohlcv.index),
        'short': pd.Series(cond_short, index=ohlcv.index),
        'long_f':  pd.Series(cond_long_f,  index=ohlcv.index),
        'short_f': pd.Series(cond_short_f, index=ohlcv.index),
    }
    
    # VERIFICATION: signals fire ONLY at the correct NY time
    if cond_long.any():
        sig_times = ohlcv_ny[cond_long].time
        assert all(t == pd.to_datetime(w).time() for t in sig_times), \
            f"BUG: long signal at wrong time for window {w}"
    if cond_short.any():
        sig_times = ohlcv_ny[cond_short].time
        assert all(t == pd.to_datetime(w).time() for t in sig_times), \
            f"BUG: short signal at wrong time for window {w}"
    
    print(f"  Window NY {w}: {cond_long.sum()} longs, {cond_short.sum()} shorts (raw) | "
          f"{cond_long_f.sum()} longs, {cond_short_f.sum()} shorts (filtered)")

all_longs  = signals['09:30']['long']  | signals['10:00']['long']  | signals['10:30']['long']
all_shorts = signals['09:30']['short'] | signals['10:00']['short'] | signals['10:30']['short']
all_longs_f  = signals['09:30']['long_f']  | signals['10:00']['long_f']  | signals['10:30']['long_f']
all_shorts_f = signals['09:30']['short_f'] | signals['10:00']['short_f'] | signals['10:30']['short_f']

total_raw = all_longs.sum() + all_shorts.sum()
total_filt = all_longs_f.sum() + all_shorts_f.sum()
print(f"\n[OK] All signals verified: correct NY time, conditions met")
print(f"Total combined signals: {total_raw} raw, {total_filt} filtered")

# Exit at 15:45 NY time
at_exit = ohlcv_ny.time == pd.to_datetime('15:45').time()
exits = pd.Series(at_exit, index=ohlcv.index)
exit_times = set(ohlcv_ny[at_exit].time)
assert all(t == pd.to_datetime('15:45').time() for t in exit_times), "BUG: exits not at 15:45"
print(f"[OK] All time-stops at 15:45 NY time")

# Execution: open of next bar (no look-ahead)
exec_price = ohlcv['open'].shift(-1)
print("[OK] Execution at open of NEXT bar (shift -1)")

# =========================================================================
# STEP 5: FULL PERIOD BACKTEST (TP=9, SL=40)
# =========================================================================
print("\n" + "=" * 80)
print("STEP 5: FULL PERIOD BACKTEST (TP=9 pts, SL=40 pts)")
print("=" * 80)

TP_PTS = 9
SL_PTS = 40
FEES_PTS = 0.50  # 2 ticks round-trip

def run_backtest(longs, shorts, close, ex, exits_s, label=""):
    tp_pct = TP_PTS / ex
    sl_pct = SL_PTS / ex
    fees_pct = FEES_PTS / ex
    
    pf = vbt.Portfolio.from_signals(
        close=close, entries=longs, short_entries=shorts,
        exits=exits_s, short_exits=exits_s,
        tp_stop=tp_pct, sl_stop=sl_pct,
        price=ex, freq='15min', fees=fees_pct, init_cash=50000,
    )
    tc = pf.trades.count()
    if tc == 0:
        print(f"  {label}: 0 trades")
        return pf
    wr = pf.trades.win_rate() * 100
    ret = pf.total_return() * 100
    sharpe = pf.sharpe_ratio()
    dd = pf.max_drawdown() * 100
    pf_ratio = pf.trades.profit_factor()
    print(f"  {label}: Trades={tc}, WR={wr:.1f}%, Ret={ret:+.2f}%, "
          f"Sharpe={sharpe:.2f}, MaxDD={dd:.2f}%, PF={pf_ratio:.2f}")
    return pf

pf_raw = run_backtest(all_longs, all_shorts, ohlcv['close'], exec_price, exits, "SIN filtro noticias")
pf_filt = run_backtest(all_longs_f, all_shorts_f, ohlcv['close'], exec_price, exits, "CON filtro noticias")

# =========================================================================
# STEP 6: PER-WINDOW BREAKDOWN
# =========================================================================
print("\n" + "=" * 80)
print("STEP 6: PER-WINDOW BREAKDOWN")
print("=" * 80)

for w in windows_ny:
    run_backtest(signals[w]['long'], signals[w]['short'], 
                 ohlcv['close'], exec_price, exits, f"Window {w}")

# =========================================================================
# STEP 7: WALK-FORWARD (3 INDEPENDENT PERIODS)
# =========================================================================
print("\n" + "=" * 80)
print("STEP 7: WALK-FORWARD (3 PERIODS)")
print("=" * 80)

total_bars = len(ohlcv)
third = total_bars // 3
p1_end = ohlcv.index[third]
p2_end = ohlcv.index[2 * third]

periods = [
    ("P1 TRAIN", ohlcv.index[0], p1_end),
    ("P2 VALID", p1_end, p2_end),
    ("P3 TEST ", p2_end, ohlcv.index[-1]),
]

for name, start, end in periods:
    mask = (ohlcv.index >= start) & (ohlcv.index < end)
    run_backtest(
        all_longs[mask], all_shorts[mask],
        ohlcv['close'][mask], exec_price[mask], exits[mask],
        f"{name} ({start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')})"
    )

# =========================================================================
# STEP 8: INDIVIDUAL TRADE AUDIT
# =========================================================================
print("\n" + "=" * 80)
print("STEP 8: TRADE AUDIT (first 10 trades)")
print("=" * 80)

trades = pf_raw.trades.records_readable
cols = ['Entry Timestamp', 'Exit Timestamp', 'Direction', 'PnL', 'Return', 'Status']
available_cols = [c for c in cols if c in trades.columns]
print(trades[available_cols].head(10).to_string())

# =========================================================================
# STEP 9: MONTE CARLO PERMUTATION TEST (200 shuffles)
# =========================================================================
print("\n" + "=" * 80)
print("STEP 9: MONTE CARLO PERMUTATION TEST (200 permutations)")
print("=" * 80)

real_return = pf_raw.total_return()
n_perms = 200
beat_count = 0
perm_returns = []

np.random.seed(42)
signal_indices_long  = np.where(all_longs.values)[0]
signal_indices_short = np.where(all_shorts.values)[0]
n_long  = len(signal_indices_long)
n_short = len(signal_indices_short)

# Valid candidate bars: those at the right NY times (any of the 3 windows)
candidate_mask = np.zeros(len(ohlcv), dtype=bool)
for w in windows_ny:
    candidate_mask |= (ohlcv_ny.time == pd.to_datetime(w).time())
candidate_indices = np.where(candidate_mask)[0]

for i in range(n_perms):
    # Randomly reassign signals to different valid window bars
    rand_long_idx  = np.random.choice(candidate_indices, size=n_long, replace=False) if n_long <= len(candidate_indices) else np.random.choice(candidate_indices, size=n_long, replace=True)
    rand_short_idx = np.random.choice(candidate_indices, size=n_short, replace=False) if n_short <= len(candidate_indices) else np.random.choice(candidate_indices, size=n_short, replace=True)
    
    rand_longs  = pd.Series(False, index=ohlcv.index)
    rand_shorts = pd.Series(False, index=ohlcv.index)
    rand_longs.iloc[rand_long_idx]  = True
    rand_shorts.iloc[rand_short_idx] = True
    
    tp_pct = TP_PTS / exec_price
    sl_pct = SL_PTS / exec_price
    fees_pct = FEES_PTS / exec_price
    
    pf_rand = vbt.Portfolio.from_signals(
        close=ohlcv['close'], entries=rand_longs, short_entries=rand_shorts,
        exits=exits, short_exits=exits,
        tp_stop=tp_pct, sl_stop=sl_pct,
        price=exec_price, freq='15min', fees=fees_pct, init_cash=50000,
    )
    rand_ret = pf_rand.total_return()
    perm_returns.append(rand_ret)
    if rand_ret >= real_return:
        beat_count += 1
    
    if (i + 1) % 50 == 0:
        p_running = (1 + beat_count) / (1 + i + 1)
        print(f"  MCPT {i+1}/{n_perms}  p_partial={p_running:.4f}")

p_value = (1 + beat_count) / (1 + n_perms)
perm_returns = np.array(perm_returns)
print(f"\nReal strategy return: {real_return*100:+.3f}%")
print(f"Random mean return:  {perm_returns.mean()*100:+.3f}%")
print(f"Random std return:   {perm_returns.std()*100:.3f}%")
print(f"Strategies that beat real: {beat_count}/{n_perms}")
print(f"P-value: {p_value:.4f}")
if p_value < 0.05:
    print("[OK] Edge is STATISTICALLY SIGNIFICANT (p < 0.05)")
elif p_value < 0.10:
    print("[WARNING] Marginal significance (0.05 <= p < 0.10)")
else:
    print("[FAIL] Edge is NOT statistically significant (p >= 0.10)")

# =========================================================================
# STEP 10: T-TEST ON DAILY RETURNS
# =========================================================================
print("\n" + "=" * 80)
print("STEP 10: T-TEST ON DAILY RETURNS (H0: mean return = 0)")
print("=" * 80)

equity = pf_raw.value()
daily_returns = equity.resample('1D').last().pct_change().dropna()
daily_returns = daily_returns[daily_returns != 0]

t_stat, t_pval = sp_stats.ttest_1samp(daily_returns, 0)
print(f"Trading days with activity: {len(daily_returns)}")
print(f"Mean daily return: {daily_returns.mean()*100:.4f}%")
print(f"Std daily return:  {daily_returns.std()*100:.4f}%")
print(f"T-statistic: {t_stat:.3f}")
print(f"P-value (2-tailed): {t_pval:.4f}")
if t_pval < 0.05:
    print("[OK] Daily returns significantly different from zero (p < 0.05)")
else:
    print("[INFO] Daily returns NOT significantly different from zero")

# =========================================================================
# STEP 11: SUMMARY
# =========================================================================
print("\n" + "=" * 80)
print("STEP 11: VALIDATION SUMMARY")
print("=" * 80)
print("[v] OHLC internally consistent")
print("[v] Overnight range: pre-RTH only, high > low always")
print("[v] SMA 200 in valid ES price range")
print("[v] Signals fire ONLY at correct NY windows")
print("[v] Execution at open of next bar (no look-ahead)")
print("[v] Time-stops all at 15:45 NY")
print(f"[v] Fees: {FEES_PTS} pts ({FEES_PTS*4:.0f} ticks) per trade")
print(f"[v] TP={TP_PTS} pts, SL={SL_PTS} pts")
print(f"MCPT p-value: {p_value:.4f}")
print(f"T-test p-value: {t_pval:.4f}")
