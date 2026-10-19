"""Exploratory effects: fixed primary geometry; no selection of winning cells."""
import os,json,csv,math,itertools,gzip
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np,pandas as pd
P=Path(os.environ['REPLICATION_ROOT']);C=os.environ['REPLICATION_CONTRACT'];m=json.load(open(P/'manifest.json'));rng=np.random.default_rng(17331);dates=m['event_dates'];ix=rng.integers(0,len(dates),size=(10000,len(dates)));SIGNAL=P/'signals-private.csv';SIGNAL=SIGNAL if SIGNAL.exists() else P/'signals-private.csv.gz';count=pd.read_csv(P/'rule-counts.csv');keys=['family','origin','landmark','D','q','endpoint'];ind=Counter();parts=[]
assert m.get('feature_schema_version')==2 or (P/'schema-repair-evidence.json').exists(), 'UNVERIFIED_FEATURE_SCHEMA'
from feature_schema import validate
for chunk in pd.read_csv(SIGNAL,chunksize=100000):
 assert chunk.hour.between(0,23).all() and chunk.visits1.notna().all() and (chunk.visits5<=chunk.visits1).all(), 'INVALID_FEATURE_SCHEMA'
 for row in chunk.head(2).to_dict('records'):validate(row)
 ind.update(chunk.groupby(keys,dropna=False).size().to_dict());h=chunk[chunk.family.eq('P80_W5_R18_2000_20')&chunk.D.eq(40)&chunk.q.eq(.5)]
 if len(h):parts.append(h.copy())
