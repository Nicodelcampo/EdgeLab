"""Descriptive diagnostic, fixed thinning and filters, clustered day resampling.
All ten dates already inspected: NOT untouched OOS, no P&L or strategy claim.
"""
import csv,json,math,hashlib
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np,pandas as pd
P=Path('/data/analysis/avzvol-expansion');KEYS=['family','origin','mode','endpoint','D','q']
FILTERS=['all','speed_ratio_ge1','inward_imbalance_ge02_coverage80','efficiency_ge03','prior64_inward','corridor_sparse_lt25','confirmed_peak_during_return','fast_inward_flow','fast_inward_flow_sparse']
def num(r,k):
 try:return float(r[k])
 except (ValueError,TypeError):return math.nan

def applies(r):
 speed=num(r,'speed_ratio')>=1;flow=num(r,'return_imbalance_toward')>=.2 and num(r,'quote_coverage')>=.8;sparse=num(r,'prior256_corridor_overlap')<.25
 return {'all':True,'speed_ratio_ge1':speed,'inward_imbalance_ge02_coverage80':flow,'efficiency_ge03':num(r,'return_efficiency')>=.3,'prior64_inward':num(r,'prior64_toward')>0,'corridor_sparse_lt25':sparse,'confirmed_peak_during_return':num(r,'confirmed_peaks_return')>0,'fast_inward_flow':speed and flow,'fast_inward_flow_sparse':speed and flow and sparse}
