"""Fixed primary replication and secondary neighbors; whole-day uncertainty.
Primary success is not declared from a selected best neighboring cell.
"""
import csv,json,math,itertools
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np,pandas as pd
P=Path('/data/analysis/avzvol-replication-rest/combined');BIN=[6250,25000];THRESHOLDS=[None,.25]
def sanitize(x):
 if isinstance(x,dict):return {k:sanitize(v) for k,v in x.items()}
 if isinstance(x,list):return [sanitize(v) for v in x]
 if isinstance(x,float) and not math.isfinite(x):return None
 return x

def main():
 m=json.loads((P/'manifest.json').read_text());raw_counts=defaultdict(Counter);bins={};signals=0
 for contract in m['contracts']:
  with (P/contract/'signals-private.csv').open() as f:
   for r in csv.DictReader(f):
    assert r['session'] in m['event_dates'][contract];key=(contract,r['origin'],int(r['D']),float(r['q']));raw_counts[key][r['status']]+=1;signals+=1;tr=int(r['trigger_idx']);anchor=int(r['anchor_idx']);o=float(r['occupancy']) if r['occupancy'] else math.nan
    for size in BIN:
     k=(*key,r['session'],size,tr//size);old=bins.get(k);v=(tr,anchor,r['status'],o)
     if old is None or v[:2]<old[:2]:bins[k]=v
 summaries=list(csv.DictReader((P/'rule-counts.csv').open()))
 for s in summaries:
  k=(s['contract'],s['origin'],int(s['D']),float(s['q']));c=raw_counts[k]
  assert sum(c.values())==int(float(s['signals']))
  for status,n in c.items():assert n==int(float(s[status]))
 daily=defaultdict(lambda:np.zeros(3,np.int64))
 for k,(_,_,status,occupancy) in bins.items():
  contract,origin,d,q,date,size,_=k
  for threshold in THRESHOLDS:
   if threshold is not None and not occupancy<threshold:continue
   c=daily[(contract,origin,d,q,size,threshold,date)];c[0]+=status=='TARGET_FIRST';c[1]+=status=='OPPOSITE_FIRST';c[2]+=1
 del bins
 groups=list(itertools.product(m['contracts'],m['origins'],m['D'],m['q'],BIN,THRESHOLDS));rng=np.random.default_rng(91217);bootstrap={c:rng.integers(0,len(m['event_dates'][c]),size=(20000,len(m['event_dates'][c]))) for c in m['contracts']};rows=[];contrast=[];dayrows=[]
 for k in groups:
  contract,origin,d,q,size,threshold=k;dates=m['event_dates'][contract];a=np.array([daily[(*k,date)] for date in dates]);w=a[:,0];n=a[:,:2].sum(axis=1);sig=a[:,2];ix=bootstrap[contract];bw=w[ix].sum(axis=1);bn=n[ix].sum(axis=1);good=bn>0;ci=np.quantile(100*bw[good]/bn[good],[.025,.975]) if good.any() else [math.nan]*2;unresolved=int(sig.sum()-n.sum())
  r=dict(contract=contract,origin=origin,D=d,q=q,bin_records=size,occupancy_lt='none' if threshold is None else threshold,signals=int(sig.sum()),resolved=int(n.sum()),target_first=int(w.sum()),opposite_first=int((n-w).sum()),unresolved=unresolved,active_dates=int(np.count_nonzero(sig)),observed_dates=len(dates),target_percent=100*w.sum()/n.sum() if n.sum() else math.nan,day_lower=ci[0],day_upper=ci[1],censor_lower=100*w.sum()/sig.sum() if sig.sum() else math.nan,censor_upper=100*(w.sum()+unresolved)/sig.sum() if sig.sum() else math.nan);rows.append(r)
  for date,z in zip(dates,a):dayrows.append({**{kk:r[kk] for kk in ['contract','origin','D','q','bin_records','occupancy_lt']},'session':date,'wins':int(z[0]),'losses':int(z[1]),'signals':int(z[2])})
  if origin=='real_racimo':
   for control in m['origins'][1:]:
    b=np.array([daily[(contract,control,d,q,size,threshold,date)] for date in dates]);cw=b[:,0];cn=b[:,:2].sum(axis=1);cbw=cw[ix].sum(axis=1);cbn=cn[ix].sum(axis=1);ok=(bn>0)&(cbn>0);delta=100*(bw[ok]/bn[ok]-cbw[ok]/cbn[ok]);lo,hi=np.quantile(delta,[.025,.975]) if len(delta) else [math.nan]*2
    contrast.append(dict(contract=contract,control=control,D=d,q=q,bin_records=size,occupancy_lt='none' if threshold is None else threshold,real_resolved=int(n.sum()),control_resolved=int(cn.sum()),real_minus_control_points=100*(w.sum()/n.sum()-cw.sum()/cn.sum()) if n.sum() and cn.sum() else math.nan,paired_day_lower=lo,paired_day_upper=hi))
 out=pd.DataFrame(rows);co=pd.DataFrame(contrast);pd.DataFrame(dayrows).to_csv(P/'thinned-daily-counts.csv',index=False);out.to_csv(P/'thinned-summary.csv',index=False);co.to_csv(P/'paired-contrasts.csv',index=False)
 primary=out[(out.D==40)&(out.q==.5)&(out.bin_records==6250)&(out.occupancy_lt==.25)];first=primary[(primary.contract=='MNQ_12-26')&(primary.origin=='real_racimo')].iloc[0];assert (int(first.target_first),int(first.opposite_first),int(first.unresolved))==(255,212,9)
 cp=co[(co.D==40)&(co.q==.5)&(co.bin_records==6250)&(co.occupancy_lt==.25)]
 criteria=json.loads((P/'replication-criteria.json').read_text());checks={}
 for c in m['contracts']:
  if c=='MNQ_12-26':continue
  rep=primary[(primary.contract==c)&(primary.origin=='real_racimo')].iloc[0];inc=cp[(cp.contract==c)&cp.control.str.startswith('clock_price')]
  checks[c]=dict(min_resolved200=bool(rep.resolved>=200),at_least20_active_dates=bool(rep.active_dates>=20),target_percent_above50=bool(rep.target_percent>50),day_lower_above50=bool(rep.day_lower>50),all_three_price_reference_increment_lower_above0=bool((inc.paired_day_lower>0).all()))
 evidence=dict(status='REPLICATION_ANALYZED',rule_groups_recounted=len(summaries),raw_signal_rows_recounted=signals,original_primary_counts_recounted=True,original_tick_labels_reused_not_new_replication=True,thinned_groups=len(rows),control_contrasts=len(contrast),primary=primary.to_dict('records'),primary_contrasts=cp.to_dict('records'),replication_criteria=criteria,criteria_outcomes=checks,primary_replication_pass=all(all(v.values()) for v in checks.values()),contract_pass={c:all(v.values()) for c,v in checks.items()},source_certified=False,holdout_opened=False,pnl_computed=False,multiplicity_corrected=False,bootstrap='20000 whole-date resamples within each contract; fixed parameters; not randomised intervention or corrected FWER',control_caveat='price-only references have fixed centered widths, not exact geometry matching; covariate distributions may differ',comparison_plan=[dict(grain='contract by origin',population='fixedD40/q50/touch/first-D-qualified/corridor<25%/bin6250 labels among resolved selected-date signals',unit='target-first percent',finding='replication and price-only references compare fixed combination without retuning',derivation='wins/resolved*100',disposition='chart',reason='tests generalization and whether context alone can reproduce candidate effect')])
 (P/'analysis-evidence.json').write_text(json.dumps(sanitize(evidence),indent=2,allow_nan=False)+'\n');print('PRIMARY_REAL',primary[primary.origin.eq('real_racimo')][['contract','resolved','target_percent','day_lower','day_upper']].to_dict('records'));print('CRITERIA',checks)
if __name__=='__main__':main()
