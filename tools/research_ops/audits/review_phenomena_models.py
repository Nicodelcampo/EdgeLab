"""Review exported aggregates only. No private predictions, market or authority."""
import argparse,json,hashlib,math
from pathlib import Path
import numpy as np
from tools.research_ops.confluence.phenomena_models import TRAIN,EVAL,MODELS,CAL_SHA,FEATURES
from tools.research_ops.confluence.phenomena_model_pilot import validate_plan
from tools.research_ops.confluence.build_target_free_pilot import digest

def review(boot,receipt,plan,package,receipt_bytes):
 validate_plan(plan)
 if package['plan_sha256']!=digest(plan):raise ValueError('package plan binding')
 for k in ('source_commit','bundle_sha256','plan_sha256'):
  if boot.get(k)!=package[k]:raise ValueError('immutable package/boot mismatch: '+k)
 if boot.get('status')!='DEVELOPMENT_MODEL_COMPLETE_NOT_EDGE' or boot.get('exit_code')!=0 or boot.get('stop_reason') is not None or boot.get('outcomes_computed') is not True:raise ValueError('successful exact boot required')
 if boot.get('model_receipt_sha256')!=hashlib.sha256(receipt_bytes).hexdigest():raise ValueError('physical model receipt SHA')
 if receipt.get('schema')!='mnq_phenomena_model_available_receipt_v1' or receipt.get('status')!='DEVELOPMENT_BENCHMARK_COMPLETE_FOR_AVAILABLE_PRESELECTED_SESSIONS_NOT_EDGE' or receipt['plan_sha256']!=digest(plan) or receipt['calibration_sha256']!=CAL_SHA or receipt['feature_names']!=list(FEATURES):raise ValueError('fixed scientific receipt identity')
 for k in ('new_inference','confirmation','holdout_opened','pnl','raw_exported','private_rows_persisted','canonical_brain_written','a_e_mechanisms_identified','automatic_model_selection','overlapping_anchors_independent'):
  if receipt.get(k) is not False:raise ValueError('scientific limits: '+k)
 if receipt.get('training_outcomes_previously_inspected') is not True:raise ValueError('honest development label')
 tr,ev=receipt['training_sessions'],receipt['evaluation_sessions']
 unavailable=receipt['unavailable_evaluation_sessions'];missing=[s['trade_date'] for s in unavailable]
 if len(missing)!=len(set(missing)) or any(s!={'trade_date':s['trade_date'],'status':'SOURCE_EMPTY_NO_TICKS_IN_EXACT_PRESELECTED_RANGE','replacement_selected':False,'response_read':False} for s in unavailable):raise ValueError('closed unavailable session census')
 if receipt['requested_evaluation_sessions']!=list(EVAL) or any(d not in EVAL for d in missing) or receipt['available_evaluation_session_count']!=len(ev) or len(ev)<6 or receipt['original_strict12_protocol_succeeded'] is not False:raise ValueError('honest availability-qualified coverage')
 if [s['trade_date'] for s in tr]!=list(TRAIN) or [s['trade_date'] for s in ev]!=[d for d in EVAL if d not in missing]:raise ValueError('all fixed dates accounted without replacement')
 def integer(n):return type(n) is int and n>=0
 def scorecheck(sc,n):
  if sc['anchors']!=n or set(sc['mean_brier'])!=set(MODELS):raise ValueError('shared score population')
  if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=2+1e-12 for v in sc['mean_brier'].values()):raise ValueError('Brier in [0,2]')
 for s in tr+ev:
  n=s['common_usable_anchors'];a=s['anchors']
  if not integer(n) or n<100 or not integer(a) or a>plan['max_anchors'] or s['ticks']>plan['max_session_ticks'] or s['response_scanned_elements']>plan['max_scan_elements_per_session']:raise ValueError('bounded session support')
  for k in ('classification_state_counts','excluded_counts','labeled_response_counts','common_state_counts','common_response_counts'):
   if any(not integer(v) for v in s[k].values()):raise ValueError('integer count census')
  if sum(s['classification_state_counts'].values())!=a or sum(s['excluded_counts'].values())+n!=a or sum(s['common_state_counts'].values())!=n or sum(s['common_response_counts'].values())!=n:raise ValueError('aggregate crossfoot')
  if s in ev:
   scorecheck(s['scores'],n)
   for k in ('phase_direction_scores','proxy_state_scores'):
    groups=s[k]
    if sum(g['anchors'] for g in groups.values())!=n:raise ValueError('group score census')
    for g in groups.values():scorecheck(g,g['anchors'])
    for model in MODELS:
     independently=sum(g['anchors']*g['mean_brier'][model] for g in groups.values())/n
     if not math.isclose(independently,s['scores']['mean_brier'][model],abs_tol=1e-12):raise ValueError('independent group loss reconciliation')
   for key,base in (('paired_delta_AE_minus_CONTINUOUS','CONTINUOUS'),('paired_delta_AE_minus_CC','CONTINUOUS_CC')):
    if not math.isclose(s[key],s['scores']['mean_brier']['CONTINUOUS_AE']-s['scores']['mean_brier'][base],abs_tol=1e-12):raise ValueError('paired loss difference')
   if len(s['feature_mean'])!=len(FEATURES) or not np.isfinite(s['feature_mean']).all() or len(s['feature_outside_training_range_fraction'])!=len(FEATURES) or any(not math.isfinite(v) or not 0<=v<=1 for v in s['feature_outside_training_range_fraction']):raise ValueError('feature drift aggregates')
 if sum(s['ticks'] for s in tr+ev)!=receipt['total_ticks'] or receipt['total_ticks']>plan['max_total_ticks'] or sum(s['response_scanned_elements'] for s in tr+ev)!=receipt['response_scanned_elements'] or receipt['response_scanned_elements']>plan['max_scan_elements_total']:raise ValueError('total finite budgets')
 expected={'PRIOR':0,'CONTINUOUS':len(FEATURES),'CONTINUOUS_CC':len(FEATURES)+2,'CONTINUOUS_A':len(FEATURES)+1,'CONTINUOUS_E':len(FEATURES)+1,'CONTINUOUS_AE':len(FEATURES)+2}
 if receipt['model_feature_counts']!=expected or receipt['scored_model_count']!=6:raise ValueError('capacity matching')
 expected_prior=[sum(s['common_response_counts'][v]/s['common_usable_anchors'] for s in tr)/len(tr) for v in ('CONTINUATION_FIRST','REVERSAL_FIRST','HORIZON_NO_OBSERVED_PASSAGE')]
 if not np.allclose(expected_prior,receipt['training_equal_session_prior'],rtol=0,atol=1e-12):raise ValueError('training-only equal session prior')
 means={m:sum(s['scores']['mean_brier'][m] for s in ev)/len(ev) for m in MODELS}
 for m,v in means.items():
  if not math.isclose(v,receipt['mean_session_brier'][m],abs_tol=1e-12):raise ValueError('equal session headline independently reconciled')
 return {'schema':'phenomena_model_aggregate_review_v1','status':'PASS_AGGREGATE_RECONCILIATION_NOT_INDEPENDENT_MARKET_RECOUNT','plan_sha256':digest(plan),'calibration_sha256':CAL_SHA,'training_dates':list(TRAIN),'requested_evaluation_dates':list(EVAL),'evaluation_dates':[s['trade_date'] for s in ev],'unavailable_evaluation_dates':missing,'mean_session_brier':means,'sessions':[{'trade_date':s['trade_date'],'common_usable_anchors':s['common_usable_anchors'],'AE_minus_CONTINUOUS':s['paired_delta_AE_minus_CONTINUOUS'],'AE_minus_CC':s['paired_delta_AE_minus_CC'],'scores':s['scores']['mean_brier']} for s in ev],'AE_better_than_CONTINUOUS_sessions':sum(s['paired_delta_AE_minus_CONTINUOUS']<0 for s in ev),'AE_better_than_CC_sessions':sum(s['paired_delta_AE_minus_CC']<0 for s in ev),'inference':False,'confirmation':False,'canonical_brain_written':False,'limitations':['Development features informed by earlier inspected outcomes','Overlapping anchors; equal-session score does not establish independence','Conditioned on common usable events; censoring is not corrected','Fixed linear ridge benchmark and two smooth capacity terms; not all nonlinear models','Same contract/nearby dates; not a validated trading edge or physical mechanism; conditional on available preselected sessions']}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(__file__).resolve().parents[3];d=root/'docs/research/ops';raw=Path(a.raw_dir);b=(raw/'model-receipt.json').read_bytes()
 result=review(json.loads((raw/'boot-receipt.json').read_bytes()),json.loads(b),json.loads((d/'MNQ_PHENOMENA_MODEL_PLAN.json').read_bytes()),json.loads((d/'MNQ_PHENOMENA_MODEL_PACKAGE_RECEIPT.json').read_bytes()),b);Path(a.out).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
