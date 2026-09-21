from __future__ import annotations
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from math import erfc, sqrt
import csv, hashlib, json, os, sys, time
import numpy as np
import pyarrow.parquet as pq
SRC=Path(__file__).resolve().parents[2];sys.path.insert(0,str(SRC))
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.bars import session_ids
from edgelab.bridge.indicators import bigtrap2absorption as bt2
from edgelab.research.ym_bt2a_retest_pilot import _ceil_even,_floor_even
from edgelab.research.ym_bt2a_economic_search import entry_policy_grid_v2,coarse_exit_grid_v1
RAW=Path(os.environ.get('EDGELAB_YM_RAW_ROOT','/data/raw/ym-kaggle/extracted'));OUT=Path(os.environ.get('EDGELAB_ECONOMIC_OUT','/data/analysis/ym-bt2a-economic/stage1'));OUT.mkdir(parents=True,exist_ok=True)
DISCOVERY_END_NS=1767225600000000000;FILES=['YM_09-25_ticks.parquet','YM_12-25_ticks.parquet','YM_03-26_ticks.parquet'];COLS=['ts_utc_ns','sequence','price_ticks','bid_ticks','ask_ticks','volume']
POLICIES=entry_policy_grid_v2();EXITS=coarse_exit_grid_v1();NP=len(POLICIES);NX=len(EXITS);assert(NP,NX,NP*NX)==(132,54,7128)
count=np.zeros((NP,NX),dtype=np.int64);sums=np.zeros((NP,NX));sums2=np.zeros((NP,NX));wins={c:np.zeros((NP,NX),dtype=np.int64) for c in(2,4,6)};entry_counts=np.zeros(NP,dtype=np.int64);contract_stats=defaultdict(lambda:{'events':0,'zones':0,'entries':0});source_hashes={}
def fhash(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def first(mask):
 idx=np.flatnonzero(mask);return int(idx[0]) if idx.size else None
def gross_vector(prices,sessions,entry_idx,direction):
 sign=1 if direction=='long' else-1;end=min(len(prices),entry_idx+1001);cut=np.flatnonzero(sessions[entry_idx+1:end]!=sessions[entry_idx])
 if cut.size:end=entry_idx+1+int(cut[0])
 rel=sign*(prices[entry_idx+1:end]-prices[entry_idx])
 if not len(rel):return None
 target_first={t:first(rel>=t) for t in(6,12,24)};trigger_first={None:None,6:first(rel>=6),12:first(rel>=12)};stop_first={}
 for be in(None,6,12):
  trig=trigger_first[be]
  for s in(6,12,24):
   mask=rel<=-s
   if trig is not None:mask=mask.copy();mask[trig:]=rel[trig:]<=0
   stop_first[(be,s)]=first(mask)
 out=[]
 for spec in EXITS:
  si=stop_first[(spec.break_even_trigger_ticks,spec.stop_ticks)];ti=target_first[spec.target_ticks];limit=min(spec.max_hold_ticks,len(rel));hits=[]
  if si is not None and si<limit:hits.append((si,'stop'))
  if ti is not None and ti<limit:hits.append((ti,'target'))
  if hits:
   idx,kind=min(hits,key=lambda x:x[0]);gross=float(rel[idx]) if kind=='stop' else float(spec.target_ticks)
  else:gross=float(rel[limit-1])
  out.append(gross)
 return np.asarray(out)
def entry_indices(z,prices,sessions):
 sig=int(z['sig_idx']);sess=sessions[sig];end=min(len(prices),sig+2001);cut=np.flatnonzero(sessions[sig+1:end]!=sess)
 if cut.size:end=sig+1+int(cut[0])
 future=prices[sig+1:end];n=len(future);result={}
 if n:result[0]=sig+1
 for offset,w in enumerate((5,10,25,50,100,200),start=1):
  if n>w:result[offset]=sig+1+w
 lo2=int(round(float(z['lo'])*2));hi2=int(round(float(z['hi'])*2));direction=str(z['dir']);future2=future*2;lookup={(p.departure_ticks,p.depth,p.max_wait_ticks):i for i,p in enumerate(POLICIES) if p.mode=='RETEST'}
 for dep in(1,2,4,6,8):
  armed=first(future2>=hi2+2*dep) if direction=='long' else first(future2<=lo2-2*dep)
  if armed is None:continue
  tail=future2[armed+1:]
  for depth in(0.0,.25,.5,.75,1.0):
   raw=hi2-depth*(hi2-lo2) if direction=='long' else lo2+depth*(hi2-lo2);target=_ceil_even(raw) if direction=='long' else _floor_even(raw);hit=first((tail>=lo2)&(tail<=target)) if direction=='long' else first((tail>=target)&(tail<=hi2))
   if hit is None:continue
   trigger=armed+1+hit;fill=trigger+1
   if fill>=n:continue
   observed=fill+1
   for wait in(100,250,500,1000,2000):
    if observed<=wait:result[lookup[(dep,depth,wait)]]=sig+1+fill
 return result
start=time.time();total_rows=0;total_zones=0
for name in FILES:
 path=RAW/name;source_hashes[name]=fhash(path);table=pq.read_table(path,columns=COLS,filters=[('ts_utc_ns','<',DISCOVERY_END_NS)])
 if not table.num_rows:continue
 def col(n,d):return table[n].to_numpy(zero_copy_only=False).astype(d,copy=False)
 ts=col('ts_utc_ns',np.int64);seq=col('sequence',np.int64);prices=col('price_ticks',np.int64);bid=col('bid_ticks',np.int64);ask=col('ask_ticks',np.int64);vol=col('volume',np.float64);contract=pq.ParquetFile(path).read_row_group(0,columns=['contract'])['contract'][0].as_py();ticks=TickSeries(ts,prices,vol,bid,ask,seq,1.0,'YM',str(contract),str(path));sessions=session_ids(ts);run=bt2.run(ticks,params=bt2.DEFAULTS)
 total_rows+=len(ts);total_zones+=int(run['n_zones']);contract_stats[str(contract)]['zones']=int(run['n_zones']);contract_stats[str(contract)]['events']=int(run['n_zones'])
 for z in run['zones']:
  entries=entry_indices(z,prices,sessions);contract_stats[str(contract)]['entries']+=len(entries);cache={}
  for pi,ei in entries.items():
   if ei not in cache:cache[ei]=gross_vector(prices,sessions,ei,str(z['dir']))
   gross=cache[ei]
   if gross is None:continue
   entry_counts[pi]+=1;count[pi]+=1;sums[pi]+=gross;sums2[pi]+=gross*gross
   for c in(2,4,6):wins[c][pi]+=(gross-c>0)
 print(json.dumps({'contract':contract,'rows':len(ts),'zones':run['n_zones'],'entries':contract_stats[str(contract)]['entries']}),flush=True)
rows=[]
for pi,p in enumerate(POLICIES):
 for xi,x in enumerate(EXITS):
  n=int(count[pi,xi]);mu=sums[pi,xi]/n if n else None;se=None
  if n>1:se=sqrt(max(0.0,(sums2[pi,xi]-sums[pi,xi]**2/n)/(n-1))/n)
  mean4=mu-4 if mu is not None else None;z=mean4/se if se and se>0 else 0;pval=.5*erfc(z/sqrt(2)) if n else 1.0
  rows.append({'entry_policy_id':p.policy_id,'exit_spec_id':x.spec_id,'trades':n,'mean_gross_ticks':mu,'mean_net_2':mu-2 if mu is not None else None,'mean_net_4':mean4,'mean_net_6':mu-6 if mu is not None else None,'iid_se':se,'iid_lcb95_net4':mean4-1.96*se if se is not None else None,'iid_p_one_sided_net4':pval,'win_rate_net2':wins[2][pi,xi]/n if n else None,'win_rate_net4':wins[4][pi,xi]/n if n else None,'win_rate_net6':wins[6][pi,xi]/n if n else None,'entry_mode':p.mode,'wait_ticks':p.wait_ticks,'departure_ticks':p.departure_ticks,'depth':p.depth,'max_wait_ticks':p.max_wait_ticks,'stop_ticks':x.stop_ticks,'target_ticks':x.target_ticks,'max_hold_ticks':x.max_hold_ticks,'be_trigger':x.break_even_trigger_ticks,'be_lock':x.break_even_lock_ticks})
m=len(rows);order=sorted(range(m),key=lambda i:rows[i]['iid_p_one_sided_net4']);prev=0
for rank,i in enumerate(order):adj=min(1.0,(m-rank)*rows[i]['iid_p_one_sided_net4']);prev=max(prev,adj);rows[i]['holm_p']=prev
prev=1
for rev,i in enumerate(reversed(order),start=1):rank=m-rev+1;q=min(prev,rows[i]['iid_p_one_sided_net4']*m/rank);rows[i]['bh_q']=q;prev=q
eligible=[r for r in rows if r['trades']>=200];top=sorted(eligible,key=lambda r:(r['mean_net_6'],r['iid_lcb95_net4']),reverse=True)[:100];entry_best={}
for r in eligible:
 cur=entry_best.get(r['entry_policy_id'])
 if cur is None or(r['mean_net_6'],r['iid_lcb95_net4'])>(cur['mean_net_6'],cur['iid_lcb95_net4']):entry_best[r['entry_policy_id']]=r
selected=sorted(entry_best.values(),key=lambda r:(r['mean_net_6'],r['iid_lcb95_net4']),reverse=True)[:12];summary={'schema':'ym_bt2a_economic_stage1_v1','campaign_id':'CAMP-YM-BT2A-ECONOMIC-002','split':'DISCOVERY_ONLY_BEFORE_2026','discovery_end_ns_exclusive':DISCOVERY_END_NS,'holdout_accessed':False,'validation_outcomes_accessed':False,'rows':total_rows,'zones':total_zones,'entry_policy_count':NP,'exit_spec_count':NX,'family_count':m,'minimum_trades':200,'source_hashes':source_hashes,'contracts':dict(contract_stats),'selected_entry_archetypes':selected,'top_100':top,'survivors_positive_net6':sum(1 for r in eligible if r['mean_net_6']>0),'survivors_holm_net4':sum(1 for r in eligible if r['holm_p']<.05 and r['mean_net_4']>0),'runtime_seconds':time.time()-start,'completed_at_utc':datetime.now(timezone.utc).isoformat(),'limitations':['IID screen only; session-cluster inference required before validation','Independent event outcomes; non-overlap enforcement required for final candidates','No validation or holdout outcomes opened']};raw=json.dumps(summary,sort_keys=True,separators=(',',':')).encode();summary['evidence_sha256']=hashlib.sha256(raw).hexdigest();(OUT/'stage1_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True))
with(OUT/'stage1_all_7128.csv').open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'rows':total_rows,'zones':total_zones,'family':m,'eligible':len(eligible),'positive_net6':summary['survivors_positive_net6'],'holm_net4':summary['survivors_holm_net4'],'best':top[:5],'runtime_seconds':round(summary['runtime_seconds'],2),'evidence_sha256':summary['evidence_sha256']},indent=2),flush=True)
