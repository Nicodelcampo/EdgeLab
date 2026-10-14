from pathlib import Path
import json,hashlib,math
from collections import Counter,defaultdict
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import argparse
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
A=args.out;A.mkdir(parents=True,exist_ok=True); R=args.repo; I=R/'docs/research/avzvol_entry_distance_20261011'
expected_inputs={'evidence.json': 'bf6cebb8ccee3113b4276ddfc163d203b87f51b2c6a7977ac0c9abd854eb440f', 'reach-by-fold.csv': '742ce4e82bc874691064cb75f122e5d23e73decbb0eae2d1b576f6d6d2874001', 'context-support.json': '5f660e6d6d6fe67c2a66b0b39286e175f62827140c716f28bded6889d943f344'}
for name,digest in expected_inputs.items():
 assert hashlib.sha256((I/name).read_bytes()).hexdigest()==digest,name
plan=json.loads((Path(__file__).parent/'plan.json').read_text()); (A/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)); prev=json.loads((R/'docs/research/avzvol_entry_distance_20261011/evidence.json').read_text())
f=pd.read_csv(I/'reach-by-fold.csv'); sup=pd.DataFrame(json.loads((I/'context-support.json').read_text()))
assert len(f)==660 and not f.isna().any().any() and not f.duplicated(['fold','cohort','bucket','unit','distance']).any()
assert all(f.reach_rate.between(0,1))
rows=[]
for (fold,cohort,unit,dist),g in f.groupby(['fold','cohort','unit','distance']):
 for policy,buckets in plan['policies'].items():
  b=['ALL'] if buckets is None else buckets
  z=g[g.bucket.isin(b)].merge(sup[['fold','cohort','bucket','weight_mass']],on=['fold','cohort','bucket'],validate='one_to_one'); assert len(z)==len(b)
  mass=math.fsum(z.weight_mass); total=float(sup[(sup.fold==fold)&(sup.cohort==cohort)&(sup.bucket=='ALL')].weight_mass.iloc[0])
  rate=math.fsum(float(a)*float(w) for a,w in zip(z.reach_rate,z.weight_mass))/mass
  rows.append(dict(fold=int(fold),cohort=cohort,policy=policy,unit=unit,distance=float(dist),reach_rate=rate,coverage=mass/total,weight_mass=mass,rows=int(z.rows.sum())))
agg=pd.DataFrame(rows); frames=[]
for pin in prev['plan']['pins']:
 matches=list(args.input_dir.rglob(pin['basename'])); assert len(matches)==1
 p=matches[0]; assert hashlib.sha256(p.read_bytes()).hexdigest()==pin['sha256']
 d=pq.read_table(p,columns=['contract','cell','kind','session','t0','te','pos','o2','amp','h','mx_h']).to_pandas(); assert len(d)==pin['rows'] and not d.isna().any().any();frames.append(d)
