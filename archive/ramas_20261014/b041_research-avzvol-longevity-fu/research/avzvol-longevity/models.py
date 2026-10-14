"""Fixed ridge-logit incremental diagnostic. Temporal split previously inspected, not a holdout."""
import os,json,math
from pathlib import Path
import numpy as np,pandas as pd
P=Path(os.environ['REPLICATION_ROOT']);C=os.environ['REPLICATION_CONTRACT'];m=json.load(open(P/'manifest.json'));dates=m['event_dates'];cut=int(len(dates)*.6);train_dates=dates[:cut];test_dates=dates[cut:];a=pd.read_csv(P/'primary-thinned-private.csv');a=a[a.origin.eq('real')&a.dedup75.eq(1)&a.landmark.isin([2000,3000])&a.endpoint.eq(0)&a.status.isin(['TARGET_FIRST','OPPOSITE_FIRST'])].sort_values(['landmark','zone_id']).drop_duplicates(['source_trigger_sequence']);train=a[a.session.isin(train_dates)].copy();test=a[a.session.isin(test_dates)].copy();status=dict(status='INCREMENTAL_DIAGNOSTIC_NOT_VIRGIN_HOLDOUT',contract=C,training_dates=train_dates,test_dates=test_dates,training_signals=len(train),test_signals=len(test),fixed_ridge_lambda=10,hyperparameter_tuning=False,source_certified=False,pnl_computed=False,multiplicity_corrected=False)
if len(train)<100 or len(test)<50 or train.status.nunique()<2:
 status.update(status='INSUFFICIENT_SUPPORT_FOR_INCREMENTAL_FIT',minimum_training=100,minimum_test=50)
else:
 for d in [train,test]:
  d['hour_sin']=np.sin(2*np.pi*d.hour/24);d['hour_cos']=np.cos(2*np.pi*d.hour/24);d['log_age']=np.log1p(d.age_bars);d['log_remaining']=np.log1p(d.remaining_ticks);d['log_span']=np.log1p(d.volatility256_ticks);d['log_visits']=np.log1p(d.visits1);d['speed_ratio']=d.speed_ratio.clip(0,5);d['log_recency']=np.log1p(d.recency_seconds)
 base=['log_age','log_remaining','log_span','hour_sin','hour_cos'];extra=['log_visits','volume_inside_fraction','speed_ratio','return_imbalance_proxy_toward','proxy_coverage','return_efficiency','log_recency'];y=train.status.eq('TARGET_FIRST').to_numpy(float);yy=test.status.eq('TARGET_FIRST').to_numpy(float);pred={};coeff={}
 for name,columns in [('context_only',base),('plus_revisits_volume_speed_flow',base+extra)]:
  tr=train[columns].replace([np.inf,-np.inf],np.nan);te=test[columns].replace([np.inf,-np.inf],np.nan);med=tr.median().fillna(0);missing=tr.isna().any();keep_missing=list(missing[missing].index);x=tr.fillna(med).to_numpy();z=te.fillna(med).to_numpy();mu=x.mean(axis=0);sd=x.std(axis=0);sd[sd==0]=1;x=(x-mu)/sd;z=(z-mu)/sd
  if keep_missing:x=np.column_stack([x,tr[keep_missing].isna().to_numpy(float)]);z=np.column_stack([z,te[keep_missing].isna().to_numpy(float)])
  x=np.column_stack([np.ones(len(x)),x]);z=np.column_stack([np.ones(len(z)),z]);w=np.zeros(x.shape[1]);pen=np.eye(len(w))*10;pen[0,0]=0
  for _ in range(30):
   pr=1/(1+np.exp(-np.clip(x@w,-30,30)));grad=x.T@(pr-y)+pen@w;h=x.T@((pr*(1-pr))[:,None]*x)+pen+np.eye(len(w))*1e-8;step=np.linalg.solve(h,grad);w-=step
   if np.max(np.abs(step))<1e-8:break
  p=1/(1+np.exp(-np.clip(z@w,-30,30)));pred[name]=p;coeff[name]=dict(feature_names=['intercept']+columns+[c+'_missing' for c in keep_missing],coefficients=w.tolist(),training_only_imputation_and_scaling=True)
  status[name]=dict(test_brier=float(np.mean((p-yy)**2)),test_log_loss=float(-np.mean(yy*np.log(p)+(1-yy)*np.log1p(-p))),test_signals=len(p),training_signals=len(train))
 delta=(pred['plus_revisits_volume_speed_flow']-yy)**2-(pred['context_only']-yy)**2;dd=np.array([[delta[test.session.eq(d)].sum(),test.session.eq(d).sum()] for d in test_dates]);rng=np.random.default_rng(17337);ix=rng.integers(0,len(test_dates),(10000,len(test_dates)));r=dd[ix].sum(axis=1);ok=r[:,1]>0;ci=np.quantile(r[ok,0]/r[ok,1],[.025,.975]);status['extended_minus_baseline_brier']=float(delta.mean());status['test_session_bootstrap95']=ci.tolist();status['interpretation']='negative Brier gap is better prediction in this diagnostic, not causal interest, certified edge, costs or virgin validation';status['coefficients']=coeff
(P/'incremental-model-diagnostic.json').write_text(json.dumps(status,indent=2,allow_nan=False)+'\n');print('INCREMENTAL',C,status['status'],len(train),len(test),status.get('extended_minus_baseline_brier'))
