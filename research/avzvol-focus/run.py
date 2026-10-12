"""Finite focal feature search; no tick replay or baseline modification; common-support controls."""
import os,json,csv,gzip,sqlite3,hashlib,math,itertools,time
from pathlib import Path
import numpy as np,pandas as pd
from gates import collapse,matched,influence
P=Path('/data/analysis/avzvol-focus');C=os.environ.get('FOCUS_CONTRACT','MNQ_12-26');R=P/C;R.mkdir(exist_ok=True);L=Path('/data/analysis/avzvol-longevity')/C;reg=json.load(open(P/'manifest.json'));baseline=json.load(open(L/'manifest.json'));dates=baseline['event_dates'];nd=len(dates);day_lookup={d:i for i,d in enumerate(dates)};source=L/'signals-private.csv.gz';source=source if source.exists() else L/'signals-private.csv'
assert json.load(open(P/'test-evidence.json'))['status']=='PASS';assert json.load(open(L/'evidence.json'))['status']=='LONGEVITY_CONTRACT_COMPLETE';assert baseline.get('feature_schema_version')==2 or json.load(open(L/'schema-repair-evidence.json'))['status']=='PASS_REPAIRED_SCHEMA'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
t0=time.time();pin=sha(source);launch=dict(status='FOCAL_CONTRACT_RUNNING',contract=C,source_signals_sha256=pin,raw_source_sha256=baseline['source']['sha256'],registry_sha256=sha(P/'manifest.json'),condition_sha256=sha(P/'conditions.json'),code_sha256={n:sha(P/n) for n in ['run.py','gates.py','test_gates.py']},holdout_opened=False,pnl_computed=False);(R/'manifest.json').write_text(json.dumps(launch,indent=2)+'\n');print('FOCAL_START',C,flush=True)
fields=['family','origin','landmark','D','q','endpoint','session','zone_id','dedup75','trigger_idx','status','visits1','speed_ratio','return_efficiency','return_imbalance_proxy_toward','proxy_coverage','volume_inside_fraction','return_bars_per_tick','prior_gap_count','volatility256_ticks','remaining_ticks','hour'];keys=['family','origin','landmark','D','q','endpoint','session','bin'];cols=fields+['bin'];text={'family','origin','session','status'};db=R/'thinned-private.sqlite';con=sqlite3.connect(db);con.execute('PRAGMA cache_size=-32000');con.execute('PRAGMA journal_mode=DELETE');con.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT)');old=con.execute("SELECT value FROM meta WHERE key='source_sha256'").fetchone()
if old:assert old[0]==pin
else:con.execute("INSERT INTO meta VALUES('source_sha256',?)",(pin,));con.commit()
complete=con.execute("SELECT value FROM meta WHERE key='extract_complete'").fetchone()
if not complete:
 con.execute('DROP TABLE IF EXISTS signals');con.execute('CREATE TABLE signals ('+','.join('"'+k+'" '+('TEXT' if k in text else 'REAL') for k in cols)+',PRIMARY KEY('+','.join('"'+k+'"' for k in keys)+'))')
 placeholders=','.join('?' for _ in cols);updates=','.join('"'+k+'"=excluded."'+k+'"' for k in cols if k not in keys);sql='INSERT INTO signals VALUES('+placeholders+') ON CONFLICT('+','.join('"'+k+'"' for k in keys)+') DO UPDATE SET '+updates+' WHERE excluded.trigger_idx<signals.trigger_idx OR (excluded.trigger_idx=signals.trigger_idx AND excluded.zone_id<signals.zone_id)';read_rows=0
 for chunk in pd.read_csv(source,usecols=fields,chunksize=50000):
  assert chunk.hour.between(0,23).all() and chunk.visits1.notna().all();read_rows+=len(chunk);chunk=chunk[chunk.landmark.isin(reg['age_landmarks'])&chunk.family.isin(reg['families'])].copy();chunk['bin']=chunk.trigger_idx//6250;chunk=chunk.sort_values(['trigger_idx','zone_id'],kind='stable').drop_duplicates(keys);chunk=chunk[cols]
  con.executemany(sql,chunk.itertuples(index=False,name=None));con.commit()
 assert read_rows==json.load(open(L/'evidence.json'))['signal_rows_not_independent'];con.execute("INSERT OR REPLACE INTO meta VALUES('extract_complete','yes')");con.commit();print('THINNING_DONE',C,read_rows,con.execute('SELECT count(*) FROM signals').fetchone()[0],flush=True)