raw=pd.concat(frames,ignore_index=True);q=raw[raw.pos.eq(0)&raw.te.ge(0)&raw.o2.isin([0,1])].copy()
q['delay']=q.te-q.t0;q['range_band']=q.amp/q.h;q['ticks']=np.rint(q.mx_h*q.h).astype(int)
assert np.allclose(q.ticks,q.mx_h*q.h,rtol=0,atol=1e-10)
maxerr=0; checks=[]
for fold in prev['folds']:
 for cohort in ['real','pseudo']:
  z=q[q.kind.eq(cohort)&q.session.between(fold['test_first'],fold['test_last'])].copy()
  edges=sup[(sup.fold==fold['fold'])&(sup.cohort==cohort)&sup.bucket.eq('ALL')].training_edges.iloc[0]
  x=np.searchsorted(edges['exit_delay_bars'],z.delay,side='right');y=np.searchsorted(edges['range_over_band'],z.range_band,side='right')
  z['bucket']=[f'{a}:{b}' for a,b in zip(x,y)]
  keys=list(z[['session','contract','t0']].itertuples(index=False,name=None));counts=Counter(keys);anchors=defaultdict(set);contracts=defaultdict(set)
  for day,ct,t in keys: anchors[day,ct].add(t);contracts[day].add(ct)
  w=np.array([1/(counts[k]*len(anchors[k[:2]])*len(contracts[k[0]])) for k in keys]);total=math.fsum(w)
  for policy,buckets in plan['policies'].items():
   mask=np.ones(len(z),dtype=bool) if buckets is None else z.bucket.isin(buckets).to_numpy();zz=z.loc[mask];ww=w[mask];mass=math.fsum(ww)
   for unit,levels in plan['units'].items():
    for dist in levels:
     rate=math.fsum(float(weight) for exc,h,weight in zip(zz.ticks,zz.h,ww) if exc >= (dist if unit=='ticks' else math.ceil(h*dist-1e-12)))/mass
     a=agg[(agg.fold==fold['fold'])&(agg.cohort==cohort)&(agg.policy==policy)&(agg.unit==unit)&(agg.distance==dist)].iloc[0]
     err=abs(rate-a.reach_rate);maxerr=max(err,maxerr);assert err<1e-12 and a.rows==len(zz);assert abs(a.coverage-mass/total)<1e-12
  checks.append({'fold':fold['fold'],'cohort':cohort,'all_rates_and_policy_support_match_raw':True})
summary=agg.groupby(['cohort','policy','unit','distance']).agg(mean_rate=('reach_rate','mean'),min_rate=('reach_rate','min'),max_rate=('reach_rate','max'),mean_coverage=('coverage','mean')).reset_index()
gaps=[]
for (fold,cohort,unit,dist),g in agg.groupby(['fold','cohort','unit','distance']):
 r=g.set_index('policy').reach_rate
 for a,b in [('wide','all'),('fast','all'),('fast_wide','wide'),('fast_wide','medium_wide'),('fast_wide','slow_wide')]: gaps.append(dict(fold=int(fold),cohort=cohort,unit=unit,distance=float(dist),comparison=a+' minus '+b,gap_pp=float((r[a]-r[b])*100)))
