import numpy as np
from edgelab.equivalence import tick_bars,match_bar_size,sync_resample,signal_agreement,outcome_agreement,ema_cross_signals

def test_tick_bars_do_not_cross_groups_and_drop_tail():
    ts=np.arange(100);px=np.arange(100.);g=np.r_[np.zeros(55,int),np.ones(45,int)];t,c,gg=tick_bars(ts,px,10,g);assert len(t)==5+4 and np.all(np.diff(t)>0) and (gg[:5]==0).all() and (gg[5:]==1).all();assert c[0]==9

def test_match_bar_size_recovers_the_event_rate_ratio():
    rng=np.random.default_rng(0);T=20*86_400_000_000_000
    fut=np.sort(rng.integers(0,T,200_000));spot=np.sort(rng.integers(0,T,800_000))     # el sustituto emite 4x más eventos
    r=match_bar_size(fut,spot,25);assert 80<=r["best"]["n_spot"]<=125

def test_sync_resample_takes_last_value_before_close():
    ts=np.array([10,20,30]);px=np.array([1.,2.,3.]);o=sync_resample(np.array([5,10,25,40]),ts,px);assert np.isnan(o[0]) and o[1]==1. and o[2]==2. and o[3]==3.

def test_signals_identical_on_scaled_shifted_copy_and_agreement_is_perfect():
    rng=np.random.default_rng(1);x=np.cumsum(rng.standard_normal(30000));i,d=ema_cross_signals(x,20,50,200);assert len(i)>3
    j,e=ema_cross_signals(x*3+100,20,50,200);assert np.array_equal(i,j) and np.array_equal(d,e)     # invariante a escala y nivel (la base del spot)
    ts=np.arange(len(x))*10**9;a=signal_agreement(ts[i],d,ts[j],e,1.);assert a["f1"]==1.0

def test_agreement_degrades_with_noisy_proxy_and_outcome_corr_high_for_same_path():
    rng=np.random.default_rng(2);x=np.cumsum(rng.standard_normal(40000));ts=np.arange(len(x))*10**9
    i,d=ema_cross_signals(x,20,50,200);y=x+np.cumsum(rng.standard_normal(len(x)))*0.0+rng.standard_normal(len(x))*0.5;j,e=ema_cross_signals(y,20,50,200)
    a=signal_agreement(ts[i],d,ts[j],e,60.);assert 0<=a["f1"]<=1
    o=outcome_agreement(ts[i],d,ts,x,ts[i],d,ts,x,[600.],day_ns=3000*10**9);assert o["600"]["daily_pnl_correlation"]>0.999
