from pathlib import Path
import argparse,json,hashlib,math
from collections import Counter,defaultdict
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();A=a.out;A.mkdir(parents=True,exist_ok=True);R=a.repo
plan=json.loads((Path(__file__).parent/'plan.json').read_text());(A/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));previous=R/'docs/research/avzvol_entry_distance_20261011'
expected={'evidence.json': 'bf6cebb8ccee3113b4276ddfc163d203b87f51b2c6a7977ac0c9abd854eb440f', 'context-support.json': '5f660e6d6d6fe67c2a66b0b39286e175f62827140c716f28bded6889d943f344', 'reach-by-fold.csv': '742ce4e82bc874691064cb75f122e5d23e73decbb0eae2d1b576f6d6d2874001'}
for name,digest in expected.items():
 assert hashlib.sha256((previous/name).read_bytes()).hexdigest()==digest,name
old=json.loads((previous/'evidence.json').read_text());sup=pd.DataFrame(json.loads((previous/'context-support.json').read_text()));frames=[];profiles=[]
cols=['contract','cell','kind','session','t0','te','pos','amp','h','o2','o3a','o3b','mx_h','dir','trend','mom100_h']
for pin in old['plan']['pins']:
 paths=list(a.input_dir.rglob(pin['basename']));assert len(paths)==1;f=paths[0];assert hashlib.sha256(f.read_bytes()).hexdigest()==pin['sha256'];pf=pq.ParquetFile(f);assert pf.metadata.num_rows==pin['rows'];idx=pf.schema_arrow.names.index('session')
 for rg in range(pf.metadata.num_row_groups):
  st=pf.metadata.row_group(rg).column(idx).statistics;assert st and st.has_min_max and st.max<20261001
 d=pq.read_table(f,columns=cols).to_pandas();assert not d.isna().any().any();profiles.append({'basename':f.name,'rows':len(d),'nulls':0,'identity_duplicates_retained':int(d.duplicated(['contract','cell','kind','session','t0']).sum())});frames.append(d)
d=pd.concat(frames,ignore_index=True);assert len(d)==544531;q=d[d.pos.eq(0)&d.te.ge(0)&d.o2.isin([0,1])].copy();assert q.h.gt(0).all() and q.dir.isin([-1,1]).all() and q.trend.isin([-1,0,1]).all();q['delay']=q.te-q.t0;q['range_band']=q.amp/q.h;q['ticks']=np.rint(q.mx_h*q.h).astype(int);assert np.allclose(q.ticks,q.mx_h*q.h,rtol=0,atol=1e-10);assert np.array_equal(q.ticks.ge(q.h),q.o2.eq(1))
mo=np.sign(q.mom100_h);q['context']=np.select([(q.trend==0)|(mo==0),(q.trend==q.dir)&(mo==q.dir),(q.trend==-q.dir)&(mo==-q.dir)],['NEUTRAL_OR_ZERO','BOTH_ALIGNED','BOTH_OPPOSED'],default='MIXED')

def weights(z):
 w=1/(z.groupby(['session','contract','t0']).t0.transform('size').to_numpy(float)*z.groupby(['session','contract']).t0.transform('nunique').to_numpy(float)*z.groupby('session').contract.transform('nunique').to_numpy(float))
 keys=list(z[['session','contract','t0']].itertuples(index=False,name=None));cs=Counter(keys);an=defaultdict(set);ct=defaultdict(set)
 for day,c,t in keys:an[day,c].add(t);ct[day].add(c)
 nw=np.array([1/(cs[k]*len(an[k[:2]])*len(ct[k[0]])) for k in keys]);assert np.allclose(w,nw,rtol=0,atol=1e-12);return w
q['subcontext']=np.select([q.context.eq('MIXED')&(mo==q.dir),q.context.eq('MIXED')&(mo==-q.dir)],['SHORT_ALIGNED_LONG_OPPOSED','SHORT_OPPOSED_LONG_ALIGNED'],default='NOT_MIXED')
records=[];supports=[];ret=[];contracts=[];maxerr=0.0

