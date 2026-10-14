"""Independent scalar recomputation and neighborhood/leave-day-out sensitivity, not validation."""
import os,json,sqlite3,math,re
from pathlib import Path
from collections import defaultdict
from functools import lru_cache
import pandas as pd,numpy as np
P=Path('/data/analysis/avzvol-focus');C=os.environ.get('FOCUS_CONTRACT','MNQ_12-26');R=P/C;ev=json.load(open(R/'evidence.json'));reg=json.load(open(P/'manifest.json'));baseline=json.load(open(Path('/data/analysis/avzvol-longevity')/C/'manifest.json'));dates=baseline['event_dates'];nd=len(dates);dateid={d:i for i,d in enumerate(dates)};conditions=json.load(open(P/'conditions.json'));source=pd.read_csv(R/'supported-results.csv');candidate=source[source.approx_joint95_lower_points>0].sort_values(['approx_joint95_lower_points','matched_weight'],ascending=False);con=sqlite3.connect(R/'thinned-private.sqlite')
@lru_cache(maxsize=12)
def cohort(family,age,d,q,ep):return pd.read_sql_query('SELECT * FROM signals WHERE family=? AND landmark=? AND D=? AND q=? AND endpoint=?',con,params=(family,age,d,q,ep)).to_dict('records')
def scalar_gate(r,c):
 def finite(k):return r[k] is not None and math.isfinite(float(r[k]))
 if r['dedup75']!=1:return False
 s=c['speed']
 if s!='all' and (not finite('speed_ratio') or not (r['speed_ratio']>=1 if s=='return_ge_outgoing' else r['speed_ratio']<1)):return False
 s=c['efficiency']
 if s!='all' and (not finite('return_efficiency') or r['return_efficiency']<(.5 if s=='ge_0.50' else .75)):return False
 s=c['flow']
 if s!='all':
  if not finite('return_imbalance_proxy_toward') or not finite('proxy_coverage') or r['proxy_coverage']<.8:return False
  v=r['return_imbalance_proxy_toward'];ok=v>0 if s=='toward_positive_cov80' else v>=.25 if s=='toward_ge_0.25_cov80' else v<0 if s=='away_negative_cov80' else v<=-.25
  if not ok:return False
 s=c['revisits']
 if s!='all' and (not finite('visits1') or r['visits1']<int(s[3:])):return False
 s=c['volume']
 if s!='all' and (not finite('volume_inside_fraction') or r['volume_inside_fraction']<(.25 if s.endswith('0.25') else .5)):return False
 s=c['density']
 if s!='all':
  if not finite('return_bars_per_tick'):return False
  v=r['return_bars_per_tick'];ok=v<=.5 if s=='le_0.5' else v<=1 if s=='le_1' else v>1
  if not ok:return False
 if c['gaps']=='gap_free' and r['prior_gap_count']!=0:return False
 return True
