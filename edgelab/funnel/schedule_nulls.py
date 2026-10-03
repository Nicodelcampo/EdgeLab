"""Nulls for calendar/schedule strategies (entries at fixed times with time-based exits).

Vendor/strategy-agnostic: callers pass per-opportunity outcomes already priced with honest fills and costs.
All statistics are totals of net ticks. Randomization is by session so intra-session structure is preserved.
"""
from __future__ import annotations
import numpy as np


def session_bootstrap(values,sessions,n_boot=10_000,seed=0,alpha=.05):
    """Mean and percentile CI of per-trade values, resampling whole sessions."""
    v=np.asarray(values,float);s=np.asarray(sessions)
    if v.size==0:raise ValueError('no values')
    u,inv=np.unique(s,return_inverse=True);tot=np.bincount(inv,weights=v);cnt=np.bincount(inv).astype(float)
    rng=np.random.default_rng(seed);k=len(u);means=np.empty(n_boot)
    for b in range(n_boot):
        pick=rng.integers(0,k,k);means[b]=tot[pick].sum()/max(cnt[pick].sum(),1.)
    return {'mean':float(v.mean()),'n_trades':int(v.size),'n_sessions':int(k),'ci_low':float(np.quantile(means,alpha/2)),'ci_high':float(np.quantile(means,1-alpha/2)),'n_boot':int(n_boot)}


def direction_null_total(plus,minus,sessions,n_sims=5000,seed=0):
    """plus/minus: net outcome of each opportunity in its own / the opposite direction (NaN opportunities must be removed).
    Null: flip the direction of whole sessions at random. p = (1+#{null>=real})/(1+n)."""
    p=np.asarray(plus,float);m=np.asarray(minus,float);u,inv=np.unique(np.asarray(sessions),return_inverse=True)
    if p.shape!=m.shape or not np.isfinite(p).all() or not np.isfinite(m).all():raise ValueError('plus/minus must be finite and aligned')
    rng=np.random.default_rng(seed);real=float(p.sum())
    sp=np.bincount(inv,weights=p);sm=np.bincount(inv,weights=m)
    flips=rng.integers(0,2,(n_sims,len(u))).astype(bool)
    null=np.where(flips,sm,sp).sum(1)
    return {'real_total':real,'n_sims':int(n_sims),'null_mean':float(null.mean()),'null_sd':float(null.std()),'null_q95':float(np.quantile(null,.95)),'p':float((np.sum(null>=real)+1)/(n_sims+1))}


def placebo_schedule_null(S,actual_slots,n_draws=2000,seed=0,allowed_slots=None):
    """S[r,s] = total net ticks rule r would have earned at slot s (same weekday/direction/hold/filter).
    Placebo: every rule gets an independent uniformly drawn slot. p = P(placebo total >= actual total)."""
    S=np.asarray(S,float);R,K=S.shape;a=np.asarray(actual_slots)
    if a.shape!=(R,):raise ValueError('one actual slot per rule')
    real=float(S[np.arange(R),a].sum());rng=np.random.default_rng(seed)
    pool=np.arange(K) if allowed_slots is None else np.asarray(allowed_slots)
    draws=pool[rng.integers(0,len(pool),(n_draws,R))]
    null=S[np.arange(R)[None,:],draws].sum(1)
    return {'real_total':real,'n_draws':int(n_draws),'null_mean':float(null.mean()),'null_sd':float(null.std()),'null_q95':float(np.quantile(null,.95)),'p':float((np.sum(null>=real)+1)/(n_draws+1))}
