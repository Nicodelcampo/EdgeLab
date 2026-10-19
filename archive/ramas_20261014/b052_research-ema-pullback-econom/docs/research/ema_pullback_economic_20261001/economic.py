"""Frozen six-cell development screen. No holdout, no live fills, no L2."""
from pathlib import Path,PureWindowsPath
import sys,json,argparse,collections
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).parent/'repo'))
from edgelab.research.holdout_guard import check_holdout
from edgelab.research.universo_estudio import cargar_dias_de_estudio
from edgelab.research.costs import CostScenario,friccion_rt_ticks
from edgelab.stats import cluster_estimand as ce
import past_price_producer as p
from census import events
NS=10**9

def costs(m,asset,leg):
 c=m['costs'][asset]
 return friccion_rt_ticks(CostScenario('explicit',leg,leg,leg,leg,c['commission_side_usd']),tick_value_usd=c['tick_value_usd'],instrument=asset)

def replay(slots,batches):
 waiting={s['id']:s for s in slots};opened={};stats={'invalid_quotes':0,'quote_rows':0}
 for batch in batches:
  t=batch.to_pandas()
  if t.empty:continue
  last=int(t.ts_utc_ns.iloc[-1]);valid=np.isfinite(t[['bid_ticks','ask_ticks']]).all(axis=1)&(t.bid_ticks>0)&(t.ask_ticks>t.bid_ticks)
  q=t.loc[valid];ts=q.ts_utc_ns.to_numpy();bid=q.bid_ticks.to_numpy(float);ask=q.ask_ticks.to_numpy(float)
  stats['invalid_quotes']+=int((~valid).sum());stats['quote_rows']+=len(q)
  for ident,s in list(waiting.items()):
   target=s['signal_ns']+250000000;deadline=s['signal_ns']+30*NS
   if last<=target:continue
   j=int(np.searchsorted(ts,target,side='right'))
   if j<len(ts) and ts[j]<=deadline:
    s.update(status='OPEN',entry_ns=int(ts[j]),entry_bid=float(bid[j]),entry_ask=float(ask[j]));opened[ident]=s;del waiting[ident]
   elif last>deadline:s['status']='NO_ENTRY_QUOTE_WITHIN30S';del waiting[ident]
  for ident,s in list(opened.items()):
   target=s['entry_ns']+s['hold_min']*60*NS
   if last<target:continue
   j=int(np.searchsorted(ts,target,side='left'))
   if j<len(ts) and ts[j]<=s['cutoff_ns']:
    eb=s['entry_bid'];ea=s['entry_ask'];xb=float(bid[j]);xa=float(ask[j]);long=xb-ea;short=eb-xa
    gross=long if s['direction']>0 else short;alpha=s['direction']*((xb+xa)-(eb+ea))/2
    assert abs(alpha-(gross-(long+short)/2))<1e-9
    s.update(status='COMPLETE',exit_ns=int(ts[j]),exit_bid=xb,exit_ask=xa,gross_ticks=gross,alpha_ticks=alpha,alpha_U=alpha/s['U'],entry_lag_s=(s['entry_ns']-s['signal_ns'])/NS,exit_lag_s=(int(ts[j])-target)/NS)
    del opened[ident]
   elif last>s['cutoff_ns']:s['status']='UNKNOWN_EXIT_NO_QUOTE_BY16ET';del opened[ident]
 for s in waiting.values():s['status']='NO_ENTRY_QUOTE_WITHIN30S'
 for s in opened.values():s['status']='UNKNOWN_EXIT_EOF'
 return stats

