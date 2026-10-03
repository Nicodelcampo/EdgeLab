import numpy as np,pytest
from edgelab.funnel.schedule_nulls import session_bootstrap,direction_null_total,placebo_schedule_null

def test_bootstrap_ci_contains_mean_and_is_session_based():
    rng=np.random.default_rng(1);s=np.repeat(np.arange(40),5);v=rng.normal(2,5,200)
    r=session_bootstrap(v,s,2000,3);assert r['ci_low']<r['mean']<r['ci_high'] and r['n_sessions']==40
    with pytest.raises(ValueError):session_bootstrap([],[])

def test_direction_null_detects_real_direction_and_not_noise():
    rng=np.random.default_rng(2);s=np.repeat(np.arange(60),6);edge=rng.normal(0,1,360)
    plus=3+edge;minus=-3-edge          # directional information: own direction wins
    assert direction_null_total(plus,minus,s,2000,1)['p']<.01
    x=rng.normal(0,5,360);r=direction_null_total(x,-x,s,2000,1);assert r['p']>.05   # symmetric noise: nothing to find
    with pytest.raises(ValueError):direction_null_total([1.,np.nan],[1.,1.],[0,1])

def test_placebo_schedule_flags_special_slots_only():
    R,K=30,20;rng=np.random.default_rng(4);S=rng.normal(0,10,(R,K));actual=rng.integers(0,K,R)
    S[np.arange(R),actual]+=40            # the actual slots are genuinely better
    assert placebo_schedule_null(S,actual,3000,1)['p']<.01
    S2=rng.normal(0,10,(R,K));assert placebo_schedule_null(S2,actual,3000,1)['p']>.05
    with pytest.raises(ValueError):placebo_schedule_null(S2,actual[:5])

def test_exposure_preserving_null_ignores_drift_but_sees_timing():
    from edgelab.funnel.schedule_nulls import exposure_preserving_direction_null
    rng=np.random.default_rng(5);n=400;s=np.repeat(np.arange(40),10)
    drift=np.repeat(rng.normal(0,20,40),10)                    # market goes up or down for the whole session
    d=np.where(drift>0,1,-1)                                   # strategy is simply on the side of the drift of its session
    long_out=drift+rng.normal(0,3,n);short_out=-drift+rng.normal(0,3,n)
    plus=np.where(d==1,long_out,short_out);minus=np.where(d==1,short_out,long_out)
    # same-side-per-session exposure: permuting within a session cannot change anything -> p ~ 1, drift explains it
    assert exposure_preserving_direction_null(plus,minus,d,s,500,1)['p']>.5
    # now directions vary inside sessions and the strategy picks the right one each time -> real timing skill
    d2=rng.choice([-1,1],n);edge=rng.normal(0,3,n)
    lg=rng.normal(0,3,n)+np.where(d2==1,6,-6);sh=-lg
    p2=np.where(d2==1,lg,sh);m2=np.where(d2==1,sh,lg)
    assert exposure_preserving_direction_null(p2,m2,d2,s,500,1)['p']<.01
    with pytest.raises(ValueError):exposure_preserving_direction_null([1.],[1.],[0],[0])
