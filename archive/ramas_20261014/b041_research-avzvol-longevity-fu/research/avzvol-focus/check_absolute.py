"""All supported masks: absolute equal-barrier target rate AND matched-control difference."""
import os,json,sqlite3,itertools,math
from pathlib import Path
import numpy as np,pandas as pd
from gates import collapse,matched,influence
P=Path('/data/analysis/avzvol-focus');C=os.environ.get('FOCUS_CONTRACT','MNQ_12-26');R=P/C;baseline=json.load(open(Path('/data/analysis/avzvol-longevity')/C/'manifest.json'));dates=baseline['event_dates'];nd=len(dates);di={d:i for i,d in enumerate(dates)};supported=pd.read_csv(R/'supported-results.csv');reg=json.load(open(P/'manifest.json'));con=sqlite3.connect(R/'thinned-private.sqlite');rows=[];scores=[]
for key,g in supported.groupby(['family','landmark','D','q','endpoint']):
 family,age,d,q,ep=key;a=pd.read_sql_query('SELECT * FROM signals WHERE family=? AND landmark=? AND D=? AND q=? AND endpoint=?',con,params=(family,int(age),int(d),float(q),int(ep)));day=a.session.map(di).to_numpy(np.int64);origin=a.origin.map({'real':0,'translated_geometry250':1}).to_numpy(np.int64);resolved=a.status.isin(['TARGET_FIRST','OPPOSITE_FIRST']).to_numpy();win=a.status.eq('TARGET_FIRST').to_numpy();ss=np.column_stack([day,a.hour.to_numpy(np.int64)//3,np.minimum(a.volatility256_ticks.fillna(-40).to_numpy()//40,4),np.minimum(a.remaining_ticks.to_numpy()//10,8)]);_,strata=np.unique(ss,axis=0,return_inverse=True);lookup=g.set_index('representative_condition_id')
 for mask,cid,aliases in collapse(a):
  if cid not in lookup.index:continue
  old=lookup.loc[cid];r=mask&(origin==0)&resolved;weights=np.bincount(day[r],minlength=nd);wins=np.bincount(day[r],weights=win[r],minlength=nd);nr=int(weights.sum());p,se,score=influence(wins,weights);assert nr==old.real_resolved and np.isclose(100*p,old.real_target_percent)
  num,matchedweights,_=matched(day,strata,origin,win,mask&resolved,nd);delta,dse,dscore=influence(num,matchedweights);assert np.isclose(delta*100,old.real_minus_control_points) and np.isclose(dse*100,old.standard_error_points)
  if not np.isfinite(se) or se<=1e-12:continue
  scores.extend([score/se,dscore/dse]);rows.append(dict(family=family,landmark=int(age),D=int(d),q=float(q),endpoint=int(ep),condition_id=int(cid),real_resolved=nr,real_target_first=int(wins.sum()),real_target_percent=100*p,absolute_se_percent=100*se,matched_difference_points=100*delta,matched_se_points=100*dse))
con.close();signs=np.array(list(itertools.product([-1.,1.],repeat=nd)),float) if nd<=12 else np.random.default_rng(reg['multiplier_seed']).choice([-1.,1.],(reg['multipliers'],nd));maxima=np.zeros(len(signs));z=np.array(scores);factor=np.sqrt(nd/(nd-1))
if len(scores):
 for start in range(0,len(z),1024):maxima=np.maximum(maxima,np.max(np.abs(signs@z[start:start+1024].T)*factor,axis=1))
 critical=float(np.quantile(maxima,.95))
else:critical=None
for row in rows:
 row.update(absolute_joint95_lower=row['real_target_percent']-critical*row['absolute_se_percent'],absolute_joint95_upper=row['real_target_percent']+critical*row['absolute_se_percent'],matched_joint95_lower=row['matched_difference_points']-critical*row['matched_se_points'],matched_joint95_upper=row['matched_difference_points']+critical*row['matched_se_points']);row['passes_both_exploratory_bands']=bool(row['absolute_joint95_lower']>50 and row['matched_joint95_lower']>0)
result=pd.DataFrame(rows);result.to_csv(R/'absolute-and-control-results.csv',index=False);bank=json.load(open(P/'frozen-replication-bank.json'));recipes=[]
for recipe in bank['recipes']:
 found=[r for r in rows if r['family']==recipe['family'] and r['landmark']==recipe['landmark'] and r['D']==recipe['D'] and r['q']==recipe['q'] and r['endpoint']==recipe['endpoint'] and r['condition_id']==recipe['condition_id']]
 # Exact condition IDs can become aliases in another contract; don't silently infer an absent result.
 recipes.append(dict(recipe_id=recipe['recipe_id'],**found[0]) if found else dict(recipe_id=recipe['recipe_id'],status='MASK_ALIAS_OR_INSUFFICIENT_SUPPORT_REQUIRES_FIXED_SCALAR_RECOUNT',passes_both_exploratory_bands=False))
out=dict(status='ABSOLUTE_AND_CONTROL_FAMILY_CHECK_COMPLETE',contract=C,supported_masks_recounted=len(rows),joint_statistic_count=len(scores),approx_within_contract_joint95_critical=critical,absolute_and_control_positive_cells=sum(r['passes_both_exploratory_bands'] for r in rows),frozen_bank_recipes_passing_both=sum(r['passes_both_exploratory_bands'] for r in recipes),fixed_bank_results=recipes,qualification=f'allsupported masks jointly test absolute target probability versus50and matched real-control difference versus0; approximate{nd}-session influence/multiplier bands, NOT exact finite-sample/FWER guarantee, virgin validation, causal interest or executable advantage; adjustment is local to this contract/pass',bank_not_reselected=True);(R/'absolute-and-control-evidence.json').write_text(json.dumps(out,indent=2)+'\n');print('ABSOLUTE_AND_CONTROL',C,len(rows),out['absolute_and_control_positive_cells'],out['frozen_bank_recipes_passing_both'],flush=True)
