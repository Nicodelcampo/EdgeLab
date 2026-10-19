from pathlib import Path,PureWindowsPath
import argparse,json,hashlib,sys,math,importlib.util
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).parent/'repo'))
from edgelab.research.holdout_guard import check_holdout
from edgelab.research.universo_estudio import cargar_dias_de_estudio
import past_price_producer as p
NS=10**9
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def dump(f,j):Path(f).write_text(json.dumps(j,indent=2,ensure_ascii=False,allow_nan=False))
def events(b,asset,contract,days,tf,k,H):
 lag=60//tf;prev=b.bucket.diff().eq(1);history=b.bucket-b.bucket.shift(lag);move=b.c-b.c.shift(lag);U=b.mom_atr_prev
 last=960-H-15
 mask=(np.arange(len(b))>=600)&b.date.isin(days)&(b.minute>=600)&(b.minute+tf<=last)&prev&(history==lag)&np.isfinite(U)&(U>0)&(move.abs()>=k*U)&(move!=0)
 indices=np.flatnonzero(mask.to_numpy());raw=[];slots=[];blocked=-1
 for i in indices:
  z=b.iloc[i];ns=int(z.close_ns);v={'asset':asset,'contract':contract,'day':z.date,'tf':tf,'threshold':k,'hold_min':H,'signal_ns':ns,'direction':int(np.sign(move.iloc[i])),'U':float(U.iloc[i])};raw.append(v)
  if ns<=blocked:continue
  slots.append(v);blocked=ns+(H*60+60)*NS
 assert all(a['signal_ns']+(H*60+60)*NS<b['signal_ns'] for a,b in zip(slots,slots[1:]))
 return raw,slots

def quote_entries(rows,file):
 waiting={x['signal_ns'] for x in rows};good={};lo=min(waiting);hi=max(waiting)+30*NS+1;invalid=0
 for ba in p.scan(file,['ts_utc_ns','bid_ticks','ask_ticks'],lo,hi):
  t=ba.to_pandas();end=int(t.ts_utc_ns.iloc[-1]);valid=np.isfinite(t[['bid_ticks','ask_ticks']]).all(axis=1)&(t.bid_ticks>0)&(t.ask_ticks>t.bid_ticks);invalid+=int((~valid).sum());q=t.loc[valid];ts=q.ts_utc_ns.to_numpy();bid=q.bid_ticks.to_numpy(float);ask=q.ask_ticks.to_numpy(float)
  for s in list(waiting):
   target=s+250000000;deadline=s+30*NS
   if end<=target:continue
   i=np.searchsorted(ts,target,side='right')
   if i<len(ts) and ts[i]<=deadline:good[s]={'lag_s':float((ts[i]-s)/NS),'spread_ticks':float(ask[i]-bid[i])};waiting.remove(s)
   elif end>deadline:waiting.remove(s)
 return good,invalid

