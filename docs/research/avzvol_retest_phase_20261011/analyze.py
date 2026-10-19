from pathlib import Path
import argparse,json,hashlib,math
from collections import Counter,defaultdict
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
R=args.repo; A=args.out; A.mkdir(parents=True,exist_ok=True);plan=json.loads((Path(__file__).parent/'plan.json').read_text()); (A/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
previous=R/'docs/research/avzvol_entry_distance_20261011'
expected={'evidence.json': 'bf6cebb8ccee3113b4276ddfc163d203b87f51b2c6a7977ac0c9abd854eb440f', 'context-support.json': '5f660e6d6d6fe67c2a66b0b39286e175f62827140c716f28bded6889d943f344'}
for name,digest in expected.items():
 assert hashlib.sha256((previous/name).read_bytes()).hexdigest()==digest,name
e=json.loads((previous/'evidence.json').read_text());support=pd.DataFrame(json.loads((previous/'context-support.json').read_text()));frames=[];profile=[]
for pin in e['plan']['pins']:
 paths=list(args.input_dir.rglob(pin['basename']));assert len(paths)==1;p=paths[0];assert hashlib.sha256(p.read_bytes()).hexdigest()==pin['sha256'];pf=pq.ParquetFile(p);assert pf.metadata.num_rows==pin['rows'];idx=pf.schema_arrow.names.index('session')
 for rg in range(pf.metadata.num_row_groups):
  st=pf.metadata.row_group(rg).column(idx).statistics;assert st and st.has_min_max and st.max<20261001
 d=pq.read_table(p,columns=['contract','cell','kind','session','t0','te','pos','amp','h','o2','o3a','o3b']).to_pandas();assert not d.isna().any().any();assert set(d.o3a)<={-1,0,1} and set(d.o3b)<={-2,-1,0,1};profile.append({'file':p.name,'rows':len(d),'duplicate_identity_rows':int(d.duplicated(['contract','cell','kind','session','t0']).sum()),'nulls':0});frames.append(d)
d=pd.concat(frames,ignore_index=True);assert len(d)==544531;q=d[d.pos.eq(0)&d.te.ge(0)].copy();assert q.o3a.isin([0,1]).all() and q.h.gt(0).all();assert q.loc[q.o3a.eq(0),'o3b'].eq(-1).all();q['delay']=q.te-q.t0;q['range_band']=q.amp/q.h
q['state']=np.select([q.o3a.eq(0),q.o3b.eq(1),q.o3b.eq(0),q.o3b.eq(-2)],plan['states'][:4],default='unresolved_after_retest')
records=[];contract_records=[];oracle_error=0.0

def weights(z):
 sizes=z.groupby(['session','contract','t0']).t0.transform('size').to_numpy(float);anchors=z.groupby(['session','contract']).t0.transform('nunique').to_numpy(float);cts=z.groupby('session').contract.transform('nunique').to_numpy(float);w=1/(sizes*anchors*cts)
 keys=list(z[['session','contract','t0']].itertuples(index=False,name=None));cs=Counter(keys);an=defaultdict(set);ct=defaultdict(set)
 for day,c,t in keys:an[day,c].add(t);ct[day].add(c)
 nw=np.array([1/(cs[k]*len(an[k[:2]])*len(ct[k[0]])) for k in keys]);assert np.allclose(w,nw,rtol=0,atol=1e-12);return w

def metrics(z,w,fold,cohort,policy,scope,contract=None):
 global oracle_error
 mass=math.fsum(w);assert mass>0;states={s:float(np.dot(w,z.state.eq(s).to_numpy())) for s in plan['states']}
 direct={s:math.fsum(float(weight) for state,weight in zip(z.state,w) if state==s) for s in plan['states']}
 for s in states:oracle_error=max(oracle_error,abs(states[s]-direct[s]));assert abs(states[s]-direct[s])<1e-10
 assert abs(math.fsum(states.values())-mass)<1e-10
 ret=mass-states['no_observed_retest'];resolved=states['exit_side_first']+states['opposite_side_first'];amb=states['same_bar_both']+states['unresolved_after_retest']
 row={'fold':fold,'cohort':cohort,'policy':policy,'scope':scope,'contract':contract,'rows':len(z),'anchors':len(z[['session','contract','t0']].drop_duplicates()),'sessions':int(z.session.nunique()),'weight_mass':mass,'observed_retest_rate':ret/mass,'exit_side_given_resolved_retest':None if resolved==0 else states['exit_side_first']/resolved,'exit_side_lower_all_retests':None if ret==0 else states['exit_side_first']/ret,'exit_side_upper_all_retests':None if ret==0 else (states['exit_side_first']+amb)/ret,'ambiguous_unresolved_given_retest':None if ret==0 else amb/ret,'unresolved_o2_rows':int((~z.o2.isin([0,1])).sum())}
 for s in states:row[s+'_share_all_exits']=states[s]/mass;row[s+'_rows']=int(z.state.eq(s).sum())
 return row

for fold in e['folds']:
 for cohort in ['real','pseudo']:
  z=q[q.kind.eq(cohort)&q.session.between(fold['test_first'],fold['test_last'])].copy();edges=support[(support.fold==fold['fold'])&(support.cohort==cohort)&support.bucket.eq('ALL')].training_edges.iloc[0]
  x=np.searchsorted(edges['exit_delay_bars'],z.delay,side='right');y=np.searchsorted(edges['range_over_band'],z.range_band,side='right');z['bucket']=[f'{a}:{b}' for a,b in zip(x,y)];w=weights(z);total=math.fsum(w)
  for policy,buckets in plan['policies'].items():
   mask=np.ones(len(z),dtype=bool) if buckets is None else z.bucket.isin(buckets).to_numpy();r=metrics(z.loc[mask],w[mask],fold['fold'],cohort,policy,'global');r['coverage']=r['weight_mass']/total;records.append(r)
  for ct in sorted(z.contract.unique()):
   cz=z[z.contract.eq(ct)].copy();cw=weights(cz);cmass=math.fsum(cw)
   for policy,buckets in plan['policies'].items():
    mask=np.ones(len(cz),dtype=bool) if buckets is None else cz.bucket.isin(buckets).to_numpy()
    if not mask.any():continue
    r=metrics(cz.loc[mask],cw[mask],fold['fold'],cohort,policy,'contract',ct);r['coverage']=r['weight_mass']/cmass;contract_records.append(r)
f=pd.DataFrame(records);c=pd.DataFrame(contract_records)
metrics_cols=['coverage','observed_retest_rate','exit_side_given_resolved_retest','exit_side_lower_all_retests','exit_side_upper_all_retests','ambiguous_unresolved_given_retest']+[s+'_share_all_exits' for s in plan['states']]
summary=f.groupby(['cohort','policy'])[metrics_cols].mean().reset_index();assert np.allclose(summary[[s+'_share_all_exits' for s in plan['states']]].sum(axis=1),1)
gaps=[]
for (fold,cohort),g in f.groupby(['fold','cohort']):
 r=g.set_index('policy')
 for a,b in [('wide','all'),('fast','all'),('fast_wide','wide'),('fast_wide','all')]:
  for metric in ['observed_retest_rate','exit_side_given_resolved_retest']:
   gaps.append({'fold':int(fold),'cohort':cohort,'comparison':a+' minus '+b,'metric':metric,'gap_pp':float((r.loc[a,metric]-r.loc[b,metric])*100)})
for name,df in [('phase-by-fold.csv',f),('phase-summary.csv',summary),('phase-by-contract.csv',c),('phase-gaps.csv',pd.DataFrame(gaps))]:df.to_csv(A/name,index=False)
ledger=[]
for kind in ['real','pseudo']:
 v=d[d.kind.eq(kind)&d.pos.eq(0)];ledger.append({'cohort':kind,'inside_rows':len(v),'no_exit_rows':int(v.te.lt(0).sum()),'observed_exit_rows':int(v.te.ge(0).sum()),'unresolved_o2_retained_rows':int((v.te.ge(0)&~v.o2.isin([0,1])).sum())})
ev={'plan':plan,'profile':profile,'profile_resolution':'Same six exact previously profiled raw exports; identity duplicates retained sharing anchor weight, not independent. Label codes validated, no nulls; t0/te bar indices not dates; unresolved outcomes NOT dropped as losses. Raw grain event x cell.','ledger':ledger,'folds':e['folds'],'summaries':summary.to_dict('records'),'gaps':gaps,'pins':e['plan']['pins'],'dependencies_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [previous/'evidence.json',previous/'context-support.json']},'independent_counter_weights_and_state_mass_verified':True,'max_state_mass_oracle_error':oracle_error,'state_shares_crossfoot':True,'new_raw_price_outcomes_or_profit':False,'blind_confirmation':False,'comparison_plan':[{'question':'Exit context: return frequency versus side after return','grain':'policy x mutually exclusive state','population':'all observed exits; nested policy populations separate rows','unit':'state share percent','finding':'All5 states retained, no-observed-return separated from unresolved retest','disposition':'chart','reason':'One 100% horizontal state composition; native attachment unavailable, analysis delivered with explicit limitation'}, {'question':'Does continuation context transfer to bounce?','grain':'policy x conditional endpoint,3 prior exposed blocks','population':'resolved retests for side rate; all retests for bounds; all exits for return','unit':'percent, pp gaps','disposition':'table','reason':'Keep denominator changes and all uncertain cases visible'}, {'question':'Do dates/contracts/controls reverse conclusions?','grain':'fold and supported contract x cohort','population':'all6 source contracts,4test-supported contracts, policies kept','unit':'percent','disposition':'table','reason':'Inspect all supported groups before claiming transferability'}]}
(A/'evidence.json').write_text(json.dumps(ev,ensure_ascii=False,indent=2,allow_nan=False))
print(summary[['cohort','policy','coverage','observed_retest_rate','exit_side_given_resolved_retest','exit_side_lower_all_retests','exit_side_upper_all_retests','ambiguous_unresolved_given_retest']].round(6).to_string(index=False));print('BY FOLD real all and fast_wide');print(f[(f.cohort=='real')&f.policy.isin(['all','fast_wide'])][['fold','policy','observed_retest_rate','exit_side_given_resolved_retest','exit_side_lower_all_retests','exit_side_upper_all_retests']].round(6).to_string(index=False))