def independent(family,age,d,q,ep,condition):
 a=cohort(family,age,d,q,ep);g=defaultdict(lambda:[[],[]]);rd=set();cd=set();rn=cn=0;triggers=set()
 for r in a:
  if not scalar_gate(r,condition) or r['status'] not in ['TARGET_FIRST','OPPOSITE_FIRST']:continue
  day=dateid[r['session']];o=0 if r['origin']=='real' else 1;win=int(r['status']=='TARGET_FIRST');span=min((r['volatility256_ticks'] if r['volatility256_ticks'] is not None else -40)//40,4);k=(day,int(r['hour'])//3,span,min(r['remaining_ticks']//10,8));g[k][o].append(win)
  if o==0:rn+=1;rd.add(day);triggers.add(int(r['trigger_idx']))
  else:cn+=1;cd.add(day)
 num=[0.]*nd;weights=[0.]*nd;common=0
 for k,(rr,cc) in g.items():
  if rr and cc:
   w=min(len(rr),len(cc));num[k[0]]+=w*(sum(rr)/len(rr)-sum(cc)/len(cc));weights[k[0]]+=w;common+=1
 total=sum(weights);effect=sum(num)/total if total else math.nan;score=[(n-effect*w)/total for n,w in zip(num,weights)] if total else [math.nan]*nd;se=math.sqrt(nd/(nd-1)*sum(s*s for s in score)) if total else math.nan;ok=rn>=100 and cn>=100 and min(len(rd),len(cd))>=math.ceil(.8*nd) and total>=50 and sum(w>0 for w in weights)>=math.ceil(.5*nd) and math.isfinite(se) and se>1e-12
 return dict(real_resolved=rn,control_resolved=cn,matched_weight=total,common_strata=common,effect=effect,se=se,eligible=ok,num=num,weights=weights,triggers=triggers)
def neighbors(row):
 f=row.family;age=int(row.landmark);d=int(row.D);q=float(row.q);ep=int(row.endpoint);out=set()
 for seq,val,axis in [(reg['age_landmarks'],age,'age'),([20,40,80],d,'D'),([.25,.5,.75],q,'q')]:
  i=seq.index(val)
  for j in [i-1,i+1]:
   if 0<=j<len(seq):
    aa=seq[j] if axis=='age' else age;dd=seq[j] if axis=='D' else d;qq=seq[j] if axis=='q' else q
    if any(r['D']==dd and r['q']==qq and r['endpoint']==ep for r in reg['rules']):out.add((f,aa,dd,qq,ep))
 match=re.fullmatch(r'P(.+)_W(.+)_R(.+)_(.+)_20',f);pct,w,minimum,look=match.groups()
 for seq,val,axis in [([8,18],int(minimum),'R'),([1000,2000,3000],int(look),'L')]:
  i=seq.index(val)
  for j in [i-1,i+1]:
   if 0<=j<len(seq):
    ff=f'P{pct}_W{w}_R{seq[j] if axis=="R" else minimum}_{seq[j] if axis=="L" else look}_20';assert ff in reg['families'];out.add((ff,age,d,q,ep))
 return sorted(out)
rows=[];clusters=[];union=set();neighbor_checks=0
for row in candidate.itertuples():
 condition=conditions[int(row.representative_condition_id)];m=independent(row.family,int(row.landmark),int(row.D),float(row.q),int(row.endpoint),condition)
 assert m['eligible'] and m['real_resolved']==row.real_resolved and m['control_resolved']==row.control_resolved and m['matched_weight']==row.matched_weight and m['common_strata']==row.common_strata;assert np.isclose(m['effect']*100,row.real_minus_control_points,atol=1e-9) and np.isclose(m['se']*100,row.standard_error_points,atol=1e-9)
 loo=[(sum(m['num'])-n)/(sum(m['weights'])-w) for n,w in zip(m['num'],m['weights']) if sum(m['weights'])>w];cut=int(nd*.6);earlier=sum(m['num'][:cut])/sum(m['weights'][:cut]) if sum(m['weights'][:cut]) else math.nan;later=sum(m['num'][cut:])/sum(m['weights'][cut:]) if sum(m['weights'][cut:]) else math.nan;near=[]
 for params in neighbors(row):
  mm=independent(*params,condition);neighbor_checks+=1;near.append(dict(family=params[0],age=params[1],D=params[2],q=params[3],endpoint=params[4],eligible=bool(mm['eligible']),difference_points=100*mm['effect'] if math.isfinite(mm['effect']) else None))
 eligible_near=[x for x in near if x['eligible']];pos=sum(x['difference_points']>0 for x in eligible_near);ratio=pos/len(eligible_near) if eligible_near else 0;priority=min(loo)>0 and earlier>0 and later>0 and len(eligible_near)>=2 and ratio>=.8;union|=m['triggers'];cluster=-1
 for j,old in enumerate(clusters):
  if len(old&m['triggers'])/len(old|m['triggers'])>=.8:cluster=j;break
 if cluster<0:cluster=len(clusters);clusters.append(m['triggers'])
 rows.append(dict(cohort_id=int(row.cohort_id),family=row.family,landmark=int(row.landmark),D=int(row.D),q=float(row.q),endpoint=int(row.endpoint),condition_id=int(row.representative_condition_id),condition=condition,independent_recount=True,matched_difference_points=100*m['effect'],approx_joint95_lower_points=float(row.approx_joint95_lower_points),real_resolved=m['real_resolved'],control_resolved=m['control_resolved'],matched_weight=m['matched_weight'],largest_matched_session_fraction=max(m['weights'])/sum(m['weights']),worst_delete_one_day_points=100*min(loo),earlier_points=100*earlier if math.isfinite(earlier) else None,later_points=100*later if math.isfinite(later) else None,eligible_neighbors=len(eligible_near),positive_eligible_neighbors=pos,review_priority=bool(priority),redundancy_cluster=cluster,neighbors=near,not_a_fresh_validation=True))
assert len(rows)==ev['positive_lower_bands_development_candidates_only'];out=dict(status='INDEPENDENT_CANDIDATE_REVIEW_COMPLETE',contract=C,screen_positive_cells=len(rows),all_independently_recounted=True,independent_neighbor_comparisons=neighbor_checks,greedy_Jaccard80pct_clusters=len(clusters),distinct_observed_real_trigger_union=len(union),not_independent_events_or_opportunities=True,review_priority_cells=sum(r['review_priority'] for r in rows),review_priority_clusters=len({r['redundancy_cluster'] for r in rows if r['review_priority']}),candidates=rows,assumption=f'postselection sensitivity on same previously inspected{nd}sessions; not holdout or strategy evidence');(R/'candidate-review-evidence.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');pd.DataFrame([{k:v for k,v in r.items() if k not in ['neighbors','condition']} for r in rows]).to_csv(R/'candidate-review.csv',index=False);print('CANDIDATE_REVIEW',C,len(rows),'CLUSTERS',len(clusters),'REVIEW_PRIORITY',out['review_priority_cells'],out['review_priority_clusters'],'NEIGHBORS',neighbor_checks,flush=True)
