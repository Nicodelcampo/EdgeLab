"""Aggregate-only science pilot checks; no private market data, inference or writes."""
import json,csv,hashlib
from pathlib import Path
from collections import Counter
from tools.research_ops.confluence.build_target_free_pilot import digest
import argparse
ap=argparse.ArgumentParser(description='Reproduce aggregate development response counts, not private-label validation or remote authentication')
ap.add_argument('--evidence-dir',type=Path,default=Path(__file__).resolve().parents[3]/'docs/research/ops')
ap.add_argument('--raw-dir',type=Path,help='Optional directory containing boot-receipt.json/science-receipt.json')
ap.add_argument('--out-dir',type=Path,required=True)
args=ap.parse_args();D=args.evidence_dir;O=args.out_dir;O.mkdir(parents=True,exist_ok=True)
def load(path):
    path=Path(path)
    if path.stat().st_size>1048576:raise ValueError('aggregate input cap')
    return json.loads(path.read_bytes())
def raw_file(name):
    if args.raw_dir:return args.raw_dir/name
    return D/('MNQ_PHENOMENA_SCIENCE_BOOT_RECEIPT.json' if name=='boot-receipt.json' else 'MNQ_PHENOMENA_SCIENCE_RECEIPT.json')
b=load(raw_file('boot-receipt.json'));a=load(raw_file('science-receipt.json'));p=load(D/'MNQ_PHENOMENA_SCIENCE_PACKAGE_RECEIPT.json');l=load(D/'MNQ_PHENOMENA_SCIENCE_LAUNCH.json');idc=load(D/'MNQ_PHENOMENA_SCIENCE_REMOTE_IDENTITY_CHECK.json');plan=load(D/'MNQ_PHENOMENA_SCIENCE_PILOT_PLAN.json')
assert b['exit_code']==0 and b['stop_reason'] is None and b['transport_pin_verified'] and b['outcomes_computed']
for k in ('source_commit','bundle_sha256','plan_sha256'):assert b[k]==p[k]==l['job'][k]
assert idc['exact_request_source_verified'] and idc['notebook_source_sha256']==p['notebook_text_sha256']
assert hashlib.sha256((raw_file('science-receipt.json')).read_bytes()).hexdigest()==b['science_receipt_sha256']
assert a['plan_sha256']==p['plan_sha256']==digest(plan)
assert a['training']['trade_date']==plan['training_session'] and a['training']['responses_read'] is False
assert [s['trade_date'] for s in a['evaluation_sessions']]==plan['evaluation_sessions']
c=a['calibration'];assert digest({k:v for k,v in c.items() if k!='sha256'})==c['sha256'] and c['outcomes_used'] is False
assert sum(x['anchors'] for x in c['cells'].values())==a['training']['calibration_eligible_anchors']
assert all(a[k] is False for k in ('source_quality_audit','training_outcomes_used','model_incremental_value_tested','inference','holdout_opened','pnl','raw_exported','private_rows_persisted','canonical_brain_written'))
assert a['total_ticks']==a['training']['measurement']['ticks']+sum(s['measurement']['ticks'] for s in a['evaluation_sessions'])
USABLE={'CONTINUATION_FIRST','REVERSAL_FIRST','HORIZON_NO_OBSERVED_PASSAGE'};STATES=['A_ONLY','E_ONLY','BOTH','NEITHER','UNKNOWN'];rows=[];pooled={s:Counter() for s in STATES};allanchors=0
for s in a['evaluation_sessions']:
 assert s['calibration_sha256']==c['sha256'];assert sum(s['state_counts'].values())==s['anchors'];allanchors+=s['anchors']
 assert sum(s['classification_reason_counts'].values())==s['anchors']
 assert sum(sum(v.values()) for g in s['calibration_cell_state_response_counts'].values() for v in g.values())==s['anchors']
 for state in STATES:
  z=s['state_response_counts'][state];total=sum(z.values());assert total==s['state_counts'][state];pooled[state].update(z);valid=sum(z.get(k,0) for k in USABLE)
  # Independent aggregation from phase/direction cells checks every status total.
  check=Counter()
  for g in s['calibration_cell_state_response_counts'].values():check.update(g[state])
  assert dict(check)==z
  row={'trade_date':s['trade_date'],'state':state,'anchors':total,'usable_responses':valid,'censored_or_unknown_response':total-valid,
       'continuation':z.get('CONTINUATION_FIRST',0),'reversal':z.get('REVERSAL_FIRST',0),'no_observed_passage':z.get('HORIZON_NO_OBSERVED_PASSAGE',0),
       'reversal_percent_among_usable':None if not valid else 100*z.get('REVERSAL_FIRST',0)/valid,
       'continuation_percent_among_usable':None if not valid else 100*z.get('CONTINUATION_FIRST',0)/valid,
       'no_passage_percent_among_usable':None if not valid else 100*z.get('HORIZON_NO_OBSERVED_PASSAGE',0)/valid,
       'censored_or_unknown_percent_of_state':None if not total else 100*(total-valid)/total}
  rows.append(row)
