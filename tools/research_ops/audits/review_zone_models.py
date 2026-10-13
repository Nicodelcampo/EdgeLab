"""Review hashes and aggregate census/scores only, not private ticks or NT8 parity."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from tools.research_ops.confluence.zone_model_pilot import validate_plan
from tools.research_ops.confluence.zone_model_design import MODELS,FEATURE_COUNTS
from tools.research_ops.confluence.phenomena_models import TRAIN,EVAL
from tools.research_ops.confluence.build_target_free_pilot import digest


def near(a,b):
    if type(a) not in (int,float) or not math.isfinite(a) or not math.isclose(a,b,rel_tol=0,abs_tol=1e-12):
        raise ValueError('aggregate numerical reconciliation')


def review(boot,result,plan,package,raw,*,baseline=None):
    validate_plan(plan)
    for k in ('source_commit','bundle_sha256','plan_sha256'):
        if boot.get(k)!=package[k]:raise ValueError('package identity mismatch')
    if package['plan_sha256']!=digest(plan) or result['plan_sha256']!=digest(plan):raise ValueError('immutable plan identity')
    if boot.get('status')!='DEVELOPMENT_ZONE_COMPLETE_NOT_EDGE' or boot.get('exit_code')!=0 or boot.get('stop_reason') is not None or boot.get('outcomes_computed') is not True:
        raise ValueError('not successful terminal benchmark')
    if boot.get('zone_receipt_sha256')!=hashlib.sha256(raw).hexdigest():raise ValueError('zone receipt SHA mismatch')
    if result.get('calibration_sha256')!=plan['calibration_sha256']:raise ValueError('frozen calibration identity')
    if result.get('status')!='DEVELOPMENT_ZONE_BENCHMARK_COMPLETE_NOT_EDGE':raise ValueError('wrong scientific scope')
    for k in ('confirmation','new_inference','edge_claim','holdout_opened','pnl','raw_exported','canonical_brain_written','automatic_model_selection','overlapping_anchors_independent','rows_or_snapshots_persisted','retained_pair_graph','sqlite_capture_store','native_zone_liveness_measured','first_touch_measured','bt2_or_bt2a_computed','zone_specific_attribution'):
        if result.get(k) is not False:raise ValueError('scope guard not false')
    if result.get('evaluation_outcomes_previously_inspected') is not True or result['model_feature_counts']!=FEATURE_COUNTS:raise ValueError('development/capacity disclosure')
    tr=result['training_sessions'];ev=result['evaluation_sessions'];un=result['unavailable_evaluation_sessions']
    if [s['trade_date'] for s in tr]!=list(TRAIN):raise ValueError('training census')
    dates=[s['trade_date'] for s in ev];empty=[s['trade_date'] for s in un]
    if dates!=sorted(dates) or empty!=sorted(empty) or len(set(dates+empty))!=len(EVAL) or set(dates+empty)!=set(EVAL) or len(ev)<6 or result['available_evaluation_session_count']!=len(ev):raise ValueError('available original calendar census')
    if result['requested_evaluation_sessions']!=list(EVAL):raise ValueError('requested calendar changed')
    for s in un:
        if s['status']!='SOURCE_EMPTY_NO_TICKS_IN_EXACT_PRESELECTED_RANGE' or s['replacement_selected'] is not False:raise ValueError('empty not replaced')
    total_common=0
    for s in tr+ev:
        n=s['common_usable_anchors']
        if type(n) is not int or n<100 or s['anchors']!=n+sum(s['excluded_counts'].values()) or sum(s['classification_state_counts'].values())!=s['anchors'] or sum(s['common_state_counts'].values())!=n or sum(s['common_response_counts'].values())!=n or s['zone_context']['common_anchors']!=n:raise ValueError('common population census')
        if not all(0<=x<=n for x in s['zone_context']['nearest_present_anchors'].values()):raise ValueError('nearest support census')
        if s in ev:
            total_common+=n;score=s['scores']
            if score['anchors']!=n or set(score['mean_brier'])!=set(MODELS):raise ValueError('same anchors all seven models')
            for value in score['mean_brier'].values():
                if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=2:raise ValueError('bounded Brier')
            for key,value in s['paired_deltas'].items():
                l,r=key.split('_MINUS_');near(value,score['mean_brier'][l]-score['mean_brier'][r])
            for grouping in ('phase_direction_scores','proxy_state_scores'):
                groups=s[grouping]
                if sum(g['anchors'] for g in groups.values())!=n:raise ValueError('exclusive group census')
                for model in MODELS:near(sum(g['anchors']*g['mean_brier'][model] for g in groups.values())/n,score['mean_brier'][model])
    for model in MODELS:near(result['mean_session_brier'][model],sum(s['scores']['mean_brier'][model] for s in ev)/len(ev))
    if result['total_ticks']!=result['warmup_ticks']+sum(s['ticks'] for s in tr+ev):raise ValueError('read-once tick census')
    if result['response_scanned_elements']!=sum(s['response_scanned_elements'] for s in tr+ev):raise ValueError('response scan census')
    if result['context_query_hits']!=sum(s['zone_context']['context_query_hits'] for s in tr+ev) or result['context_query_hits']>plan['max_total_context_query_hits']:raise ValueError('context query budget census')
    if baseline is not None:
        old={s['trade_date']:s for s in baseline['training_sessions']+baseline['evaluation_sessions']}
        if [s['trade_date'] for s in baseline['evaluation_sessions']]!=dates:raise ValueError('baseline dates drift')
        for s in tr+ev:
            prev=old[s['trade_date']]
            for k in ('ticks','anchors','common_usable_anchors','common_response_counts','common_state_counts','excluded_counts'):
                if s[k]!=prev[k]:raise ValueError('prior v4 population drift')
            if s in ev:
                for model in ('PRIOR','CONTINUOUS'):near(s['scores']['mean_brier'][model],prev['scores']['mean_brier'][model])
    return {'schema':'mnq_zone_context_aggregate_review_v1','status':'PASS_AGGREGATE_HASH_CENSUS_AND_SCORES_NOT_PRIVATE_TICK_RECOUNT',
            'plan_sha256':digest(plan),'zone_receipt_sha256':hashlib.sha256(raw).hexdigest(),'available_evaluation_sessions':len(ev),
            'common_evaluation_anchors':total_common,'prior_v4_population_and_baseline_scores_equal':baseline is not None,
            'native_parity_percent_certified':False,'raw_exported':False,'inference':False,'edge_claim':False}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',required=True);ap.add_argument('--plan',required=True);ap.add_argument('--package-receipt',required=True);ap.add_argument('--out',required=True);ap.add_argument('--baseline')
    x=ap.parse_args();r=Path(x.raw_dir);raw=(r/'zone-receipt.json').read_bytes()
    result=review(json.loads((r/'boot-receipt.json').read_bytes()),json.loads(raw),json.loads(Path(x.plan).read_bytes()),json.loads(Path(x.package_receipt).read_bytes()),raw,baseline=json.loads(Path(x.baseline).read_bytes()) if x.baseline else None)
    Path(x.out).write_text(json.dumps(result,indent=2)+'\n');print(result['status'])

if __name__=='__main__':main()
