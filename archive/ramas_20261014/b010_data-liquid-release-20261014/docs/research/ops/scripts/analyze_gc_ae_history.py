from pathlib import Path
import json,hashlib,math
import pandas as pd
raw=Path('/data/raw/gc-ae-history-AE');out=Path('/data/analysis/gc-ae-history');r=json.loads((raw/'ae-history-receipt.json').read_bytes());boot=json.loads((raw/'boot-receipt.json').read_bytes());review=json.loads((out/'review.json').read_bytes())
sessions=r['evaluation_sessions'];rows=[]
for s in sessions:
 for family in ('STATE','DURATION','ALL'):
  means=s['whole_population']['mean_brier'];a=means['PROXY:'+family];c=means['CAPACITY:'+family];base=means['HISTORY']
  rows.append({'trade_date':s['trade_date'],'family':family,'common_usable_anchors':s['common_usable_anchors'],'proxy_brier':a,'history_brier':base,'capacity_brier':c,'proxy_minus_history_x1000':(a-base)*1000,'proxy_minus_capacity_x1000':(a-c)*1000})
df=pd.DataFrame(rows);assert len(df)==len(sessions)*3;assert not df.duplicated(['trade_date','family']).any();df.to_csv(out/'session_ablations.csv',index=False)
contrasts={}
for family in ('STATE','DURATION','ALL'):
 a=df.loc[df.family==family];original=r['baseline_equal_session_brier'];dh=(original['PROXY:'+family]-original['HISTORY'])*1000;dc=(original['PROXY:'+family]-original['CAPACITY:'+family])*1000
 assert math.isclose(dh,a.proxy_minus_history_x1000.sum()/len(a),abs_tol=1e-10);assert math.isclose(dc,a.proxy_minus_capacity_x1000.sum()/len(a),abs_tol=1e-10)
 contrasts[family]={'minus_history_x1000':dh,'minus_capacity_x1000':dc,'sessions_better_than_history':int((a.proxy_minus_history_x1000<0).sum()),'sessions_better_than_capacity':int((a.proxy_minus_capacity_x1000<0).sum()),'session_minus_history_range_x1000':[float(a.proxy_minus_history_x1000.min()),float(a.proxy_minus_history_x1000.max())]}
census={}
for phase in ('training_sessions','evaluation_sessions'):
 ss=r[phase];states={k:sum(s['state_counts_before_labels'].get(k,0) for s in ss) for k in ('A_ONLY','E_ONLY','BOTH','NEITHER','UNKNOWN')};n=sum(s['observed_anchors'] for s in ss);assert sum(states.values())==n
 # Independently recount A_ONLY count without the state-column aggregation route.
 assert states['A_ONLY']==sum(v for s in ss for k,v in s['state_counts_before_labels'].items() if k=='A_ONLY')
 transitions={k:sum(s['observed_transition_counts_before_labels'][k] for s in ss) for k in ('A_TO_E','E_TO_A')}
 census[phase]={'sessions':len(ss),'observed_anchors_before_labels':n,'state_counts':states,'common_usable_anchors':sum(s['common_usable_anchors'] for s in ss),'direct_transition_counts':transitions}
assert all(x==0 for phase in census.values() for x in phase['direct_transition_counts'].values())
assert all(r['primary_results'][f]['all_usable']['anchors']==0 for f in ('A_TO_E','E_TO_A'))
seconds={'runner':r['wall_seconds'],'host_including_source_transport':boot['wall_seconds'],'measurement':r['measurement_seconds'],'fit':r['fit_seconds'],'score':r['scoring_seconds']}
known=census['evaluation_sessions']['observed_anchors_before_labels']-census['evaluation_sessions']['state_counts']['UNKNOWN'];assert known==sum(census['evaluation_sessions']['state_counts'][k] for k in ('A_ONLY','E_ONLY','BOTH','NEITHER'))
e={'schema':'gc_ae_history_analysis_v1','status':'PRIMARY_INCONCLUSIVE_NO_DIRECT_TRANSITION_SUPPORT','receipt_sha256':hashlib.sha256((raw/'ae-history-receipt.json').read_bytes()).hexdigest(),'independent_aggregate_review':review,'census':census,'all_primary_results':r['primary_results'],'secondary_equal_session_ablations':contrasts,'missing_evaluation_dates':[s['trade_date'] for s in r['unavailable_evaluation_sessions']],'timings_seconds':seconds,'total_ticks':r['total_ticks'],'sampled_child_peak_rss_bytes':boot['sampled_child_peak_rss_bytes'],'hypothesis_conclusion':'NO_TESTABLE_DIRECT_A_TO_E_OR_E_TO_A_POPULATION_UNDER_THIS_PROXY_DEFINITION;NOT_PHYSICAL_ABSENCE_OR_PROFITABILITY_RESULT','absorption_proxy_support_caveat':'A_ONLY only2 anchors in evaluation and2 in training; strict conjunction/calibration transporting July31 likely support bottleneck; receipts do not decompose which conjunct failed. Do not assign specific cause without new target-free diagnostics.','primary_estimability':False,'secondary_not_rescue':True,'chart_plan':[{'comparison':'STATE/DURATION/ALL proxy minus same HISTORY/capacity','grain':'equal-session mean over9available evaluation sessions','population':'same common usable anchors within each session across14models','unit':'Delta sum-three-class Brier times1000','finding':'All3secondary average deltas positive versus both comparators; positive=worse, not significance','disposition':'chart','reason':'compact diagnostic comparison with common scored population; does not replace primary support stop'},{'comparison':'A_TO_E/E_TO_A primary and A_ONLY support','grain':'observed anchors before future labels','population':'same explicit9available eval calendar, prelabel denominator preserved','unit':'anchors, not independent events','finding':'zero direct transitions both directions; absorptionproxyonly2anchors','disposition':'prose','reason':'three small counts communicate support failure directly'}],'no_new_dataset_validation':True,'canonical_brain_written':False,'holdout_opened':False,'pnl':False,'edge_claim':False}
(out/'analysis.json').write_text(json.dumps(e,indent=2)+'\n')
labels=['Estado','Duración','Estado + duración + transiciones'];families=['STATE','DURATION','ALL']
spec={'version':1,'form':'categorical-bars','mode':'grouped','title':'Estado y duración no mejoran la pérdida media','aside':'Δ Brier ×1000; positivo = peor. Medias por sesión en9sesionesGC; mismas anclas por comparador. Diagnóstico secundario: ambos primarios sin soporte.','labels':labels,'series':[{'label':'Proxy − misma historia','role':'base','valueKind':'number','data':[contrasts[k]['minus_history_x1000'] for k in families]},{'label':'Proxy − control de capacidad','role':'subject','valueKind':'number','data':[contrasts[k]['minus_capacity_x1000'] for k in families]}],'axis':{'zero':True}}
assert all(v>0 for s in spec['series'] for v in s['data']);(out/'chart-spec.json').write_text(json.dumps(spec))
print(json.dumps({'census':census,'secondary':contrasts,'missing':e['missing_evaluation_dates'],'timings':seconds},indent=2))
