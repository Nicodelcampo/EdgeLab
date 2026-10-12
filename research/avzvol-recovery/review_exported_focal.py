"""Read-only independent SQL recount of an exported frozen focal run.
Usage: python review_exported_focal.py EXPORT_DIRECTORY
Private SQLite is an input only. The output is aggregate evidence, not edge validation.
"""
import collections,csv,hashlib,json,math,pathlib,sqlite3,sys
root=pathlib.Path(sys.argv[1]);load=lambda p:json.load(open(p));rows=lambda p:list(csv.DictReader(open(p)))
def digest(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
state=load(root/'campaign-status.json');C=state['contract'];F=root/'analysis'/'avzvol-focus'/C;L=root/'analysis'/'avzvol-longevity'/C
inventory={x['path']:x for x in load(root/'artifact-inventory.json')['artifacts']};verified=0
for p in (root/'analysis').rglob('*'):
 if p.is_file():
  pin=inventory[str(p.relative_to(root))];assert p.stat().st_size==pin['bytes'] and digest(p)==pin['sha256'];verified+=1
bank=load(root/'frozen-replication-bank.json');assert digest(root/'frozen-replication-bank.json')=='59184949160128b524c7a47290889d4bdf55c6c0ff214c8a7fc4eac411e0ee06'
assert state['status']=='LONGEVITY_FOCAL_COMPLETE_MATRIX_PENDING_NOT_VALIDATED_EDGE'
assert not any(state[x] for x in ['holdout_opened','pnl_computed','source_certified'])
le=load(L/'evidence.json');fe=load(F/'evidence.json');assert le['feature_schema_version']==2 and le['scope_leakage']==0
assert len(rows(L/'frequency.csv'))==le['configurations']==18
counts=rows(L/'rule-counts.csv');assert len(counts)==le['landmark_rule_groups']==2772
assert sum(int(float(x['signals'])) for x in counts)==le['signal_rows_not_independent']
assert fe['nominal_event_condition_pairs']==3207600 and fe['base_cohorts']==594
dates=load(L/'manifest.json')['event_dates'];nd=len(dates);assert nd==le['selected_sessions']
con=sqlite3.connect('file:'+str(F/'thinned-private.sqlite')+'?mode=ro',uri=True);con.execute('PRAGMA query_only=ON')
def recount(recipe):
 c=recipe['condition'];where=['family=?','landmark=?','D=?','q=?','endpoint=?','dedup75=1',"status IN ('TARGET_FIRST','OPPOSITE_FIRST')"]
 params=[recipe[k] for k in ['family','landmark','D','q','endpoint']]
 if c['speed']!='all':
  assert c['speed'] in ['return_ge_outgoing','return_lt_outgoing'];where.append('speed_ratio>=1' if c['speed']=='return_ge_outgoing' else 'speed_ratio<1')
 for axis,field,options in [('efficiency','return_efficiency',{'ge_0.50':.5,'ge_0.75':.75}),('revisits','visits1',{'ge_5':5,'ge_10':10,'ge_20':20,'ge_50':50}),('volume','volume_inside_fraction',{'ge_0.25':.25,'ge_0.50':.5})]:
  if c[axis]!='all':where.append(field+'>=?');params.append(options[c[axis]])
 if c['flow']!='all':
  assert c['flow']=='away_negative_cov80';where+=['proxy_coverage>=0.8','return_imbalance_proxy_toward<0']
 if c['density']!='all':where.append({'le_0.5':'return_bars_per_tick<=0.5','le_1':'return_bars_per_tick<=1','gt_1':'return_bars_per_tick>1'}[c['density']])
 if c['gaps']!='observed':assert c['gaps']=='gap_free';where.append('prior_gap_count=0')
 sql="""SELECT session,CAST(hour/3 AS INT),min(CAST(COALESCE(volatility256_ticks,-40)/40 AS INT),4),min(CAST(remaining_ticks/10 AS INT),8),origin,count(*),sum(status='TARGET_FIRST') FROM signals WHERE """+' AND '.join(where)+' GROUP BY 1,2,3,4,5'
 strata=collections.defaultdict(dict);totals=collections.Counter();wins=collections.Counter()
 for session,hour,vol,distance,origin,n,w in con.execute(sql,params):strata[(session,hour,vol,distance)][origin]=(n,w);totals[origin]+=n;wins[origin]+=w
 num=dict.fromkeys(dates,0.);weights=dict.fromkeys(dates,0.)
 for key,sides in strata.items():
  if 'real' in sides and 'translated_geometry250' in sides:
   nr,wr=sides['real'];nc,wc=sides['translated_geometry250'];w=min(nr,nc);num[key[0]]+=w*(wr/nr-wc/nc);weights[key[0]]+=w
 total=sum(weights.values());effect=sum(num.values())/total if total else None
 se=math.sqrt(nd/(nd-1)*sum(((num[d]-effect*weights[d])/total)**2 for d in dates)) if total else None
 return dict(real_resolved=totals['real'],control_resolved=totals['translated_geometry250'],matched_weight=total,difference_points=effect*100 if total else None,standard_error_points=se*100 if total else None,real_target_first=wins['real'])
review=load(F/'candidate-review-evidence.json');recounted=[]
for recipe in review['candidates']:
 m=recount(recipe)
 for key in ['real_resolved','control_resolved','matched_weight']:assert m[key]==recipe[key]
 assert math.isclose(m['difference_points'],recipe['matched_difference_points'],abs_tol=1e-8)
 lower=m['difference_points']-fe['approx_joint95_critical']*m['standard_error_points'];assert math.isclose(lower,recipe['approx_joint95_lower_points'],abs_tol=1e-8) and lower>0
 recounted.append({k:recipe[k] for k in ['family','landmark','D','q','endpoint','condition_id','condition','review_priority']}|m)
supported=rows(F/'supported-results.csv');assert len(supported)==fe['supported_unique_hypotheses']
assert sum(float(x['approx_joint95_lower_points'])>0 for x in supported)==len(recounted)==review['screen_positive_cells']
absolute=rows(F/'absolute-and-control-results.csv');assert len(absolute)==len(supported);both=0
for row in absolute:
 passed=float(row['absolute_joint95_lower'])>50 and float(row['matched_joint95_lower'])>0;assert passed==(row['passes_both_exploratory_bands'].lower()=='true');both+=passed
assert both==load(F/'absolute-and-control-evidence.json')['absolute_and_control_positive_cells']
bankrows={r['recipe_id']:r for r in rows(F/'fixed-bank-results.csv')};assert len(bankrows)==len(bank['recipes'])==34
for recipe in bank['recipes']:
 m=recount(recipe);r=bankrows[str(recipe['recipe_id'])]
 for key in ['real_resolved','control_resolved','matched_weight']:assert math.isclose(m[key],float(r[key]),abs_tol=1e-8)
 if m['matched_weight']:assert math.isclose(m['difference_points'],float(r['difference_points']),abs_tol=1e-8)
con.close()
evidence=dict(status='PASS_EXPORTED_FOCAL_INDEPENDENT_SQL_RECOUNT',contract=C,verified_artifact_count=verified,selected_sessions=nd,families=18,landmark_rule_groups=2772,focal_definitions=3207600,signal_rows_not_independent=le['signal_rows_not_independent'],supported_unique_masks=len(supported),matched_positive_candidates=len(recounted),priority_candidates=sum(x['review_priority'] for x in recounted),absolute_and_control_positive_cells=both,bank_recipes_independently_recounted=34,candidates=recounted,source_certified=False,holdout_opened=False,pnl_computed=False,validated_edge=False,qualification='Exploratory, previously inspected sessions; within-contract approximate bands only. Private thinned SQLite independently grouped via SQL, not reusing the scientific gate or reviewer functions. Unknown gates fail closed.',profiler_warning_disposition='Constant eligibility/development/contract flags are expected by construction, not cleaning exclusions.')
(root/'independent-review.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in evidence.items() if k!='candidates'},indent=2))