def evaluate(rows,days,m,cell_index):
 done=[s for s in rows if s['status']=='COMPLETE'];asset=rows[0]['asset'];states=dict(collections.Counter(s['status'] for s in rows));overlaps=[]
 for a,b in zip(rows,rows[1:]):
  if a['status']=='COMPLETE' and a['exit_ns']>=b['signal_ns']:overlaps.append([a['id'],b['id']])
 if not done:return {'states':states,'n':0,'screen_pass':False}
 for s in done:
  for label,leg in [('base',1),('adverse',2),('severe',3)]:
   s['net_'+label+'_ticks']=s['gross_ticks']-costs(m,asset,leg);s['net_'+label+'_U']=s['net_'+label+'_ticks']/s['U']
  s['net_base_usd']=s['net_base_ticks']*m['costs'][asset]['tick_value_usd']
 total=sum(s['net_base_ticks'] for s in done);ordered=sorted(done,key=lambda s:s['net_base_ticks'],reverse=True);contracts={}
 for c in sorted({s['contract'] for s in rows}):
  rr=[s for s in done if s['contract']==c];su=sum(s['net_base_ticks'] for s in rr)
  contracts[c]={'n':len(rr),'sum_net_ticks':su,'mean_net_ticks':su/len(rr) if rr else None,'mean_net_U':float(np.mean([s['net_base_U'] for s in rr])) if rr else None,'share_total_net':su/total if total else None}
 daily={d:[s for s in done if s['day']==d] for d in days};active=sum(bool(v) for v in daily.values());inference={}
 for endpoint in ['net_base_U','alpha_U']:
  cl=ce.aggregate_sessions(days,{d:[float(s[endpoint]) for s in rr] for d,rr in daily.items()});bs=ce.resample_stationary_session_clusters(cl,n_replicates=m['bootstrap_replicates'],seed=m['seed']+cell_index*2+int(endpoint=='alpha_U'))
  assert bs.invalid_zero_denominator==0
  qs=np.quantile(bs.replicates,[.025,.975,.05/12,.05/120])
  inference[endpoint]={'observed':bs.observed,'percentile95':[float(qs[0]),float(qs[1])],'lower_one_sided_bonf12':float(qs[2]),'lower_one_sided_budget120':float(qs[3]),'block_length':bs.block_length,'n_sessions':bs.n_sessions,'bootstrap_se':float(np.std(bs.replicates,ddof=1)),'invalid_zero_denominator':bs.invalid_zero_denominator,'method':bs.method}
  try:ce.studentized_stationary_interval(cl,n_replicates=100,seed=m['seed'])
  except ce.ClusterEstimandError as e:formal=str(e)
  else:raise AssertionError('G2 unexpectedly enabled')
 top5sum=sum(s['net_base_ticks'] for s in ordered[5:]);maxshare=max(v['share_total_net'] for v in contracts.values()) if total>0 else None
 g1={'n_at_least100':len(done)>=100,'mean_net_positive':total>0,'positive_without_best5_trades':top5sum>0,'contract_concentration_le80pct':maxshare is not None and maxshare<=.8}
 technical=not overlaps and not any(k.startswith('UNKNOWN') for k in states)
 out={'states':states,'n':len(done),'active_dates':active,'eligible_dates':len(days),'median_trades_per_date':float(np.median([len(rr) for rr in daily.values()])),'mean_net_ticks':total/len(done),'mean_net_U':float(np.mean([s['net_base_U'] for s in done])),'mean_net_usd':float(np.mean([s['net_base_usd'] for s in done])),'mean_alpha_U':float(np.mean([s['alpha_U'] for s in done])),'win_fraction_base':float(np.mean([s['net_base_ticks']>0 for s in done])),'mean_net_adverse_U':float(np.mean([s['net_adverse_U'] for s in done])),'mean_net_severe_U':float(np.mean([s['net_severe_U'] for s in done])),'net_ticks_without_best5_trades':top5sum,'mean_ticks_without_best5_trades':top5sum/(len(done)-5),'by_contract':contracts,'inference':inference,'g1_diagnostic':g1,'g1_pass':all(g1.values()),'formal_G2':'BLOCKED: '+formal,'technical_gate':technical,'overlap_pairs':overlaps,'screen_pass':technical and len(done)>=100 and active>=45 and all(v['lower_one_sided_bonf12']>0 for v in inference.values()),'cumulative_sensitivity_pass':technical and all(v['lower_one_sided_budget120']>0 for v in inference.values()),'quote_lag_entry_p50_p95_max':list(map(float,np.quantile([s['entry_lag_s'] for s in done],[.5,.95,1]))),'quote_lag_exit_p50_p95_max':list(map(float,np.quantile([s['exit_lag_s'] for s in done],[.5,.95,1])))}
 return out

