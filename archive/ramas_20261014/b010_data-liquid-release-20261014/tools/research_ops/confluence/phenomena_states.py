"""Frozen development A/E proxies calibrated only on an earlier session.

No outcomes, tape read, zone detector or fitting by successful response here.
Direction/clock calibration addresses context only; it is not causal matching.
"""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import math
import numpy as np
from .build_target_free_pilot import digest
STATES=('A_ONLY','E_ONLY','BOTH','NEITHER','UNKNOWN')
DATE_TRAIN='2026-06-12';EVAL_DATES=('2026-06-15','2026-06-16')
MIN_CAL=100
SESSION_BOUNDS={}
for _d in (DATE_TRAIN,)+EVAL_DATES:
    _end=int(datetime.fromisoformat(_d+'T22:00:00+00:00').timestamp())*10**9
    SESSION_BOUNDS[_d]=(_end-86400*10**9,_end)
def validate_row_clock(row):
    bounds=SESSION_BOUNDS.get(row['trade_date'])
    if not bounds or type(row['timestamp_ns']) is not int or not bounds[0]<=row['timestamp_ns']<bounds[1]:raise ValueError('bound natural-session clock; no mislabeled split')

def cell(row):
    validate_row_clock(row)
    local=datetime.fromtimestamp(row['timestamp_ns']//10**9,timezone.utc).astimezone(ZoneInfo('America/Chicago'))
    m=local.hour*60+local.minute;phase='RTH' if 510<=m<900 else 'OTHER'
    return phase+':'+str(row['windows']['20']['direction_from_prior'])

def components(pair):
    a,b=pair['current'],pair['prior'];side='buy_volume' if pair['direction_from_prior']==1 else 'sell_volume'
    vals={'pressure':a[side],'prior_pressure':b[side],'abs_progress':abs(pair['directed_progress_ticks']),
          'range':a['range_midpoint_ticks'],'path':a['path_midpoint_ticks']}
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in vals.values()):raise ValueError('finite state components')
    return vals

def eligible(pair):
    if pair['status']!='MEASURABLE_PAIR':return 'P0_PAIR_UNKNOWN'
    if pair['current']['status']!='OBSERVABLE' or pair['prior']['status']!='OBSERVABLE':raise ValueError('pair/window eligibility mismatch')
    if type(pair['direction_from_prior']) is not int or pair['direction_from_prior'] not in (-1,1):raise ValueError('signed prior direction')
    for w in (pair['current'],pair['prior']):
        c=w['signed_volume_coverage']
        if c is None or not math.isfinite(c) or not 0<=c<=1:raise ValueError('valid signed coverage')
        if c<.8:return 'SIGNED_COVERAGE_BELOW_80PCT'
    return None

class Calibration:
    def __init__(self):self.cells={};self.n=0
    def add(self,row):
        if row['trade_date']!=DATE_TRAIN:raise ValueError('calibration training date fixed; no eval rows')
        validate_row_clock(row);p=row['windows']['20']
        if eligible(p):return
        if self.n>=250000:raise ValueError('calibration anchor budget')
        self.n+=1;key=cell(row);a=self.cells.setdefault(key,{k:[] for k in ('pressure','prior_pressure','abs_progress','range','path')})
        for k,v in components(p).items():a[k].append(v)
    def freeze(self):
        out={}
        for key,a in sorted(self.cells.items()):
            n=len(a['pressure']);v={'anchors':n,'supported':n>=MIN_CAL}
            if v['supported']:
                q=lambda k,p:float(np.quantile(a[k],p,method='linear'))
                v.update(current_pressure_q80=q('pressure',.8),current_pressure_q20=q('pressure',.2),prior_pressure_q80=q('prior_pressure',.8),
                         stall_abs_progress_max=min(2.,q('abs_progress',.2)),stall_range_max=q('range',.25),stall_path_max=q('path',.25))
            if v['supported'] and (v['current_pressure_q80']<=0 or v['prior_pressure_q80']<=0):
                v={'anchors':n,'supported':False,'reason':'NONPOSITIVE_HIGH_PRESSURE_QUANTILE'}
            out[key]=v
        result={'schema':'phenomena_state_calibration_v1','training_trade_date':DATE_TRAIN,'minimum_cell_anchors':MIN_CAL,'cells':out,'outcomes_used':False}
        result['sha256']=digest(result);return result

def classify(row,calibration):
    validate_row_clock(row)
    if calibration['schema']!='phenomena_state_calibration_v1' or calibration['training_trade_date']!=DATE_TRAIN or row['trade_date'] not in EVAL_DATES or row['trade_date']<=calibration['training_trade_date'] or calibration['outcomes_used'] is not False:raise ValueError('chronological development split')
    base={k:v for k,v in calibration.items() if k!='sha256'}
    if digest(base)!=calibration['sha256']:raise ValueError('frozen calibration hash')
    p=row['windows']['20'];why=eligible(p)
    if why:return {'state':'UNKNOWN','reason':why,'tags':[]}
    key=cell(row);c=calibration['cells'].get(key)
    if not c or not c['supported']:return {'state':'UNKNOWN','reason':'CALIBRATION_CELL_UNSUPPORTED','tags':[]}
    return classify_components(p,c)

def classify_components(p,c):
    """Pure unchanged proxy definition; callers own chronology/calibration binding."""
    why=eligible(p)
    if why:return {'state':'UNKNOWN','reason':why,'tags':[]}
    if not c or not c['supported']:return {'state':'UNKNOWN','reason':'CALIBRATION_CELL_UNSUPPORTED','tags':[]}
    x=components(p);a,b=p['current'],p['prior']
    if any(not math.isfinite(p[k]) for k in ('pressure_ratio','trade_count_ratio','prior_directed_progress_ticks')):raise ValueError('finite state ratios')
    high=x['pressure']>=c['current_pressure_q80'] and x['prior_pressure']>=c['prior_pressure_q80']
    small=x['abs_progress']<=c['stall_abs_progress_max'];confined=x['range']<=c['stall_range_max'] and x['path']<=c['stall_path_max']
    A=high and small and confined
    impulse=x['prior_pressure']>=c['prior_pressure_q80'] and p['prior_directed_progress_ticks']>=4.
    decay=p['pressure_ratio']<=.5 and p['trade_count_ratio']<=.5
    E=impulse and decay
    tags=[]
    if high and small and not confined:tags.append('HIGH_PRESSURE_EXCURSION_RETURN')
    if high and p['directed_progress_ticks']>=4.:tags.append('HIGH_PRESSURE_PROGRESS')
    if x['pressure']<c['current_pressure_q20'] and x['abs_progress']<=2.:tags.append('LOW_PRESSURE_SMALL_NET')
    if impulse and not decay:tags.append('PRIOR_IMPULSE_NO_JOINT_DECAY')
    if decay and not impulse:tags.append('DECAY_WITHOUT_PRIOR_IMPULSE')
    return {'state':'BOTH' if A and E else 'A_ONLY' if A else 'E_ONLY' if E else 'NEITHER','reason':'CLASSIFIED_PROXY','tags':tags}