def main():
 manifest=json.loads((P/'manifest.json').read_text());dates=manifest['event_dates'];train=set(dates[:6]);test=set(dates[6:]);assert len(dates)==10
 # Predeclared primary feature slice D20/40,q50,touch; all modes,origins,families.
 # One earliest observed signal per fixed6250-record bin, no label-based ranking.
 bins={};seen=Counter();dayraw=defaultdict(Counter);rule_raw=defaultdict(Counter);schema=None;events=0
 with (P/'signals-private.csv').open() as f:
  reader=csv.DictReader(f);schema=reader.fieldnames
  for r in reader:
   assert r['session'] in dates;events+=1;k=tuple(r[c] for c in KEYS);rule_raw[k][r['status']]+=1;dayraw[(*k,r['session'])][r['status']]+=1
   if r['endpoint']!='touch' or r['D'] not in ('20','40') or r['q']!='0.5':continue
   bi=int(r['trigger_idx'])//6250;key=(*k,r['session'],bi);current=bins.get(key)
   if current is None or (int(r['trigger_idx']),int(r['anchor_idx']))<(int(current['trigger_idx']),int(current['anchor_idx'])):bins[key]=r
 summaries=list(csv.DictReader((P/'rule-counts.csv').open()));verified=0
 for s in summaries:
  k=tuple(str(s[x]) for x in KEYS)
  # pandas .fillna may serialize D as integer; normalize only declared numeric keys
  k=(*k[:-2],str(int(float(k[-2]))),str(float(k[-1])))
  rr=rule_raw[k]
  for status,n in rr.items():assert int(float(s.get(status,'0')))==n,(k,status)
  assert int(float(s.get('signals','0')))==sum(rr.values());verified+=1
 assert verified==864
 daily=list(csv.DictReader((P/'daily-rule-counts.csv').open()))
 for s in daily:
  k=tuple(s[x] for x in KEYS);k=(*k[:-2],str(int(float(k[-2]))),str(float(k[-1])),s['session']);rr=dayraw[k]
  for status,n in rr.items():assert int(float(s.get(status,'0')))==n
 selected=list(bins.values());del bins
 agg=defaultdict(Counter);days=defaultdict(Counter);scope_rows=[]
 for r in selected:
  key=tuple(r[c] for c in KEYS);which='train6' if r['session'] in train else 'test4'
  for fl,on in applies(r).items():
   if not on:continue
   for segment in ['all10',which]:
    a=agg[(*key,fl,segment)];b=days[(*key,fl,segment,r['session'])]
    for z in (a,b):z['signals']+=1;z[r['status']]+=1
 rng=np.random.default_rng(71204);bootstrap_samples=10000;results=[]
 def row(key,c):
  family,origin,mode,endpoint,d,q,fl,segment=key;dd=dates if segment=='all10' else dates[:6] if segment=='train6' else dates[6:]
  wins=c['TARGET_FIRST'];loss=c['OPPOSITE_FIRST'];n=wins+loss;active=sum(days[(*key,date)]['signals']>0 for date in dd)
  dayw=np.array([days[(*key,date)]['TARGET_FIRST'] for date in dd]);dayn=np.array([days[(*key,date)]['TARGET_FIRST']+days[(*key,date)]['OPPOSITE_FIRST'] for date in dd]);ix=rng.integers(0,len(dd),size=(bootstrap_samples,len(dd)));bw=dayw[ix].sum(axis=1);bn=dayn[ix].sum(axis=1);good=bn>0;boot=bw[good]/bn[good];ci=np.quantile(boot,[.025,.975]) if len(boot) else [math.nan,math.nan]
  return dict(family=family,origin=origin,mode=mode,endpoint=endpoint,D=int(d),q=float(q),filter=fl,segment=segment,signals=c['signals'],resolved=n,target_first=wins,opposite_first=loss,unresolved=c['signals']-n,active_sessions=active,observed_sessions=len(dd),target_percent=100*wins/n if n else math.nan,day_bootstrap_lower_percent=100*ci[0],day_bootstrap_upper_percent=100*ci[1],mean_signals_per_observed_session=c['signals']/len(dd),target_lower_censor_percent=100*wins/c['signals'] if c['signals'] else math.nan,target_upper_censor_percent=100*(wins+c['signals']-n)/c['signals'] if c['signals'] else math.nan)
 for k,c in sorted(agg.items()):results.append(row(k,c))
 out=pd.DataFrame(results);out.to_csv(P/'temporal-thinned-filter-summary.csv',index=False)
 # Day-paired controls and filter deltas, percentile bootstrap conditioned on dates.
 contrasts=[]
 primary=out[(out.segment=='all10')&(out.origin=='real')&(out['filter']=='all')]
 for _,r in primary.iterrows():
  k=(r.family,'real',r['mode'],'touch',str(r.D),str(r.q),'all','all10');c=(*k[:1],'delayed_translated_250bars',*k[2:]);w1=np.array([days[(*k,dt)]['TARGET_FIRST'] for dt in dates]);n1=np.array([days[(*k,dt)]['TARGET_FIRST']+days[(*k,dt)]['OPPOSITE_FIRST'] for dt in dates]);w2=np.array([days[(*c,dt)]['TARGET_FIRST'] for dt in dates]);n2=np.array([days[(*c,dt)]['TARGET_FIRST']+days[(*c,dt)]['OPPOSITE_FIRST'] for dt in dates]);ix=rng.integers(0,10,size=(bootstrap_samples,10));a=n1[ix].sum(axis=1);b=n2[ix].sum(axis=1);ok=(a>0)&(b>0);deltas=100*(w1[ix].sum(axis=1)[ok]/a[ok]-w2[ix].sum(axis=1)[ok]/b[ok]);lo,hi=np.quantile(deltas,[.025,.975]) if len(deltas) else (math.nan,math.nan)
  contrasts.append(dict(family=r.family,mode=r['mode'],D=int(r.D),q=float(r.q),real_resolved=int(n1.sum()),control_resolved=int(n2.sum()),real_minus_control_percentage_points=100*(w1.sum()/n1.sum()-w2.sum()/n2.sum()) if n1.sum() and n2.sum() else math.nan,day_paired_lower=lo,day_paired_upper=hi))
 pd.DataFrame(contrasts).to_csv(P/'paired-control-contrasts.csv',index=False)
 # Honest large-support candidates, no multiplicity-adjusted or untouched-test claim.
 candidate=out[(out.origin=='real')&(out['mode']=='first_D_qualifying')&(out.segment=='all10')&(out.resolved>=100)&(out.active_sessions>=8)].sort_values(['day_bootstrap_lower_percent','resolved'],ascending=False)
 headline=out[(out.origin=='real')&(out['mode']=='first_D_qualifying')&(out.D==20)&(out['filter']=='all')&(out.segment=='all10')].sort_values('family')
 pre=out[(out.origin=='real')&(out['mode']=='first_departure')&(out.D==20)&(out['filter']=='all')&(out.segment=='all10')].sort_values('family')
 rawview=[]
 for s in summaries:
  if s['origin']=='real' and s['endpoint']=='touch' and int(float(s['D']))==20 and float(s['q'])==.5:rawview.append({k:s[k] for k in KEYS+['formations','signals','TARGET_FIRST','OPPOSITE_FIRST']})
 evidence=dict(status='DESCRIPTIVE_EXPANSION_ANALYSIS_COMPLETE',independent_signal_csv_recount='PASS',rule_groups_verified=verified,signals_recounted=events,temporal_thinned_primary_rows=len(selected),primary_scope='touch, D20/40, q50, six families, two modes, two origins',sampling='earliest trigger then earliest birth in fixed6250-derived-record bins per session/rule; NOT independent episodes; can still overlap',bootstrap='10000 resamples of whole observed dates; only10 clusters; exploratory intervals, no familywise guarantee',filters_predeclared=FILTERS,diagnostic_test_already_inspected=True,multiplicity_corrected=False,control_is_not_unconditional_null=True,headlines=headline.to_dict('records'),first_departure=pre.to_dict('records'),raw_primary=rawview,large_support_candidate_descriptive=candidate.head(12).to_dict('records'),paired_control_contrasts=contrasts,all_six_contracts_complete=False,holdout_opened=False,pnl_computed=False,comparison_plan=[dict(grain='detector family',population='same10selecteddates, thinnedD20/q50/touch/first-D-qualifying labels',unit='target-first percent among resolved',finding='real and delayed-translated control rates compared at symmetric barriers',derivation='sum target-first divided by sum resolved, compatible rule definitions',disposition='chart',reason='tests whether high event frequency translates into an increment beyond delayed geometry; descriptive only')])
 (P/'analysis-evidence.json').write_text(json.dumps(evidence,indent=2,allow_nan=True)+'\n')
 print('RECOUNTS',verified,'groups;',events,'signal rows;',len(selected),'temporally thinned primary signals')
 print('HEADLINE',headline[['family','resolved','target_percent','day_bootstrap_lower_percent','day_bootstrap_upper_percent']].to_dict('records'))
 print('CANDIDATES',candidate.head(6)[['family','D','filter','resolved','target_percent','day_bootstrap_lower_percent','day_bootstrap_upper_percent']].to_dict('records'))
if __name__=='__main__':main()