def measure(z,w,fold,cohort,policy,context,scope,contract=None,total=1,policy_mass=1):
 global maxerr
 mass=math.fsum(w)
 if mass==0:return
 base={'fold':fold,'cohort':cohort,'policy':policy,'context':context,'scope':scope,'contract':contract,'rows':len(z),'anchors':len(z[['session','contract','t0']].drop_duplicates()),'sessions':int(z.session.nunique()),'weight_mass':mass,'coverage_all_exits':mass/total,'coverage_within_policy':mass/policy_mass}
 if scope=='global':supports.append(base)
 for unit,levels in plan['thresholds'].items():
  for level in levels:
   hit=z.ticks.to_numpy()>=(np.full(len(z),level) if unit=='ticks' else np.ceil(z.h.to_numpy()*level-1e-12));rate=float(np.dot(w,hit)/mass)
   oracle=math.fsum(float(ww) for exc,h,ww in zip(z.ticks,z.h,w) if exc >= (level if unit=='ticks' else math.ceil(h*level-1e-12)))/mass;maxerr=max(maxerr,abs(rate-oracle));assert abs(rate-oracle)<1e-12
   row={**base,'unit':unit,'distance':level,'reach_rate':rate};(records if scope=='global' else contracts).append(row)
 if scope=='global':
  r=z.o3a.eq(1).to_numpy();known=r&z.o3b.isin([0,1]).to_numpy();yes=r&z.o3b.eq(1).to_numpy();unknown=r&z.o3b.isin([-1,-2]).to_numpy();rm=math.fsum(w[r]);km=math.fsum(w[known]);ym=math.fsum(w[yes]);um=math.fsum(w[unknown])
  ret.append({**base,'retest_given_exit':rm/mass,'side_given_resolved_retest':None if km==0 else ym/km,'lower_all_retest':None if rm==0 else ym/rm,'upper_all_retest':None if rm==0 else (ym+um)/rm,'unresolved_and_double_rows':int(unknown.sum())})

for fold in old['folds']:
 for cohort in ['real','pseudo']:
  z=q[q.kind.eq(cohort)&q.session.between(fold['test_first'],fold['test_last'])].copy();edges=sup[(sup.fold==fold['fold'])&(sup.cohort==cohort)&sup.bucket.eq('ALL')].training_edges.iloc[0];x=np.searchsorted(edges['exit_delay_bars'],z.delay,side='right');y=np.searchsorted(edges['range_over_band'],z.range_band,side='right');z['bucket']=[f'{i}:{j}' for i,j in zip(x,y)];w=weights(z);total=math.fsum(w)
  for policy,buckets in plan['policies'].items():
   mask=np.ones(len(z),dtype=bool) if buckets is None else z.bucket.isin(buckets).to_numpy();pm=math.fsum(w[mask])
   for context in plan['contexts']:
    cm=mask if context=='ALL' else mask&(z.subcontext.eq(context).to_numpy() if context.startswith('SHORT_') else z.context.eq(context).to_numpy());measure(z.loc[cm],w[cm],fold['fold'],cohort,policy,context,'global',total=total,policy_mass=pm)
  for ct in sorted(z.contract.unique()):
   cz=z[z.contract.eq(ct)].copy();cw=weights(cz);total=math.fsum(cw)
   for policy,buckets in plan['policies'].items():
    mask=np.ones(len(cz),dtype=bool) if buckets is None else cz.bucket.isin(buckets).to_numpy();pm=math.fsum(cw[mask])
    if not pm:continue
    for context in plan['contexts']:
     cm=mask if context=='ALL' else mask&(cz.subcontext.eq(context).to_numpy() if context.startswith('SHORT_') else cz.context.eq(context).to_numpy());measure(cz.loc[cm],cw[cm],fold['fold'],cohort,policy,context,'contract',contract=ct,total=total,policy_mass=pm)