s=pd.concat(parts,ignore_index=True) if parts else pd.read_csv(SIGNAL,nrows=0)
for r in count.to_dict('records'):assert ind.get(tuple(r[k] for k in keys),0)==int(r.get('signals',0))
# Independent CSV streaming primary thinning; dictionary vs stable pandas sort/groupby.
best={}
with (SIGNAL.open() if SIGNAL.suffix!='.gz' else gzip.open(SIGNAL,'rt')) as f:
 for r in csv.DictReader(f):
  if r['family']!='P80_W5_R18_2000_20' or int(r['D'])!=40 or float(r['q'])!=.5:continue
  k=(r['origin'],int(r['landmark']),int(r['endpoint']),r['session'],int(r['trigger_idx'])//6250);v=(int(r['trigger_idx']),int(r['zone_id']))
  if k not in best or v<best[k][0]:best[k]=(v,r)
t=s[s.family.eq('P80_W5_R18_2000_20')&s.D.eq(40)&s.q.eq(.5)].copy();t['bin']=t.trigger_idx//6250;t=t.sort_values(['trigger_idx','zone_id'],kind='stable').groupby(['origin','landmark','endpoint','session','bin'],sort=False).head(1);assert {(r.origin,int(r.landmark),int(r.endpoint),r.session,int(r.bin)):(int(r.trigger_idx),int(r.zone_id)) for r in t.itertuples()}=={k:v[0] for k,v in best.items()};del best,s
# Frozen birth identity dedup is a sensitivity, not future-based selection.
rows=[];daily=[];thin=t.copy();thin.to_csv(P/'primary-thinned-private.csv',index=False)
def safe(x):
 if isinstance(x,dict):return {k:safe(v) for k,v in x.items()}
 if isinstance(x,list):return [safe(v) for v in x]
 if isinstance(x,float) and not math.isfinite(x):return None
 return x
for dedup in ['all','dedup75','dedup50']:
 b=t if dedup=='all' else t[t[dedup].eq(1)]
 for origin,age,ep,definition in itertools.product(m['origins'],m['landmarks'],[0,1,2],['visits1','visits5','visits_clock10s']):
  g=b[b.origin.eq(origin)&b.landmark.eq(age)&b.endpoint.eq(ep)].copy();g['visits_group']=pd.cut(g[definition],[-1,0,1,4,np.inf],labels=['0','1','2-4','5+']).astype(str);g['speed_group']=np.where(g.speed_ratio.isna(),'unknown',np.where(g.speed_ratio>=1,'return_faster','return_slower'))
  for visits,speed,gap in itertools.product(['all','0','1','2-4','5+'],['all','return_faster','return_slower'],['observed','gap_free']):
   h=g
   if visits!='all':h=h[h.visits_group.eq(visits)]
   if speed!='all':h=h[h.speed_group.eq(speed)]
   if gap=='gap_free':h=h[h.prior_gap_count.eq(0)]
   d=np.zeros((len(dates),3),np.int64)
   for j,date in enumerate(dates):
    hh=h[h.session.eq(date)];d[j]=[hh.status.eq('TARGET_FIRST').sum(),hh.status.eq('OPPOSITE_FIRST').sum(),len(hh)]
   w=int(d[:,0].sum());l=int(d[:,1].sum());n=w+l;sig=int(d[:,2].sum());bw=d[ix,0].sum(axis=1);bn=d[ix,:2].sum(axis=(1,2));ok=bn>0;ci=np.quantile(100*bw[ok]/bn[ok],[.025,.975]) if ok.any() else [np.nan,np.nan];rows.append(dict(contract=C,dedup=dedup,origin=origin,landmark=age,endpoint=ep,visit_definition=definition,visits_group=visits,speed_group=speed,gap_policy=gap,signals=sig,resolved=n,target_first=w,opposite_first=l,unresolved=sig-n,active_dates=int(np.count_nonzero(d[:,2])),observed_dates=len(dates),target_percent=100*w/n if n else np.nan,day_lower=ci[0],day_upper=ci[1]))
result=pd.DataFrame(rows);result.to_csv(P/'primary-effects.csv',index=False)
# Common-support comparison only: same session, age landmark, endpoint, hour bucket,
# observed pretrigger256-bar price span and remaining distance bucket. No causal claim.
matched=[]
for age,ep in itertools.product([2000,3000],[0,1,2]):
 g=t[t.landmark.eq(age)&t.endpoint.eq(ep)&t.dedup75.eq(1)&t.status.isin(['TARGET_FIRST','OPPOSITE_FIRST'])].copy();g['hour_bucket']=g.hour//3;g['span_bucket']=np.minimum(g.volatility256_ticks//40,4);g['remaining_bucket']=np.minimum(g.remaining_ticks//10,8);k=['session','hour_bucket','span_bucket','remaining_bucket'];groups={o:{kk:gg for kk,gg in g[g.origin.eq(o)].groupby(k)} for o in m['origins']};common=set(groups['real'])&set(groups['translated_geometry250']);dd=np.zeros((len(dates),4),float);before={o:int(g.origin.eq(o).sum()) for o in m['origins']}
 for kk in common:
  r=groups['real'][kk];c=groups['translated_geometry250'][kk];j=dates.index(kk[0]);weight=min(len(r),len(c));dd[j]+=[weight*r.status.eq('TARGET_FIRST').mean(),weight,weight*c.status.eq('TARGET_FIRST').mean(),weight]
 sr=dd.sum(axis=0);v=dd[ix].sum(axis=1);ok=(v[:,1]>0)&(v[:,3]>0);delta=100*(v[ok,0]/v[ok,1]-v[ok,2]/v[ok,3]);ci=np.quantile(delta,[.025,.975]) if len(delta) else [np.nan,np.nan];matched.append(dict(contract=C,landmark=age,endpoint=ep,common_strata=len(common),matched_weight=float(sr[1]),real_resolved_before=before['real'],control_resolved_before=before['translated_geometry250'],real_minus_control_points=100*(sr[0]/sr[1]-sr[2]/sr[3]) if sr[1] else np.nan,paired_day_lower=ci[0],paired_day_upper=ci[1],not_randomized=True))
pd.DataFrame(matched).to_csv(P/'matched-contrasts.csv',index=False)
primary=result[result.dedup.eq('dedup75')&result.origin.eq('real')&result.landmark.isin([2000,3000])&result.endpoint.eq(0)&result.visit_definition.eq('visits1')&result.speed_group.eq('all')&result.gap_policy.eq('observed')];e=safe(dict(status='LONGEVITY_EFFECTS_COMPLETE',contract=C,primary=primary.to_dict('records'),matched=matched,software_checks='raw signal count reconciliation and independent streaming primary thinning',effect_rows=len(result),independent_primary_signals=len(t),source_certified=False,holdout_opened=False,pnl_computed=False,multiplicity_corrected=False,bootstrap='10000 whole-session resamples; pointwise intervals, exploratory',comparison_plan=[dict(grain='landmark by prior-revisit count',population='real fixed geometry18/2000/20 P80W5 D40q50 touch, dedup75, first signal per6250bin before filters',unit='target-first percent',finding='test if prior revisits differentiate old-zone outcomes; retain empty and low-count groups',derivation='wins/resolved*100',disposition='chart',reason='directly measures requested new hypothesis')],remaining='volumefraction, imbalance and efficiency are persisted causal attributes; their incremental models, cross-session carry and all non-primary family outcomes not yet inferentially analyzed'));(P/'analysis-evidence.json').write_text(json.dumps(e,indent=2,allow_nan=False)+'\n');print('EFFECTS',C,len(result));print('PRIMARY',primary[['landmark','visits_group','resolved','target_percent','day_lower','day_upper']].to_dict('records'));print('MATCHED',matched)
