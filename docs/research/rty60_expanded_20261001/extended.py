"""RTY60 expanded DEVELOPMENT population; unchanged signal/replay/costs."""
from pathlib import Path,PureWindowsPath
import json,sys,argparse,collections,dataclasses
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).parent/'repo'))
from edgelab.research.holdout_guard import check_holdout
from edgelab.research.universo_estudio import cargar_dias_de_estudio
from edgelab.stats import cluster_estimand as ce
from economic import replay,costs
from census import events
import past_price_producer as p
NS=10**9

def summarise(rows,days,m,label,seedoffset):
 rr=[s for s in rows if s['day'] in days];done=[s for s in rr if s['status']=='COMPLETE'];states=dict(collections.Counter(s['status'] for s in rr));daily={d:[s for s in done if s['day']==d] for d in days}
 assert done,('NO_COMPLETE',label)
 total=sum(s['net_base_ticks'] for s in done);byc={}
 for c in sorted({s['contract'] for s in rr},key=lambda c:min(s['signal_ns'] for s in rr if s['contract']==c)):
  ss=[s for s in done if s['contract']==c];su=sum(s['net_base_ticks'] for s in ss)
  byc[c]={'n':len(ss),'active_dates':len({s['day'] for s in ss}),'sum_net_ticks':su,'mean_net_ticks':su/len(ss) if ss else None,'mean_net_usd':5*su/len(ss) if ss else None,'mean_net_U':float(np.mean([s['net_base_U'] for s in ss])) if ss else None,'share_positive_total_net':su/total if total>0 else None}
 best=sorted(done,key=lambda s:s['net_base_ticks'],reverse=True);byq={}
 for q in sorted({s['quarter'] for s in done}):
  ss=[s for s in done if s['quarter']==q];byq[q]={'n':len(ss),'active_dates':len({s['day'] for s in ss}),'eligible_dates':sum(d[:4]+'Q'+str((int(d[4:6])-1)//3+1)==q for d in days),'mean_net_usd':float(np.mean([s['net_base_usd'] for s in ss])),'mean_net_U':float(np.mean([s['net_base_U'] for s in ss])),'sum_net_usd':sum(s['net_base_usd'] for s in ss)}
 stats={}
 for i,ep in enumerate(['net_base_U','alpha_U']):
  cl=ce.aggregate_sessions(days,{d:[float(s[ep]) for s in ss] for d,ss in daily.items()});bs=ce.resample_stationary_session_clusters(cl,n_replicates=m['bootstrap_replicates'],seed=m['seed']+seedoffset+i)
  assert bs.invalid_zero_denominator==0
  qs=np.quantile(bs.replicates,[.025,.975,.05/12,.05/122]);stats[ep]={'mean':bs.observed,'ci95_percentile':[float(qs[0]),float(qs[1])],'lower_bonf12':float(qs[2]),'lower_budget122_sensitivity':float(qs[3]),'n_sessions':bs.n_sessions,'block_length':bs.block_length,'bootstrap_se':float(np.std(bs.replicates,ddof=1)),'invalid_replicates':bs.invalid_zero_denominator,'method':bs.method}
  if label=='FULL175' and ep=='net_base_U':
   try:
    student=ce.studentized_stationary_interval(cl,n_replicates=m['studentized_replicates'],seed=m['seed']+1000,confidence=1-2*.05/12)
    stats[ep]['native_studentized_component']=dataclasses.asdict(student)
   except ce.ClusterEstimandError as e:stats[ep]['native_studentized_component']={'status':'ABSTAIN','reason':str(e)}
 g1={'n_ge100':len(done)>=100,'base_net_positive':total>0,'positive_without_top5_trades':sum(s['net_base_ticks'] for s in best[5:])>0,'no_contract_above80pct':total>0 and max(x['share_positive_total_net'] for x in byc.values())<=.8}
 dd=0.;peak=0.;bal=0.
 for s in done:
  bal+=s['net_base_usd'];peak=max(peak,bal);dd=max(dd,peak-bal)
 qvalues={k:float(v) for k,v in zip(['p5','p25','p50','p75','p95'],np.quantile([s['net_base_ticks'] for s in done],[.05,.25,.5,.75,.95]))}
 return {'population':label,'n':len(done),'intents':len(rr),'status_counts':states,'eligible_dates':len(days),'active_dates':sum(bool(v) for v in daily.values()),'zero_trade_dates':sum(not v for v in daily.values()),'mean_trades_per_date':len(done)/len(days),'median_trades_per_date':float(np.median([len(v) for v in daily.values()])),'mean_gross_ticks':float(np.mean([s['gross_ticks'] for s in done])),'mean_net_ticks':total/len(done),'mean_net_usd':5*total/len(done),'mean_net_U':float(np.mean([s['net_base_U'] for s in done])),'mean_alpha_U':float(np.mean([s['alpha_U'] for s in done])),'net_total_usd':total*5,'mean_net_adverse_usd':float(np.mean([s['net_adverse_usd'] for s in done])),'mean_net_severe_usd':float(np.mean([s['net_severe_usd'] for s in done])),'win_fraction_base':float(np.mean([s['net_base_ticks']>0 for s in done])),'closed_trade_balance_max_drawdown_usd_NOT_MTM':dd,'quantiles_net_ticks':qvalues,'net_total_usd_without_top1':sum(s['net_base_usd'] for s in best[1:]),'net_total_usd_without_top5':sum(s['net_base_usd'] for s in best[5:]),'net_total_usd_without_top10':sum(s['net_base_usd'] for s in best[10:]),'by_contract':byc,'by_quarter':byq,'inference':stats,'g1_diagnostic':g1,'g1_pass':all(g1.values()),'joint_exploratory_lower12_positive':all(x['lower_bonf12']>0 for x in stats.values()),'cumulative_sensitivity_positive':all(x['lower_budget122_sensitivity']>0 for x in stats.values())}

def run(root,out):
 here=Path(__file__).parent;m=json.load(open(here/'manifest.json'));days=m['days'];old=m['original54'];extra=sorted(set(days)-set(old));assert len(days)==175 and len(extra)==121;ss=[s for s in p.CATALOGS['RTY']['sessions'] if s['trade_date'] in days]
 assert len(ss)==175 and sorted(s['trade_date'] for s in ss)==days
 out.mkdir(parents=True,exist_ok=True)
 check_holdout(pd.Timestamp(min(s['start'] for s in ss)-7*86400*NS,tz='UTC').isoformat(),pd.Timestamp(max(s['end'] for s in ss),tz='UTC').isoformat(),purpose='development',caller='RTY60_EXPANDED175_V1',log_path=str(out/'holdout_guard.log'))
 for n,h in m['code_sha256'].items():assert p.sha(here/n)==h,('CODE_SHA',n)
 adapter={'dias':[{'fecha':s['trade_date'][:4]+'-'+s['trade_date'][4:6]+'-'+s['trade_date'][6:],'archivo':PureWindowsPath(s['path']).name,'n_ticks':s['ticks']} for s in ss]};approved,guard=cargar_dias_de_estudio(adapter,caller='RTY60_EXPANDED175');assert len(approved)==175 and not guard['descartados_holdout']
 custody=[]
 names=sorted({PureWindowsPath(s['path']).name for s in ss})
 for n in names:
  f=root/'RTY'/n;rel='RTY/'+n;h=p.sha(f);assert h==p.EXPECTED[rel];meta=pq.ParquetFile(f).metadata;custody.append({'path':rel,'sha256':h,'rows':meta.num_rows})
  mf=f.with_name(n.replace('_ticks_ext.parquet','_manifest_ext.json'))
  if mf.exists():
   assert p.sha(mf)==p.EXPECTED['RTY/'+mf.name];z=json.load(open(mf));assert z['rows']==meta.num_rows and z['tick_size']==.1 and z['lineas_no_parseadas']==0
   custody[-1].update(upstream_pre_recompression_sha=z['parquet_sha256'],metadata_sha256=p.sha(mf))
 p.dump(out/'preflight.json',{'runner_sha256':p.sha(__file__),'manifest_sha256':p.sha(here/'manifest.json'),'custody':custody,'code_sha256':m['code_sha256'],'all_price_decodes_and_targets_strictly_before_general_holdout':True,'whole_file09_hash_only_can_include_postcutoff_bytes':True,'outcomes_opened_at_preflight':False,'holdout_outcomes_opened':False})
 p.dump(out/'manifest.json',m)
 allrows=[];profiles=[];prefix=0;raw_total=0
 for n in names:
  f=root/'RTY'/n;sub=[s for s in ss if PureWindowsPath(s['path']).name==n];localdays={s['trade_date'] for s in sub};p.STEP=5*60*NS;b,prof,lo,hi=p.aggregate_profile(f,sub);assert hi<=max(s['end'] for s in ss);profiles.append(dict(contract=sub[0]['contract'],file=n,lo_ns=lo,hi_ns=hi,**prof));raw,ev=events(b,'RTY',sub[0]['contract'],localdays,5,1.,60);raw_total+=len(raw)
  positions=[i for i in range(600,len(b)) if b.date.iloc[i] in localdays and b.minute.iloc[i]==720]
  for i in positions[:3]:
   short=p.indicators(b.iloc[:i+1][['bucket','o','h','l','c','n']].copy());_,check=events(short,'RTY',sub[0]['contract'],localdays,5,1.,60);assert check==[x for x in ev if x['signal_ns']<=int(b.close_ns.iloc[i])];prefix+=1
  for s in ev:s.update(id=f"RTY|H60|{s['contract']}|{s['signal_ns']}",status='WAITING',cutoff_ns=int(pd.Timestamp(s['day']+' 16:00',tz='America/New_York').tz_convert('UTC').value),quarter=s['day'][:4]+'Q'+str((int(s['day'][4:6])-1)//3+1))
  allrows.extend(ev);print('geometry_done',n,len(ev),flush=True)
 # Target-free complete census and baseline parity BEFORE opening any new target outcomes.
 baseline=json.load(open(here/'baseline54_EVENTS_PRIVATE.json'));orig=[s for s in allrows if s['day'] in old];signature=lambda rr:sorted((s['id'],s['signal_ns'],s['direction'],s['U']) for s in rr)
 assert signature(orig)==signature(baseline),('BASELINE_SIGNAL_PARITY',len(orig),len(baseline))
 p.dump(out/'targetfree_census.json',{'selected_dates':175,'additional_dates':121,'intents':len(allrows),'original54_intents':len(orig),'additional_intents':len(allrows)-len(orig),'raw_decisions':raw_total,'prefix_checks':prefix,'prefix_pass':True,'original54_signal_parity':True,'outcomes_opened':False})
 replay_stats=[]
 for n in names:
  file_rows=[s for s in allrows if PureWindowsPath(next(q['path'] for q in ss if q['contract']==s['contract'])).name==n];f=root/'RTY'/n
  st=replay(file_rows,p.scan(f,['ts_utc_ns','bid_ticks','ask_ticks'],min(s['signal_ns'] for s in file_rows),max(s['cutoff_ns'] for s in file_rows)+1));replay_stats.append(dict(file=n,**st));print('replay_done',n,len(file_rows),flush=True)
 allrows.sort(key=lambda s:s['signal_ns']);overlap=[]
 for a,b in zip(allrows,allrows[1:]):
  assert a['signal_ns']+3660*NS<b['signal_ns']
  if a['status']=='COMPLETE' and a['exit_ns']>=b['signal_ns']:overlap.append([a['id'],b['id']])
 for s in allrows:
  if s['status']=='COMPLETE':
   for label,leg in [('base',1),('adverse',2),('severe',3)]:
    s['net_'+label+'_ticks']=s['gross_ticks']-costs(m,'RTY',leg);s['net_'+label+'_U']=s['net_'+label+'_ticks']/s['U'];s['net_'+label+'_usd']=s['net_'+label+'_ticks']*5
 results={}
 for label,dlist,offset in [('FULL175',days,0),('ORIGINAL54',old,20),('ADDITIONAL121',extra,40)]:
  results[label]=summarise(allrows,dlist,m,label,offset);print('statistics_done',label,flush=True)
 technical=not overlap and not any(s['status'].startswith('UNKNOWN') for s in allrows)
 decision=technical and results['FULL175']['g1_pass'] and results['FULL175']['joint_exploratory_lower12_positive'] and results['ADDITIONAL121']['joint_exploratory_lower12_positive']
 with open(out/'RTY60_EXTENDED_LEDGER_PRIVATE.jsonl','w') as fp:
  for s in allrows:fp.write(json.dumps(s,sort_keys=True,allow_nan=False)+'\n')
 # Persist daily aggregate public-safe view; no prices or signal instants.
 daily=[{'day':d,'n':sum(s['status']=='COMPLETE' and s['day']==d for s in allrows),'sum_net_usd':sum(s['net_base_usd'] for s in allrows if s['status']=='COMPLETE' and s['day']==d),'sum_net_U':sum(s['net_base_U'] for s in allrows if s['status']=='COMPLETE' and s['day']==d),'sum_alpha_U':sum(s['alpha_U'] for s in allrows if s['status']=='COMPLETE' and s['day']==d)} for d in days]
 p.dump(out/'daily_aggregate.json',daily);p.dump(out/'results.json',{'populations':results,'technical_gate':technical,'overlap_pairs':overlap,'expanded_joint_screen':decision,'profiles':profiles,'replay':replay_stats,'formal_G2_overall':'NOT_APPROVED: PBO/DSR/history budget/parameter sensitivity/parity incomplete; native CI component alone NOT G2','holdout_outcomes_opened':False,'no_new_parameters_or_filters':True,'additional_dates_NOT_certified_blind_OOS':True})
 print('DONE RTY60 expanded development; joint screen',decision,'not promotion',flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,default=Path('/kaggle/working/rty60_extended'));z=a.parse_args();run(z.root,z.out)