f=pd.DataFrame(records);c=pd.DataFrame(contracts);r=pd.DataFrame(ret);ss=pd.DataFrame(supports)
summary=f.groupby(['cohort','policy','context','unit','distance']).agg(mean_rate=('reach_rate','mean'),min_fold=('reach_rate','min'),max_fold=('reach_rate','max'),folds=('fold','nunique'),mean_coverage=('coverage_all_exits','mean'),mean_within_policy=('coverage_within_policy','mean')).reset_index()
rs=r.groupby(['cohort','policy','context']).agg(retest_rate=('retest_given_exit','mean'),resolved_side_rate=('side_given_resolved_retest','mean'),lower_all_retest=('lower_all_retest','mean'),upper_all_retest=('upper_all_retest','mean')).reset_index()
for name,df in [('reach-by-fold.csv',f),('reach-summary.csv',summary),('reach-by-contract.csv',c),('context-support.csv',ss),('retest-by-fold.csv',r),('retest-summary.csv',rs)]:df.to_csv(A/name,index=False)
for (fold,cohort,policy),g in ss.groupby(['fold','cohort','policy']):
 whole=g[g.context.eq('ALL')].weight_mass.iloc[0];parts=g[g.context.isin(['BOTH_ALIGNED','BOTH_OPPOSED','MIXED','NEUTRAL_OR_ZERO'])].weight_mass.sum();assert abs(whole-parts)<1e-10
 children=g[g.context.str.startswith('SHORT_')].weight_mass.sum();parent=g[g.context.eq('MIXED')].weight_mass.iloc[0];assert abs(children-parent)<1e-10
prior=pd.read_csv(previous/'reach-by-fold.csv');p1=f[(f.policy=='all')&(f.context=='ALL')].merge(prior[prior.bucket.eq('ALL')],on=['fold','cohort','unit','distance'],suffixes=('_new','_old'),validate='one_to_one');assert np.allclose(p1.reach_rate_new,p1.reach_rate_old,rtol=0,atol=1e-12)
p2=f[(f.policy=='fast_wide')&(f.context=='ALL')].merge(prior[prior.bucket.eq('0:2')],on=['fold','cohort','unit','distance'],suffixes=('_new','_old'),validate='one_to_one');assert np.allclose(p2.reach_rate_new,p2.reach_rate_old,rtol=0,atol=1e-12)
ev={'plan':plan,'pins':old['plan']['pins'],'dependencies_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [previous/'evidence.json',previous/'context-support.json',previous/'reach-by-fold.csv']},'profile':profiles,'profile_resolution':'Same exact previously profiled exports, selected16 columns no nulls; duplicates preserved sharing anchor weights, not independent. Labels finite/integer checked; partition/state semantics explicit. No new raw prices.','folds':old['folds'],'summary':summary.to_dict('records'),'retest_summary':rs.to_dict('records'),'max_independent_rate_error':maxerr,'independent_weights_and_reach_verified':True,'context_partition_mass_crossfoot':True,'prior_all_and_fast_wide_rates_reproduced':True,'blind_confirmation':False,'actual_corridor_memory_measured':False,'new_outcomes_or_pnl':False}
(A/'evidence.json').write_text(json.dumps(ev,ensure_ascii=False,indent=2,allow_nan=False))
print('FAST_WIDE 20ticks:');print(summary[(summary.policy=='fast_wide')&(summary.unit=='ticks')&(summary.distance==20)].round(5).to_string(index=False));print('REAL fast_wide by fold20ticks:');print(f[(f.cohort=='real')&(f.policy=='fast_wide')&(f.unit=='ticks')&(f.distance==20)][['fold','context','reach_rate','rows','sessions','anchors','coverage_within_policy']].round(5).to_string(index=False));print('POSTRETEST real fast_wide:');print(rs[(rs.cohort=='real')&(rs.policy=='fast_wide')].round(5).to_string(index=False))