summary=[]
for state,z in pooled.items():
 total=sum(z.values());valid=sum(z.get(k,0) for k in USABLE)
 summary.append({'state':state,'anchors':total,'usable':valid,'censored_or_unknown':total-valid,'response_counts':dict(z),
                 'continuation_percent_among_usable':None if not valid else 100*z.get('CONTINUATION_FIRST',0)/valid,
                 'reversal_percent_among_usable':None if not valid else 100*z.get('REVERSAL_FIRST',0)/valid,
                 'no_passage_percent_among_usable':None if not valid else 100*z.get('HORIZON_NO_OBSERVED_PASSAGE',0)/valid,
                 'censored_or_unknown_percent_of_state':None if not total else 100*(total-valid)/total})
with (O/'phenomena_science_response_counts.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
assert sum(x['anchors'] for x in summary)==allanchors
assert a['response_scanned_elements']==sum(s['response_scanned_elements'] for s in a['evaluation_sessions'])<=plan['max_scan_elements_total']
by={(r['trade_date'],r['state']):r for r in rows};diffs=[by[(d,'A_ONLY')]['reversal_percent_among_usable']-by[(d,'NEITHER')]['reversal_percent_among_usable'] for d in plan['evaluation_sessions']]
assert diffs[0]<0<diffs[1]
e={'schema':'phenomena_science_aggregate_analysis_v1','status':'EXACT_RECEIPT_PLAN_AND_COUNTS_PASS_DESCRIPTIVE_NOT_EDGE','job':l['job'],'kernel_slug':l['kernel_slug'],'receipt_sha256':b['science_receipt_sha256'],'total_ticks':a['total_ticks'],'evaluation_anchors':allanchors,'host_wall_seconds':b['wall_seconds'],'retrieval_seconds':b['retrieval_seconds'],'runner_wall_seconds':a['wall_seconds'],'measured_runner_peak_rss_bytes':a['measured_runner_peak_rss_bytes'],'rss_scope':a['rss_scope'],'response_scanned_elements':a['response_scanned_elements'],'calibration':c,'pooled_states':summary,'per_session_state_responses':rows,'A_vs_NEITHER_raw_reversal_gaps_pp':diffs,'controls_are_unmatched_and_may_overlap':True,'classification_already_feature_developed':True,'only_two_evaluation_sessions':True,'independent_effect_estimation':False,'model_incremental_value_tested':False,'inference':False,'confirmation':False,'canonical_brain_written':False,
   'interpretation':'A_ONLY reversal rate is below NEITHER on June15 and above on June16. E_ONLY has roughly similar observed continuation/reversal pooled, no descriptive reversal dominance. These conditional rates are not matched effects; censoring and barriers differ and anchors overlap.',
   'classification_limit':'A stall net cap2ticks plus training-cell range/pathq25 is relative confinement, not flat price. Actual accepted range caps33-56.5ticks and path138-283.5ticks allow nontrivial excursions; do not silently rename physical absorption or tighten after results.',
   'profile_resolution':'Raw nested aggregate cannot be profiled as a flat table; derived10session/state rows retain genuine zero-state row and null percentages for zero usable/empty denominator. No imputation or drops.',
   'next_scientific_step':'Prespecify additional disjoint research sessions, continuous-component baseline and phase/activity/range/barrier covariates, episode/block dependence and minimum-session precision. Do not select threshold variants on these two response dates.'}
control_totals={};control_rows=[];cell_rows=[]
for ses in a['evaluation_sessions']:
 for tag,counts in ses['control_tag_response_counts'].items():
  total=sum(counts.values());valid=sum(counts.get(k,0) for k in USABLE)
  control_totals.setdefault(tag,Counter()).update(counts)
  control_rows.append({'trade_date':ses['trade_date'],'tag':tag,'anchors':total,'usable':valid,'reversal':counts.get('REVERSAL_FIRST',0),'continuation':counts.get('CONTINUATION_FIRST',0),'no_observed_passage':counts.get('HORIZON_NO_OBSERVED_PASSAGE',0),'censored_or_unknown':total-valid})
 for key,states in ses['calibration_cell_state_response_counts'].items():
  for state,counts in states.items():
   total=sum(counts.values());valid=sum(counts.get(k,0) for k in USABLE)
   cell_rows.append({'trade_date':ses['trade_date'],'phase_direction':key,'state':state,'anchors':total,'usable':valid,'reversal':counts.get('REVERSAL_FIRST',0),'continuation':counts.get('CONTINUATION_FIRST',0),'no_observed_passage':counts.get('HORIZON_NO_OBSERVED_PASSAGE',0),'censored_or_unknown':total-valid})
e['control_tags_by_session']=control_rows;e['phase_direction_state_counts']=cell_rows
e['control_tag_totals']=[{'tag':tag,'anchors':sum(v.values()),'usable':sum(v.get(k,0) for k in USABLE),'response_counts':dict(v)} for tag,v in control_totals.items()]
e['date_warning_resolution']='Date labels parsed by fixed ISO protocol; charts use chronological categorical sessions, not a trend or forecast. Null rates correspond to zero denominators. Profiler daily-rate hints are not independent sample rates; states are additive disjoint counts, tags are not.'
e['comparison_plan']=[{'grain':'two sessions×three classified states','population':'usable observed responses conditional per state','unit':'percent reversals','finding':'A versus NEITHER changes sign across sessions; no stable raw reversal advantage.','derivation':'100REVERSAL_FIRST/usable in same session/state','disposition':'chart','reason':'A pooled percentage hides the sign reversal.'},{'grain':'pooled state counts','population':'all evaluation anchors','unit':'anchors and usable/censored counts','finding':'A_ONLY88anchors/78usable, E_ONLY654/472, BOTH4/4; censusNEITHER andUNKNOWN retained.','derivation':'sum non-overlapping state counts across dates; not independent episodes','disposition':'table','reason':'Support and differing censoring prevent an unconditional or inferential reading.'},{'grain':'one pilot','population':'4.26Mticks of existing three sessions','unit':'seconds','finding':'Protocol including state calibration/response completed without full detector products.','derivation':'bootdirect timings','disposition':'prose','reason':'No speedup claim against different workloads.'}]
(O/'phenomena_science_evidence.json').write_text(json.dumps(e,indent=2)+'\n')
labels=['15/06','16/06'];series=[]
for state,label,role in [('A_ONLY','A proxy solamente','subject'),('E_ONLY','E proxy solamente','aux'),('NEITHER','Ni A ni E','base')]:
 series.append({'label':label,'role':role,'valueKind':'percent','data':[by[(d,state)]['reversal_percent_among_usable'] for d in plan['evaluation_sessions']]})
spec={'version':1,'form':'categorical-bars','mode':'grouped','title':'La reversión observada tras A proxy cambia entre sesiones','aside':'Junio2026; porcentaje entre respuestas utilizables por estado, sin igualar controles ni barreras','labels':labels,'tooltipLabels':[d+' · A n='+str(by[(d,'A_ONLY')]['usable_responses'])+', E n='+str(by[(d,'E_ONLY')]['usable_responses'])+', ni A/E n='+str(by[(d,'NEITHER')]['usable_responses']) for d in plan['evaluation_sessions']],
      'axis':{'zero':True,'cap':100},'derived':True,'derivationReason':'100REVERSAL_FIRST / (CONTINUATION_FIRST + REVERSAL_FIRST + HORIZON_NO_OBSERVED_PASSAGE), misma sesión y estado','series':series,'colorMap':{'A proxy solamente':'blue','E proxy solamente':'orange','Ni A ni E':'neutral'}}
(O/'phenomena_science_reversal_chart.json').write_text(json.dumps(spec))
print(json.dumps({'evaluation_anchors':allanchors,'host_seconds':b['wall_seconds'],'summary':summary,'A_raw_reversal_gaps_pp':diffs},indent=2))
