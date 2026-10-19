"""Frozen development falsification; NEVER a substitute for formal G2 or fresh OOS."""
from pathlib import Path
import argparse,json,hashlib,sys,math
import numpy as np
import pyarrow.dataset as ds
sys.path.insert(0,str(Path(__file__).parent/'repo'))
from edgelab.research import g2,g2_ratio
from edgelab.stats import cluster_estimand as ce
from edgelab.research.costs import CostScenario,friccion_rt_ticks
from edgelab.research.promotion import APPROVED_G2_CONTRACT_SHA256S
from edgelab.research.holdout_guard import check_holdout
SEED=20261003

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False,ensure_ascii=False))
def load(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def moments(x):
 x=np.asarray(x,float);z=x-x.mean();sd=float(x.std(ddof=1));m2=float(np.mean(z*z));return sd,float(np.mean(z**3)/m2**1.5),float(np.mean(z**4)/m2**2)
def group_cells(rows,days,field='net_U'):
 return ce.aggregate_sessions(days,{d:[x[field] for x in rows if x['day']==d] for d in days})
def summary(rows,days):
 pn=np.array([x['net_ticks'] for x in rows]);u=np.array([x['net_U'] for x in rows]);idx=np.argsort(pn)[::-1];total=float(pn.sum());top={}
 for n in [1,5,10]:
  keep=np.ones(len(pn),bool);keep[idx[:n]]=False;top[str(n)]={'sum_remaining_ticks':float(pn[keep].sum()),'mean_remaining_ticks':float(pn[keep].mean()),'fraction_total_removed':float(pn[idx[:n]].sum()/total) if total>0 else None}
 bycontract={c:{'n':sum(x['contract']==c for x in rows),'net_ticks':sum(x['net_ticks'] for x in rows if x['contract']==c)} for c in sorted({x['contract'] for x in rows})}
 maxshare=max(x['net_ticks'] for x in bycontract.values())/total if total>0 else None
 bymonth={m:{'n':sum(x['day'].startswith(m) for x in rows),'mean_ticks':float(np.mean([x['net_ticks'] for x in rows if x['day'].startswith(m)]))} for m in sorted({x['day'][:6] for x in rows})}
 eq=np.r_[0,np.cumsum([x['net_ticks']*5 for x in sorted(rows,key=lambda x:x['exit_ns'])])];dd=float(np.max(np.maximum.accumulate(eq)-eq))
 costs={}
 for name,slip in [('base',1),('adverso',2),('severo',3)]:
  scenario=CostScenario(name,slip,slip,slip,slip,2.25);fr=friccion_rt_ticks(scenario,tick_value_usd=5,instrument='RTY');v=np.array([x['gross_ticks']-fr for x in rows]);costs[name]={'friction_ticks':fr,'mean_ticks':float(v.mean()),'mean_USD_per_contract':float(v.mean()*5)}
 g1={'n100':len(rows)>=100,'mean_net_positive':total>0,'net_without_best5_trades_positive':top['5']['sum_remaining_ticks']>0,'no_contract_above80percent':bool(maxshare is not None and maxshare<=.8)}
 # Same-anchor counterfactuals: not independent event-vs-temporal-control samples.
 for x in rows:
  x['long_ticks']=x['exit_bid']-x['entry_ask']-2-.9;x['short_ticks']=x['entry_bid']-x['exit_ask']-2-.9
  x['difference_vs_always_long_U']=(x['net_ticks']-x['long_ticks'])/x['U']
 control={'design':'SAME_ANCHOR_DIRECTIONAL_COUNTERFACTUAL_NOT_TEMPORAL_CONTROL','long_mean_ticks':float(np.mean([x['long_ticks'] for x in rows])),'short_mean_ticks':float(np.mean([x['short_ticks'] for x in rows])),'momentum_minus_long_ticks':float(np.mean([x['net_ticks']-x['long_ticks'] for x in rows])),'by_direction':{str(d):{'n':sum(x['direction']==d for x in rows),'mean_net_ticks':float(np.mean([x['net_ticks'] for x in rows if x['direction']==d]))} for d in [-1,1]}}
 cl=group_cells(rows,days);bs=ce.resample_stationary_session_clusters(cl,n_replicates=50000,seed=SEED);low,high=ce.percentile_interval(bs,.95)
 try:ce.studentized_stationary_interval(cl,n_replicates=100,seed=SEED);formal='UNEXPECTED_ACCEPTANCE'
 except ce.ClusterEstimandError as e:formal=str(e)
 daily=[x.pnl_net for x in cl];sd,sk,ku=moments(daily);sr=float(np.mean(daily)/sd)
 centered=np.asarray(daily)-np.mean(daily);den=float(np.sum(centered**2));acs=[float(np.sum(centered[k:]*centered[:-k])/den) for k in range(1,6)];neff=max(2.,min(len(days),len(days)/(1+2*sum(max(x,0) for x in acs))))
 dsrs={str(trials):{'iid_sessions':g2.deflated_sharpe(sr,len(days),trials,sk,ku),'positive_ACF1to5_n_eff':g2.deflated_sharpe(sr,neff,trials,sk,ku)} for trials in [54,100]}
 return {'trades':len(rows),'active_dates':len({x['day'] for x in rows}),'mean_net_ticks':float(pn.mean()),'mean_net_USD_per_contract':float(pn.mean()*5),'mean_net_U':float(u.mean()),'total_net_USD_per_contract':total*5,'net_ticks_quantiles':dict(zip(['p5','p25','p50','p75','p95'],map(float,np.quantile(pn,[.05,.25,.5,.75,.95])))),'top_trades':top,'contract_folds':bycontract,'max_contract_fraction_total_net':maxshare,'monthly':bymonth,'G1_diagnostic_checks':g1,'G1_diagnostic_pass':all(g1.values()),'cost_scenarios_assumed':costs,'adverse_collapse_check':costs['adverso']['mean_ticks']>-.5*costs['base']['mean_ticks'],'closed_trade_balance_maxDD_USD':dd,'MTM_drawdown_certified':False,'directional_counterfactual':control,'stationary_percentile_DIAGNOSTIC_U':{'lower':low,'upper':high,'block_length':bs.block_length,'reps':50000,'formal_G2_accepted':False},'formal_primary_refusal':formal,'DSR_diagnostic':{'session_SR_nonannualized':sr,'skew':sk,'kurtosis':ku,'n_sessions':len(days),'n_eff_ACF_positive_rule':neff,'trial_scenarios':dsrs,'method_sha256':g2.dsr_method_sha256(),'all_history_Neff_certified':False,'scale':'daily total net_U, NOT annualized, not ROI'},'temporal_concentration_DIAGNOSTIC_NOT_EDGE_TEST':g2.temporal_concentration_test([x['net_ticks'] for x in rows],[x['day'] for x in rows],n_perm=1000,seed=SEED)}

def paths_profile(rows,root,expected):
 stats={x['id']:{'mfe_mid_ticks':0.,'mae_mid_ticks':0.,'valid_quote_rows':0} for x in rows};profiles=[]
 for name in sorted({x['contract'].replace(' ','_')+'_ticks_ext.parquet' for x in rows}):
  f=Path(root)/'RTY'/name;assert sha(f)==expected['RTY/'+name];ss=[x for x in rows if x['contract'].replace(' ','_')+'_ticks_ext.parquet'==name];lo=min(x['entry_ns'] for x in ss);hi=max(x['exit_ns'] for x in ss)+1
  scanner=ds.dataset(f,format='parquet').scanner(columns=['ts_utc_ns','bid_ticks','ask_ticks'],filter=(ds.field('ts_utc_ns')>=lo)&(ds.field('ts_utc_ns')<hi),batch_size=250000,use_threads=False);pr={'path':name,'scanned_rows':0,'invalid_quotes':0,'sha256':sha(f)}
  for batch in scanner.to_batches():
   t=batch.to_pandas();pr['scanned_rows']+=len(t);valid=np.isfinite(t[['bid_ticks','ask_ticks']]).all(axis=1)&(t.bid_ticks>0)&(t.ask_ticks>t.bid_ticks);pr['invalid_quotes']+=int((~valid).sum());q=t.loc[valid];ts=q.ts_utc_ns.to_numpy();mid=(q.bid_ticks.to_numpy(float)+q.ask_ticks.to_numpy(float))/2
   for x in ss:
    # Raw groups at exact exit timestamp might be AFTER chosen exit; exclude them,
    # then explicitly include immutable ledger endpoint below.
    i=int(np.searchsorted(ts,x['entry_ns'],'left'));j=int(np.searchsorted(ts,x['exit_ns'],'left'))
    if j<=i:continue
    v=x['direction']*(mid[i:j]-(x['entry_bid']+x['entry_ask'])/2);s=stats[x['id']];s['mfe_mid_ticks']=max(s['mfe_mid_ticks'],float(v.max()));s['mae_mid_ticks']=max(s['mae_mid_ticks'],float(-v.min()));s['valid_quote_rows']+=j-i
  profiles.append(pr)
 for x in rows:
  s=stats[x['id']];s['mfe_mid_ticks']=max(s['mfe_mid_ticks'],x['alpha_ticks']);s['mae_mid_ticks']=max(s['mae_mid_ticks'],-x['alpha_ticks']);assert s['valid_quote_rows']>0
 return stats,profiles

def run(inputs,out,tickroot=None):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);inputs=Path(inputs);manifest=json.load(open(inputs/'manifest.json'));dump(out/'manifest.json',manifest);pre={'script_sha256':sha(__file__),'input_sha256':{n:sha(inputs/n) for n in ['old_slots_PRIVATE.jsonl','new_slots_PRIVATE.jsonl','days.json']},'repo_modules':{str(f.relative_to(Path(__file__).parent/'repo')):sha(f) for f in (Path(__file__).parent/'repo').rglob('*.py')},'new_windows_opened':False,'holdout_opened':False,'source_commit':manifest['source_commit']};
 for name,h in manifest['input_sha256'].items():assert sha(inputs/name)==h
 for name,h in manifest['repo_module_sha256'].items():assert sha(Path(__file__).parent/'repo'/name)==h
 dump(out/'preflight.json',pre)
 check_holdout('2025-10-07T00:00:00Z','2025-12-31T23:59:59Z',purpose='development',caller='RTY_MOM_DEV_DIAGNOSTICS_V1',log_path=str(out/'holdout_guard.log'))
 days=json.load(open(inputs/'days.json'));allrows=load(inputs/'new_slots_PRIVATE.jsonl');old=load(inputs/'old_slots_PRIVATE.jsonl');assert len({x['id'] for x in allrows})==1224 and all(x['status']=='COMPLETE' and x['day'] in days for x in allrows)
 # Invoke actual firewall before any data, not just an output flag.
 cells={};rty=[]
 for family in ['MOM5','MOM15']:
  rows=[x for x in allrows if x['asset']=='RTY' and x['family']==family];cells[family]=summary(rows,days);rty.extend(rows)
 # Preserve all48 knownfullyobservablecells in temporal ratioPBO, not just RTY survivors.
 keys=[];cols=[]
 for prefix,data in [('EMA3',old),('CROSSMOM',allrows)]:
  for asset in ['MNQ','YM','RTY']:
   for family in sorted({x['family'] for x in data if x['asset']==asset}):
    for filt in next(x['filters'].keys() for x in data if x['asset']==asset and x['family']==family):
     selected=[x for x in data if x['asset']==asset and x['family']==family and x['filters'][filt]];keys.append(f'{prefix}_{asset}_{family}_{filt}');cols.append(selected)
 assert len(keys)==48
 matrix=[[g2_ratio.RatioCell(sum(x['net_U'] for x in col if x['day']==day),sum(x['day']==day for x in col)) for col in cols] for day in days]
 try:
  pb=g2_ratio.pbo_ratio_cscv(matrix);pbo_info={'status':'DIAGNOSTIC_ONLY','pbo':pb.pbo,'n_splits':pb.n_splits,'n_rows':pb.n_rows,'n_configs':pb.n_configs}
 except g2_ratio.RatioGateError as e:pbo_info={'status':'ABSTAIN_UNESTIMABLE_SUBSPLIT','reason':str(e),'n_configs':48}
 momidx=[i for i,k in enumerate(keys) if k.startswith('CROSSMOM_') and '_MOM' in k];assert len(momidx)==6
 pbmom=g2_ratio.pbo_ratio_cscv([[row[i] for i in momidx] for row in matrix])
 pbo_info.update(metric='sum_netU_over_n_trades',configs=keys,scope_gap='old6RTYscreen excluded: execution-censored/incompatible; remaininghistoricaltrialsunknown; NOTfullselectionaudit',momentum6_predeclared_diagnostic={'pbo':pbmom.pbo,'n_splits':pbmom.n_splits,'n_configs':6,'configs':[keys[i] for i in momidx],'NOT_full_campaign_selection':True})
 # Contract-walk-forward for fixed2momentumconfigs; dates already exposed, not freshOOS.
 folds=sorted({x['contract'] for x in rty},key=lambda c:min(x['signal_ns'] for x in rty if x['contract']==c));perfold={f:{c:g2_ratio.RatioCell(sum(x['net_U'] for x in rty if x['family']==f and x['contract']==c),sum(x['family']==f and x['contract']==c for x in rty)) for c in folds} for f in cells};wf=g2_ratio.walk_forward_ratio(perfold,folds)
 sens=g2.parameter_sensitivity({f:cells[f]['mean_net_U'] for f in cells},'MOM5',[])
 result={'study':manifest['study'],'RTY':cells,'PBO48_DIAGNOSTIC':pbo_info,'contract_WF_DIAGNOSTIC':{'mean_oos_U':wf.observed,'n_oos_trades':wf.total_n_trades,'selected_configs':[str(s.selected_config) for s in wf.selections],'folds':list(folds),'only_two_exposed_contracts':True,'NOT_fresh_OOS':True},'sensitivity':{'median':sens[0],'available_neighbors':sens[2],'status':'ABSTAIN_NO_PREREGISTERED_PARAM_GRID'},'promotion_authority':{'approved_contract_hash_count':len(APPROVED_G2_CONTRACT_SHA256S),'promotion_attempted':False},'formal_G2_status':'BLOCKED_54_LT160_AND_INCOMPLETE_AUTHORITY_PARITY_BUDGET','new_windows_opened':False,'holdout_opened':False,'live_ready':False}
 if tickroot:
  stats,profiles=paths_profile(rty,tickroot,manifest['tick_file_sha256']);dump(out/'trajectory_profiles.json',profiles)
  for family in cells:
   selected=[x for x in rty if x['family']==family];result['RTY'][family]['path_diagnostic']={'unit':'mid_ticks,notliquidation/fill/stopPnl','n':len(selected),'mfe_quantiles':list(map(float,np.quantile([stats[x['id']]['mfe_mid_ticks'] for x in selected],[.05,.25,.5,.75,.95]))),'mae_quantiles':list(map(float,np.quantile([stats[x['id']]['mae_mid_ticks'] for x in selected],[.05,.25,.5,.75,.95]))),'quote_age_certified':False}
 dump(out/'results.json',result);print('DONE',json.dumps({f:{'G1':v['G1_diagnostic_pass'],'max_contract_share':v['max_contract_fraction_total_net'],'top5remaining_ticks':v['top_trades']['5']['sum_remaining_ticks']} for f,v in cells.items()}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--out',required=True);p.add_argument('--ticks');a=p.parse_args();run(a.inputs,a.out,a.ticks)