def run(root,out):
 here=Path(__file__).parent;m=json.loads((here/'manifest.json').read_text());out.mkdir(exist_ok=True,parents=True)
 check_holdout('2025-10-07T00:00:00Z','2025-12-31T23:59:59Z',purpose='development',caller='MOM_FREQUENCY_TARGETFREE_V1',log_path=str(out/'holdout_guard.log'))
 assert sha(here/'past_price_producer.py')==m['past_price_producer_sha256']
 for f,h in m['repo_modules'].items():assert sha(here/'repo'/f)==h
 baseline=json.loads((here/'baseline_EVENTS_PRIVATE.json').read_text());days=m['days']; allslots={};rawcounts={};profiles=[];parity=[];prefix=[];quotes={};custody=[]
 for asset in m['assets']:
  ss=[s for s in p.CATALOGS[asset]['sessions'] if s['trade_date'] in days];assert len(ss)==len(days)
  adapter={'dias':[{'fecha':s['trade_date'][:4]+'-'+s['trade_date'][4:6]+'-'+s['trade_date'][6:],'archivo':PureWindowsPath(s['path']).name,'n_ticks':s['ticks']} for s in ss]};approved,guard=cargar_dias_de_estudio(adapter,caller='MOM_FREQUENCY_CATALOG_ADAPTER');assert len(approved)==54 and not guard['descartados_holdout'];
  for name in sorted({PureWindowsPath(s['path']).name for s in ss}):
   rel=asset+'/'+name;f=root/rel;assert sha(f)==p.EXPECTED[rel];meta=pq.ParquetFile(f).metadata;custody.append({'path':rel,'sha256':sha(f),'rows':meta.num_rows})
   sub=[s for s in ss if PureWindowsPath(s['path']).name==name];localdays={s['trade_date'] for s in sub};fileevents=[]
   for tf in m['timeframes_min']:
    p.STEP=tf*60*NS;b,prof,lo,hi=p.aggregate_profile(f,sub);profiles.append(dict(asset=asset,path=name,tf=tf,**prof))
    for k in m['threshold_prevTR20SMA']:
     for H in m['holding_min']:
      key=f'{asset}|TF{tf}|K{k}|H{H}';raw,ev=events(b,asset,sub[0]['contract'],localdays,tf,k,H);allslots.setdefault(key,[]).extend(ev);rawcounts[key]=rawcounts.get(key,0)+len(raw);fileevents.extend(ev)
      # Three strict completed-bar prefix checks, same event populations, no future prices.
      pos=[i for i in range(600,len(b)) if b.date.iloc[i] in localdays and b.minute.iloc[i]==720]
      for i in pos[:3]:
       short=p.indicators(b.iloc[:i+1][['bucket','o','h','l','c','n']].copy());_,pev=events(short,asset,sub[0]['contract'],localdays,tf,k,H)
       assert pev==[x for x in ev if x['signal_ns']<=int(b.close_ns.iloc[i])];prefix.append({'key':key,'path':name,'cut_ns':int(b.close_ns.iloc[i]),'pass':True})
      if k==1. and H==120:
       old=[x for x in baseline if x['asset']==asset and x['tf']==tf and x['contract']==sub[0]['contract']];a=[(x['signal_ns'],x['direction'],x['U']) for x in ev];z=[(x['signal_ns'],x['direction'],x['U']) for x in old];assert a==z,('BASELINE_PARITY',key,name,len(a),len(z));parity.append({'key':key,'path':name,'n':len(a),'pass':True})
   if fileevents:
    q,invalid=quote_entries(fileevents,f)
    for ns,v in q.items():quotes[(asset,sub[0]['contract'],ns)]=v
   print('supportdone',asset,name,len(fileevents),flush=True)
 census={}
 for key,ss in allslots.items():
  ss.sort(key=lambda x:x['signal_ns']);daycounts=[sum(x['day']==d for x in ss) for d in days];base=[x for x in allslots[f"{ss[0]['asset']}|TF{ss[0]['tf']}|K1.0|H120"]] if ss else []
  aset={(x['contract'],x['signal_ns']) for x in ss};bset={(x['contract'],x['signal_ns']) for x in base};q=[quotes[(x['asset'],x['contract'],x['signal_ns'])] for x in ss if (x['asset'],x['contract'],x['signal_ns']) in quotes]
  census[key]={'unthinned_eligible_decisions':rawcounts[key],'reserved_intents':len(ss),'quote_entry_observable':len(q),'no_entry_quote':len(ss)-len(q),'active_dates':sum(n>0 for n in daycounts),'zero_dates':sum(n==0 for n in daycounts),'eligible_dates':54,'intents_per_date_quantiles':dict(zip(['min','p25','median','p75','max'],map(float,np.quantile(daycounts,[0,.25,.5,.75,1])))),'mean_intents_per_date':float(np.mean(daycounts)),'quote_lag_p50_p95_max':list(map(float,np.quantile([v['lag_s'] for v in q],[.5,.95,1]))) if q else None,'entry_spread_p50_p95':list(map(float,np.quantile([v['spread_ticks'] for v in q],[.5,.95]))) if q else None,'by_contract':{c:sum(x['contract']==c for x in ss) for c in sorted({x['contract'] for x in ss})},'by_month':{mo:sum(x['day'][:6]==mo for x in ss) for mo in ['202510','202511','202512']},'same_anchor_with_H120K1':len(aset&bset),'new_anchor_vs_H120K1':len(aset-bset),'support_goal_met':len(ss)>=100 and sum(n>0 for n in daycounts)>=45 and float(np.median(daycounts))>=4,'not_trades':True,'outcomes_computed':False}
 mod=here/'repo/tools/bt2_absorption_power.py';sp=importlib.util.spec_from_file_location('nativepower',mod);power=importlib.util.module_from_spec(sp);sp.loader.exec_module(power)
 schematic={'method':'nativebt2genericfunctionsONLY; unitSD standardized session estimand; notRTYestimatedpower; noBT2defaults','scenarios':[{'standardized_effect':d,'sessions':n,'power_unadjusted_normal_approx':power.power_two_sided_ci(d,1,n),'sessions_for80_unadjusted':power.n_for_power(d,1)} for d in [.2,.3,.5] for n in [54,100,160]],'formal_G2_min_sessions':160,'actual_sessions':54}
 pre={'script_sha256':sha(__file__),'manifest_sha256':sha(here/'manifest.json'),'producer_sha256':sha(here/'past_price_producer.py'),'baseline_event_input_sha256':sha(here/'baseline_EVENTS_PRIVATE.json'),'custody':custody,'outcomes_computed':False,'holdout_opened':False,'new_windows_opened':False}
 dump(out/'preflight.json',pre);dump(out/'manifest.json',m);dump(out/'census.json',{'cells':census,'parity':parity,'prefix_checks':len(prefix),'prefix_pass':True,'guard':'nativeuniverso+holdoutguardPASS','schematic_power':schematic,'outcomes_computed':False});dump(out/'profiles.json',profiles)
 print('DONE',len(census),'profiles;allprefix/baselinePASS;outcomesfalse',flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,default=Path('/kaggle/working/momentum_frequency'));z=a.parse_args();run(z.root,z.out)
