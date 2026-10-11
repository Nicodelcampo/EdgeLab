"""Post-discovery sensitivity grid; not a fresh independent confirmation.
Occupancy is share of last256 CLOSED tick-built bars overlapping the remaining
price corridor; NOT order-book liquidity or exact volume-at-price.
"""
import csv,json,math,itertools
from collections import defaultdict
from pathlib import Path
import numpy as np,pandas as pd
P=Path('/data/analysis/avzvol-expansion');BINS=[3125,6250,12500,25000];THRESHOLDS=[None,.125,.25,.375,.5,.75];FOCUS='P80_W5_R8_1000_20'
def main():
 m=json.loads((P/'manifest.json').read_text());dates=m['event_dates'];plan=dict(scope='POST_DISCOVERY_SENSITIVITY_NOT_NEW_OOS',families=m['families'],mode='first_D_qualifying',endpoint='touch',distances=[20,40,80],fractions=[.25,.5,.75],fixed_bin_records=BINS,corridor_thresholds=THRESHOLDS,sample_rule='earliest trigger and birth, before applying filter',control='same delayed-translated250bar control',test_already_inspected=True,holdout_opened=False);(P/'corridor-refinement-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
 bins={};rows_seen=0
 with (P/'signals-private.csv').open() as f:
  for r in csv.DictReader(f):
   if r['mode']!='first_D_qualifying' or r['endpoint']!='touch' or r['D'] not in ['20','40','80']:continue
   rows_seen+=1;tr=int(r['trigger_idx']);anchor=int(r['anchor_idx']);occupancy=float(r['prior256_corridor_overlap']) if r['prior256_corridor_overlap'] else math.nan
   base=(r['family'],r['origin'],int(r['D']),float(r['q']),r['session'])
   for size in BINS:
    k=(*base,size,tr//size);old=bins.get(k);val=(tr,anchor,r['status'],occupancy)
    if old is None or val[:2]<old[:2]:bins[k]=val
 counts=defaultdict(lambda:np.zeros(3,np.int64))
 for k,(_,_,status,occupancy) in bins.items():
  family,origin,d,q,date,size,_=k
  for threshold in THRESHOLDS:
   if threshold is not None and not occupancy<threshold:continue
   c=counts[(family,origin,d,q,size,threshold,date)];c[0]+=status=='TARGET_FIRST';c[1]+=status=='OPPOSITE_FIRST';c[2]+=1
 del bins
 groups_with_signals=len(set(k[:-1] for k in counts));names=[f'P{p:g}_W{w}_R{a}_{b}_{c}' for p,w,a,b,c in m['families']];groups=sorted(itertools.product(names,['real','delayed_translated_250bars'],[20,40,80],[.25,.5,.75],BINS,THRESHOLDS),key=str);rng=np.random.default_rng(51389);index=rng.integers(0,10,size=(10000,10));results=[];comparisons=[]
 for group in groups:
  family,origin,d,q,size,threshold=group;arr=np.array([counts[(*group,date)] for date in dates]);wins=arr[:,0];n=arr[:,0]+arr[:,1];bw=wins[index].sum(axis=1);bn=n[index].sum(axis=1);good=bn>0;ci=np.quantile(100*bw[good]/bn[good],[.025,.975]) if good.any() else [math.nan]*2
  for segment,sl in [('all10',slice(None)),('train6',slice(0,6)),('test4',slice(6,None))]:
   a=arr[sl];w=a[:,0].sum();nn=a[:,:2].sum();r=dict(family=family,origin=origin,D=d,q=q,bin_records=size,corridor_threshold='none' if threshold is None else threshold,segment=segment,signals=int(a[:,2].sum()),resolved=int(nn),target_first=int(w),target_percent=100*w/nn if nn else math.nan,active_sessions=int(np.count_nonzero(a[:,2])),observed_sessions=len(a))
   if segment=='all10':r.update(day_lower=ci[0],day_upper=ci[1])
   results.append(r)
  if origin=='real':
   cg=(family,'delayed_translated_250bars',d,q,size,threshold);ca=np.array([counts[(*cg,date)] for date in dates]);cw=ca[:,0];cn=ca[:,:2].sum(axis=1);cbw=cw[index].sum(axis=1);cbn=cn[index].sum(axis=1);ok=(bn>0)&(cbn>0);delta=100*(bw[ok]/bn[ok]-cbw[ok]/cbn[ok]);lo,hi=np.quantile(delta,[.025,.975]) if len(delta) else [math.nan]*2
   comparisons.append(dict(family=family,D=d,q=q,bin_records=size,corridor_threshold='none' if threshold is None else threshold,real_resolved=int(n.sum()),control_resolved=int(cn.sum()),real_minus_control_points=100*(wins.sum()/n.sum()-cw.sum()/cn.sum()) if n.sum() and cn.sum() else math.nan,paired_day_lower=lo,paired_day_upper=hi))
 out=pd.DataFrame(results);out.to_csv(P/'corridor-sensitivity-summary.csv',index=False);co=pd.DataFrame(comparisons);co.to_csv(P/'corridor-sensitivity-controls.csv',index=False)
 focus=out[(out.family==FOCUS)&(out.bin_records==6250)&(out.corridor_threshold==.25)&(out.origin=='real')];b=out[(out.family==FOCUS)&(out.D==40)&(out.q==.5)&(out.corridor_threshold==.25)&(out.segment=='all10')&(out.origin=='real')];c=co[(co.family==FOCUS)&(co.D==40)&(co.q==.5)&(co.corridor_threshold==.25)]
 # Quantify the looked-at family count, rather than treating a selected maximum
 # as one prespecified test. Bootstrap intervals are exploratory, not adjusted.
 evidence=dict(status='POST_DISCOVERY_CORRIDOR_SENSITIVITIES_COMPLETE',input_rows_considered=rows_seen,groups_with_signals=groups_with_signals,all_planned_groups=len(groups),real_control_contrasts=len(comparisons),multiplicity_adjusted=False,independent_confirmation=False,focus_Dq_by_segment=focus.to_dict('records'),focus_sampling_sensitivity=b.to_dict('records'),focus_control_deltas=c.to_dict('records'),all_contracts_complete=False,holdout_opened=False)
 (P/'corridor-refinement-evidence.json').write_text(json.dumps(evidence,indent=2,allow_nan=True)+'\n');print('REFINEMENT',len(groups),'groups;',len(comparisons),'real-control contrasts');print('FOCUS',focus[focus.segment=='all10'][['D','q','resolved','target_percent','day_lower','day_upper']].to_dict('records'));print('BIN_SENSITIVITY',b[['bin_records','resolved','target_percent','day_lower','day_upper']].to_dict('records'));print('CONTROL',c.to_dict('records'))
if __name__=='__main__':main()