def run(root,out):
 here=Path(__file__).parent;m=json.loads((here/'manifest.json').read_text());out.mkdir(parents=True,exist_ok=True)
 check_holdout('2025-10-07T00:00:00Z','2025-12-31T23:59:59Z',purpose='development',caller='MOM_SHORT_ECONOMIC_V1',log_path=str(out/'holdout_guard.log'))
 for name,h in m['code_sha256'].items():assert p.sha(here/name)==h,('CODE_CUSTODY',name)
 expected=pd.read_csv(here/'expected_frequency.csv');days=m['days'];custody=[];selected={}
 for asset in m['assets']:
  ss=[s for s in p.CATALOGS[asset]['sessions'] if s['trade_date'] in days];assert len(ss)==54
  adapter={'dias':[{'fecha':s['trade_date'][:4]+'-'+s['trade_date'][4:6]+'-'+s['trade_date'][6:],'archivo':PureWindowsPath(s['path']).name,'n_ticks':s['ticks']} for s in ss]}
  approved,guard=cargar_dias_de_estudio(adapter,caller='MOM_SHORT_ECONOMIC');assert len(approved)==54 and not guard['descartados_holdout'];selected[asset]=ss
  for name in sorted({PureWindowsPath(s['path']).name for s in ss}):
   rel=asset+'/'+name;f=root/rel;h=p.sha(f);assert h==p.EXPECTED[rel];custody.append({'path':rel,'sha256':h,'rows':pq.ParquetFile(f).metadata.num_rows})
 p.dump(out/'preflight.json',{'runner_sha256':p.sha(__file__),'manifest_sha256':p.sha(here/'manifest.json'),'custody':custody,'code_sha256':m['code_sha256'],'outcomes_opened_at_preflight':False,'holdout_opened':False,'new_dates_opened':False})
 p.dump(out/'manifest.json',m);allrows={};profiles=[];prefix_n=0;replay_stats=[]
 for asset in m['assets']:
  ss=selected[asset]
  for name in sorted({PureWindowsPath(s['path']).name for s in ss}):
   f=root/asset/name;sub=[s for s in ss if PureWindowsPath(s['path']).name==name];localdays={s['trade_date'] for s in sub};p.STEP=5*60*NS;b,prof,lo,hi=p.aggregate_profile(f,sub);profiles.append(dict(asset=asset,file=name,**prof));rr=[]
   for H in m['holding_min']:
    key=f'{asset}|H{H}';raw,ev=events(b,asset,sub[0]['contract'],localdays,5,1.,H)
    pos=[i for i in range(600,len(b)) if b.date.iloc[i] in localdays and b.minute.iloc[i]==720]
    for i in pos[:3]:
     short=p.indicators(b.iloc[:i+1][['bucket','o','h','l','c','n']].copy());_,check=events(short,asset,sub[0]['contract'],localdays,5,1.,H);assert check==[x for x in ev if x['signal_ns']<=int(b.close_ns.iloc[i])];prefix_n+=1
    for x in ev:
     x.update(id=f"{key}|{x['contract']}|{x['signal_ns']}",status='WAITING',cutoff_ns=int(pd.Timestamp(x['day']+' 16:00',tz='America/New_York').tz_convert('UTC').value))
    allrows.setdefault(key,[]).extend(ev);rr.extend(ev)
   st=replay(rr,p.scan(f,['ts_utc_ns','bid_ticks','ask_ticks'],min(x['signal_ns'] for x in rr),max(x['cutoff_ns'] for x in rr)+1));replay_stats.append(dict(asset=asset,file=name,**st));print('replay_done',asset,name,len(rr),flush=True)
 results={}
 for ci,(key,rr) in enumerate(allrows.items()):
  rr.sort(key=lambda x:x['signal_ns']);a=rr[0]['asset'];H=rr[0]['hold_min'];ex=expected[(expected.asset==a)&(expected.TFmin==5)&(expected.K==1)&(expected.Hmin==H)].iloc[0];assert len(rr)==int(ex.reserved),('CENSUS_PARITY',key,len(rr),int(ex.reserved))
  assert sum(x['status']!='NO_ENTRY_QUOTE_WITHIN30S' for x in rr)==int(ex.quote_entry)
  results[key]=evaluate(rr,days,m,ci);results[key]['census_parity']=True;print('statistics_done',key,flush=True)
  with open(out/(key.replace('|','_')+'_LEDGER_PRIVATE.jsonl'),'w') as fp:
   for x in rr:fp.write(json.dumps(x,sort_keys=True,allow_nan=False)+'\n')
 p.dump(out/'results.json',{'cells':results,'prefix_checks_passed':prefix_n,'profiles':profiles,'replay':replay_stats,'formal_promotion':'NOT_AUTHORIZED','new_dates_opened':False,'holdout_opened':False,'clock_and_quote_age_certified':False,'actual_fills_certified':False})
 print('DONE economic six cells; development only',flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,default=Path('/kaggle/working/momentum_short'));z=a.parse_args();run(z.root,z.out)
