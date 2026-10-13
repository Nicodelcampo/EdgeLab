"""Fixed development representation benchmark. No tuning or market export.

A/E are deterministic features, not new information or physical mechanisms.
Fit once on already inspected sessions; score identical usable anchors.
"""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import math
import numpy as np
from .phenomena_states import classify_components,eligible
from .build_target_free_pilot import digest
TRAIN=('2026-06-15','2026-06-16')
EVAL=('2026-06-17','2026-06-18','2026-06-19','2026-06-22','2026-06-23','2026-06-24','2026-06-25','2026-06-26','2026-06-29','2026-06-30','2026-07-01','2026-07-02')
MODELS=('PRIOR','CONTINUOUS','CONTINUOUS_CC','CONTINUOUS_A','CONTINUOUS_E','CONTINUOUS_AE')
CAL_SHA='3f88b2b5f12a9ac528e2b433cb36002b0f7df49135993fc73be151bc75717bc9'
WINDOW_NONNEG=('count','volume','buy_volume','sell_volume','unknown_volume','mean_trade_size','range_midpoint_ticks','path_midpoint_ticks','spread_at_end_ticks')
WINDOW_COVERAGE=('quote_volume_coverage','signed_volume_coverage')
FEATURES=tuple(f'{side}:log1p:{k}' for side in ('current','prior') for k in WINDOW_NONNEG)+tuple(f'{side}:{k}' for side in ('current','prior') for k in WINDOW_COVERAGE)+('current:signed_log1p','prior:signed_log1p','pressure_ratio:log1p','trade_count_ratio:log1p','total_volume_ratio:log1p','progress:signed_log1p','prior_progress:signed_log1p','abs_progress:log1p','context_range:log1p','barrier:log1p','RTH','direction')

def verified_calibration(c):
    if c.get('sha256')!=CAL_SHA or digest({k:v for k,v in c.items() if k!='sha256'})!=CAL_SHA:raise ValueError('published frozen calibration only')
    return c

def phase_key(row):
    date=row['trade_date'];ns=row['timestamp_ns']
    if date not in TRAIN+EVAL or type(ns) is not int:raise ValueError('explicit benchmark research dates')
    end=int(datetime.fromisoformat(date+'T22:00:00+00:00').timestamp())*10**9
    if not end-86400*10**9<=ns<end:raise ValueError('natural session clock binding')
    local=datetime.fromtimestamp(ns//10**9,timezone.utc).astimezone(ZoneInfo('America/Chicago'))
    return ('RTH' if 510<=local.hour*60+local.minute<900 else 'OTHER')+':'+str(row['windows']['20']['direction_from_prior'])

def state(row,c):
    key=phase_key(row);return classify_components(row['windows']['20'],c['cells'].get(key))

def logpos(x):
    if type(x) not in (int,float) or not math.isfinite(x) or x<0:raise ValueError('finite nonnegative feature')
    return math.log1p(x)
def signed(x):
    if type(x) not in (int,float) or not math.isfinite(x):raise ValueError('finite signed feature')
    return math.copysign(math.log1p(abs(x)),x)

def features(row,barrier):
    p=row['windows']['20']
    if eligible(p) or row['windows']['60']['current']['status']!='OBSERVABLE':raise ValueError('common observable feature population')
    values=[logpos(p[side][k]) for side in ('current','prior') for k in WINDOW_NONNEG]
    for side in ('current','prior'):
        for k in WINDOW_COVERAGE:
            v=p[side][k]
            if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1:raise ValueError('feature coverage')
            values.append(v)
    values += [signed(p[side]['signed_volume_proxy']) for side in ('current','prior')]
    values += [logpos(p[k]) for k in ('pressure_ratio','trade_count_ratio','total_volume_ratio')]
    values += [signed(p['directed_progress_ticks']),signed(p['prior_directed_progress_ticks']),logpos(abs(p['directed_progress_ticks'])),logpos(row['windows']['60']['current']['range_midpoint_ticks']),logpos(barrier),float(phase_key(row).startswith('RTH')),float(p['direction_from_prior'])]
    # Capacity-matched smooth bases fixed before scoring. Not a tuned contender.
    cc=(math.tanh(math.log(max(p['pressure_ratio'],1e-12)))*math.tanh(p['directed_progress_ticks']/4.),math.tanh(math.log(max(p['trade_count_ratio'],1e-12)))*math.tanh(p['prior_directed_progress_ticks']/4.))
    return np.array(values,dtype=float),np.array(cc,dtype=float)

def design(x,cc,ae,name):
    if name=='CONTINUOUS':return x
    if name=='CONTINUOUS_CC':return np.column_stack((x,cc))
    if name=='CONTINUOUS_A':return np.column_stack((x,ae[:,0]))
    if name=='CONTINUOUS_E':return np.column_stack((x,ae[:,1]))
    if name=='CONTINUOUS_AE':return np.column_stack((x,ae))
    raise ValueError('fixed design name')

def fit(x,y,weights,lam=.01):
    x=np.asarray(x,float);y=np.asarray(y);w=np.asarray(weights,float)
    if x.ndim!=2 or len(x)<1 or y.shape!=(len(x),) or y.dtype.kind not in 'iu' or np.any((y<0)|(y>2)) or w.shape!=(len(x),) or not np.isfinite(x).all() or not np.isfinite(w).all() or np.any(w<=0) or lam!=.01:raise ValueError('finite fixed ridge training')
    w=w/w.sum();mu=w@x;sd=np.sqrt(w@((x-mu)**2));sd=np.where(sd<1e-12,1.,sd)
    z=np.column_stack((np.ones(len(x)),(x-mu)/sd));target=np.eye(3)[y];pen=np.eye(z.shape[1])*lam;pen[0,0]=0
    coef=np.linalg.solve(z.T@(w[:,None]*z)+pen,z.T@(w[:,None]*target))
    return {'mean':mu,'scale':sd,'coef':coef,'prior':w@target}

def predict(model,x):
    x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[1]!=len(model['mean']) or not np.isfinite(x).all():raise ValueError('finite fixed inference matrix')
    p=np.clip(np.column_stack((np.ones(len(x)),(x-model['mean'])/model['scale']))@model['coef'],0.,1.)
    total=p.sum(axis=1);zero=total<=0
    p[zero]=model['prior'];total=p.sum(axis=1)
    return p/total[:,None]

def brier(p,y):
    p=np.asarray(p,float);y=np.asarray(y)
    if p.shape!=(len(y),3) or y.dtype.kind not in 'iu' or np.any((y<0)|(y>2)) or not np.isfinite(p).all() or np.any((p<0)|(p>1)) or not np.allclose(p.sum(axis=1),1.,rtol=0,atol=1e-12):raise ValueError('three-class probability simplex')
    return np.sum((p-np.eye(3)[y])**2,axis=1)