gaps=pd.DataFrame(gaps)
lookup=agg[agg.policy.eq('all')][['fold','cohort','unit','distance','reach_rate']].rename(columns={'reach_rate':'all_reach'})
agg=agg.merge(lookup,on=['fold','cohort','unit','distance'],validate='many_to_one');agg['joint_mass_fraction']=agg.coverage*agg.reach_rate;agg['share_of_all_reaching']=agg.joint_mass_fraction/agg.all_reach
assert (agg.share_of_all_reaching<=1+1e-12).all()
capture=agg.groupby(['cohort','policy','unit','distance']).agg(mean_joint_fraction=('joint_mass_fraction','mean'),mean_share_of_all_reaching=('share_of_all_reaching','mean')).reset_index();summary=summary.merge(capture,on=['cohort','policy','unit','distance'],validate='one_to_one')
for name,df in [('policy-by-fold.csv',agg),('policy-summary.csv',summary),('gaps-by-fold.csv',gaps)]:df.to_csv(A/name,index=False)
e={'plan':plan,'input_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [I/'reach-by-fold.csv',I/'context-support.json']},'raw_pins':prev['plan']['pins'],'raw_rows':len(raw),'profile_resolution':'Profiler date hint is refuted: bucket values like 0:2 are categorical tercile identifiers, not dates. Profiler daily sum hints are invalid because metric rows repeat denominators and groups overlap; never sum rows/sessions across thresholds. policy and bucket rows overlap across distances by design, not independent events; rows is event-cell count; source CSV unique at declared metric grain; raw same six previously profiled exports, no source change','checks':checks,'max_independent_rate_error':maxerr,'summaries':summary.to_dict('records'),'gaps':gaps.to_dict('records'),'no_new_price_outcomes_or_profit':True}
r=summary[(summary.cohort=='real')&(summary.unit=='ticks')].pivot(index='policy',columns='distance',values='mean_rate')*100
print(r.round(2).to_string());print('COVERAGE',summary[(summary.cohort=='real')&(summary.unit=='ticks')&(summary.distance==20)][['policy','mean_coverage']].to_string(index=False))
print('INCREMENTAL SPEED within wide:');print(gaps[(gaps.cohort=='real')&(gaps.unit=='ticks')&(gaps.comparison=='fast_wide minus wide')].to_string(index=False))
e['comparison_plan']=[{'question':'Does fast exit add reach beyond wide range alone?','grain':'policy x fixed-tick threshold, equal mean of3 prior blocks','population':'eligible resolved exits, nested policies, real cohort','unit':'reach percent','derivation':'weight-mass recombination of prior buckets, verified from raw','finding':'computed in policy summary; no winning-policy promotion','disposition':'chart','reason':'Four overlapping policies compared without stacking; preserve all four thresholds'}, {'question':'What is coverage and temporal reversal?','grain':'policy and fold x threshold','population':'same eligible cases','unit':'coverage percent; gap percentage points','disposition':'table','reason':'Coverage is not fills; keep any negative within-block incremental effect'}, {'question':'Do controls replicate and do wide speed terciles differ?','grain':'cohort and speed bucket within wide','population':'real/pseudo separately','unit':'reach percent','disposition':'table','reason':'Retain counterevidence to zone-specific mechanism; no additional fitted recipes'}]
conditional=[]
for (fold,cohort,policy),g in agg[agg.unit.eq('h')].groupby(['fold','cohort','policy']):
 rates=g.set_index('distance').reach_rate
 for offset in [0,.25,.5,.75]:
  denom=1.0 if offset==0 else float(rates.loc[offset]);numer=float(rates.loc[offset+.25])
  assert 0<numer<=denom
  conditional.append(dict(fold=int(fold),cohort=cohort,policy=policy,offset_h=offset,additional_distance_h=.25,all_case_joint_reach=numer,level_reach=denom,conditional_path_reach=numer/denom))
conditional=pd.DataFrame(conditional); conditional.to_csv(A/'conditional-path-reach.csv',index=False)
e['conditional_path_summary']=conditional.groupby(['cohort','policy','offset_h']).agg(mean_conditional=('conditional_path_reach','mean'),mean_all_case_joint=('all_case_joint_reach','mean'),mean_level_reach=('level_reach','mean')).reset_index().to_dict('records')
e['conditional_interpretation']='Retrospective nested maximum events, NOT actual filled trades or probability of success after an executable entry. Falling all-case reach as threshold increases is tautological, not evidence that late filled trades have worse expectancy. These ratios have different denominator than prior all-case scenarios.'
e['comparison_plan'].append({'question':'Does falling all-case distance coverage imply late entries are worse?','grain':'prior block x reached excursion level','population':'retrospective paths reaching each level, not trades','unit':'conditional path-reach percent versus all-case joint reach','finding':'Compute changing denominator explicitly; no entry-time or fill comparison exists','disposition':'table','reason':'Four offsets are a compact lookup; do not imply a trading win-rate'})
print('CONDITIONAL PATHS',pd.DataFrame(e['conditional_path_summary']).query("cohort=='real' and policy=='fast_wide'").round(5).to_string(index=False))
(A/'evidence.json').write_text(json.dumps(e,indent=2,ensure_ascii=False,allow_nan=False))
labels={'all':'Todos','fast':'Sólo salida rápida','wide':'Sólo rango amplio','fast_wide':'Rápida + amplio'}
spec={'version':1,'form':'multiline','title':'¿La salida rápida agrega recorrido al rango amplio?','aside':'Alcance desde el borde, no win-rate; media de3 bloques ya inspeccionados','labels':['5 ticks','10 ticks','20 ticks','40 ticks'],'axis':{'zero':True,'cap':100},'series':[{'label':label,'valueKind':'percent','role':'subject' if k=='fast_wide' else 'base','data':[float(r.loc[k,d]) for d in [5,10,20,40]]} for k,label in labels.items()]}
(A/'chart-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2))