# Independent streamed verification for the fixed primary pilot against the existing baseline thinning.
if C=='MNQ_12-26':
 old=pd.read_csv(L/'primary-thinned-private.csv');old=old[old.landmark.isin(reg['age_landmarks'])];new=pd.read_sql_query("SELECT origin,landmark,endpoint,session,bin,trigger_idx,zone_id FROM signals WHERE family='P80_W5_R18_2000_20' AND D=40 AND q=.5",con);old['bin']=old.trigger_idx//6250;kk=['origin','landmark','endpoint','session','bin'];assert {tuple(r[k] for k in kk):(int(r.trigger_idx),int(r.zone_id)) for _,r in old.iterrows()}=={tuple(r[k] for k in kk):(int(r.trigger_idx),int(r.zone_id)) for _,r in new.iterrows()};print('INDEPENDENT_PRIMARY_THINNING_PASS',len(new),flush=True)
heads=['cohort_id','family','landmark','D','q','endpoint','representative_condition_id','condition_aliases','real_signals','control_signals','real_resolved','control_resolved','real_active_dates','control_active_dates','real_target_percent','control_target_percent','matched_weight','matched_active_dates','common_strata','real_minus_control_points','standard_error_points','eligible_for_joint_band'];details=[];eligible=[];scores=[];collapsed_total=0;nominal=0;cohorts=0;assert all(x in reg['gate_definitions'] for x in ['speed','efficiency','flow','revisits','volume','density','gaps'])
with gzip.open(R/'condition-results-private.csv.gz','wt',newline='',compresslevel=1) as out:
 writer=csv.DictWriter(out,fieldnames=heads);writer.writeheader()
 for family,age,rule in itertools.product(reg['families'],reg['age_landmarks'],reg['rules']):
  a=pd.read_sql_query('SELECT * FROM signals WHERE family=? AND landmark=? AND D=? AND q=? AND endpoint=? ORDER BY origin,session,trigger_idx,zone_id',con,params=(family,age,rule['D'],rule['q'],rule['endpoint']));cid=cohorts;cohorts+=1;nominal+=5400
  if len(a):
   day=a.session.map(day_lookup).to_numpy(np.int64);origin=a.origin.map({'real':0,'translated_geometry250':1}).to_numpy(np.int64);assert np.isin(origin,[0,1]).all();resolved=a.status.isin(['TARGET_FIRST','OPPOSITE_FIRST']).to_numpy();win=a.status.eq('TARGET_FIRST').to_numpy();strata=np.column_stack([day,a.hour.to_numpy(np.int64)//3,np.minimum(a.volatility256_ticks.fillna(-40).to_numpy()//40,4),np.minimum(a.remaining_ticks.to_numpy()//10,8)]);_,stratum=np.unique(strata,axis=0,return_inverse=True);states=collapse(a)
  else:states=[(np.zeros(0,bool),0,5400)]
  collapsed_total+=len(states)
  for mask,condition,aliases in states:
   d=dict(cohort_id=cid,family=family,landmark=age,D=rule['D'],q=rule['q'],endpoint=rule['endpoint'],representative_condition_id=condition,condition_aliases=aliases);num=np.zeros(nd);weight=np.zeros(nd);common=0
   if len(a):
    rs=mask&(origin==0);cs=mask&(origin==1);r=rs&resolved;c=cs&resolved;nreal=int(r.sum());ncontrol=int(c.sum());rrdays=int(np.unique(day[r]).size);ccdays=int(np.unique(day[c]).size);d.update(real_signals=int(rs.sum()),control_signals=int(cs.sum()),real_resolved=nreal,control_resolved=ncontrol,real_active_dates=rrdays,control_active_dates=ccdays,real_target_percent=100*win[r].mean() if nreal else '',control_target_percent=100*win[c].mean() if ncontrol else '')
    # Calculate matching even for unsupported cases, without claiming inference.
    if nreal and ncontrol:num,weight,common=matched(day,stratum,origin,win,mask&resolved,nd)
   else:nreal=ncontrol=rrdays=ccdays=0;d.update(real_signals=0,control_signals=0,real_resolved=0,control_resolved=0,real_active_dates=0,control_active_dates=0,real_target_percent='',control_target_percent='')
   point,se,score=influence(num,weight);ok=nreal>=100 and ncontrol>=100 and min(rrdays,ccdays)>=math.ceil(.8*nd) and weight.sum()>=50 and np.count_nonzero(weight)>=math.ceil(.5*nd) and np.isfinite(se) and se>1e-12;d.update(matched_weight=float(weight.sum()),matched_active_dates=int(np.count_nonzero(weight)),common_strata=common,real_minus_control_points=100*point if np.isfinite(point) else '',standard_error_points=100*se if np.isfinite(se) else '',eligible_for_joint_band=int(ok));writer.writerow(d)
   if ok:eligible.append(d.copy());scores.append(score/se)
  details.append(dict(cohort_id=cid,family=family,landmark=age,**rule,nominal_conditions=5400,distinct_paired_masks=len(states),source_thinned_signals=len(a)));out.flush()
  if cid%33==32:print('FOCAL_COHORTS',C,cohorts,'ELIGIBLE',len(eligible),'UNIQUE',collapsed_total,flush=True)
assert nominal==reg['nominal_event_condition_pairs_per_contract'] and cohorts==594;con.close();pd.DataFrame(details).to_csv(R/'cohort-coverage.csv',index=False)
# One simultaneous family across ALL supported unique masks in this focal pass.
if nd<=12:signs=np.array(list(itertools.product([-1.,1.],repeat=nd)),float)
else:signs=np.random.default_rng(reg['multiplier_seed']).choice([-1.,1.],(reg['multipliers'],nd))
maxima=np.zeros(len(signs));factor=np.sqrt(nd/(nd-1));z=np.array(scores)
if len(scores):
 for start in range(0,len(z),1024):maxima=np.maximum(maxima,np.max(np.abs(signs@z[start:start+1024].T)*factor,axis=1))
 critical=float(np.quantile(maxima,.95));rows=[]
 for d in eligible:
  d.update(approx_joint95_lower_points=d['real_minus_control_points']-critical*d['standard_error_points'],approx_joint95_upper_points=d['real_minus_control_points']+critical*d['standard_error_points'],development_only=True,other_contract_replication_required=True);rows.append(d)
 results=pd.DataFrame(rows);results.to_csv(R/'supported-results.csv',index=False);review=results.sort_values(['approx_joint95_lower_points','matched_weight','representative_condition_id'],ascending=[False,False,True]).head(50);review.to_csv(R/'review-candidates.csv',index=False);positive=int(results.approx_joint95_lower_points.gt(0).sum())
else:critical=None;positive=0;pd.DataFrame(columns=heads+['approx_joint95_lower_points','approx_joint95_upper_points']).to_csv(R/'supported-results.csv',index=False)
assert sha(source)==pin;out=dict(status='FOCAL_CONTRACT_EXPLORATION_COMPLETE',contract=C,baseline_unchanged=True,source_signals_sha256=pin,registry_version=2,base_cohorts=cohorts,nominal_event_condition_pairs=nominal,distinct_paired_masks=collapsed_total,supported_unique_hypotheses=len(eligible),unsupported_cases_not_declared_opportunities=collapsed_total-len(eligible),approx_joint95_critical=critical,multiplier_patterns=len(signs),positive_lower_bands_development_candidates_only=positive,joint_correction_scope='eligible unique masks in this focal contract pass ONLY, not all earlier research or original2million grid',band_assumptions=f'whole-session independent blocks, influence linearization, symmetric multiplier approximation; not exact finite-sample inference with{nd}sessions, not randomized control or causal effect',identical_masks_collapsed=True,no_outcome_threshold_fitting=True,prior_pilot_inspected=True,source_certified=False,virgin_holdout=False,pnl_computed=False,wall_seconds=time.time()-t0);(R/'evidence.json').write_text(json.dumps(out,indent=2)+'\n');print('FOCAL_COMPLETE',json.dumps(out),flush=True)
