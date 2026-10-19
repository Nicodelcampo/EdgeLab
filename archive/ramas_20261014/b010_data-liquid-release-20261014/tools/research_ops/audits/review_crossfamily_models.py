"""Independent public-aggregate census and arithmetic review, not tick/NT8 audit."""
import argparse,json,math,hashlib
from pathlib import Path
from ..confluence.build_target_free_pilot import digest
from ..confluence.cross_family_pilot import validate_plan,COMPARISONS
from ..confluence.cross_family_design import MODELS,COUNTS
from ..confluence.phenomena_models import TRAIN,EVAL

def close(a,b):
 if type(a) not in (int,float) or type(b) not in (int,float) or not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>1e-12:raise ValueError('aggregate arithmetic mismatch')
def group(g):
 n=g['anchors']
 if type(n) is not int or n<1 or len(g['response_counts'])!=3 or any(type(v) is not int or v<0 for v in g['response_counts']) or sum(g['response_counts'])!=n:raise ValueError('common class census')
 if set(g['mean_brier'])!=set(('PRIOR','CONTINUOUS')+MODELS):raise ValueError('all fixed models, no selected winners')
 for v in g['mean_brier'].values():
  if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=2:raise ValueError('finite three-class Brier')
def review(r,plan,roster,baseline=None):
 validate_plan(plan,roster)
 if r['status']!='DEVELOPMENT_CROSSFAMILY_COMPLETE_NOT_EDGE' or r['plan_sha256']!=digest(plan) or r['roster_sha256']!=roster['roster_sha256'] or r['calibration_sha256']!=plan['calibration_sha256'] or r['model_feature_counts']!=COUNTS or r['models_including_shared_baselines']!=146:raise ValueError('exact immutable identity/design')
 for flag in ('confirmation','new_inference','edge_claim','holdout_opened','pnl','raw_exported','canonical_brain_written','automatic_model_selection','overlapping_anchors_independent','zone_specific_attribution','physical_first_touch_measured','native_AVZ_liveness_measured','rows_or_snapshots_persisted','retained_pair_graph','bt2a_bucket_preprocessing_shared'):
  if r[flag] is not False:raise ValueError('no expanded scientific/operational claims')
 if r['evaluation_outcomes_previously_inspected'] is not True or r['primary_pairs']!=18 or r['native_configs']!=9 or r['profile_views_per_anchor']!=18:raise ValueError('fixed scope')
 tr=r['training_sessions'];ev=r['evaluation_sessions'];dates=[s['trade_date'] for s in ev];missing=[s['trade_date'] for s in r['unavailable_evaluation_sessions']]
 if [s['trade_date'] for s in tr]!=list(TRAIN) or dates!=[d for d in EVAL if d in dates] or len(set(dates))!=len(dates) or missing!=[d for d in EVAL if d not in dates] or len(ev)!=r['available_evaluation_session_count'] or len(ev)<plan['minimum_available_evaluation_sessions'] or r['requested_evaluation_sessions']!=list(EVAL):raise ValueError('fixed original calendar no replacement')
 if any(s['replacement_selected'] is not False for s in r['unavailable_evaluation_sessions']):raise ValueError('no replacement dates')
 ids=[p['pair_sha256'] for p in roster['pairs']]
 if [p['pair_sha256'] for p in r['pairs']]!=ids:raise ValueError('all18 final comparisons')
 for s in tr+ev:
  n=s['common_usable_anchors'];meta=s['crossfamily_context']
  if meta['common_anchors']!=n or len(meta['pair_counts'])!=18:raise ValueError('same common population')
  for p in meta['pair_counts']:
   if p['anchors']!=n or sum(v for k,v in p.items() if k.startswith('relation:'))!=n or not 0<=p['inside_both']<=p['both_present']<=n:raise ValueError('scenario census not touch-only population')
  if s in tr:continue
  if [p['pair_sha256'] for p in s['pairs']]!=ids:raise ValueError('all pairs same order')
  for p in s['pairs']:
   g=p['scores'];group(g)
   if g['anchors']!=n:raise ValueError('one common population per pair')
   for name in ('PRIOR','CONTINUOUS'):close(g['mean_brier'][name],s['baseline_mean_brier'][name])
   for a,b in COMPARISONS:close(p['paired_deltas'][a+'_MINUS_'+b],g['mean_brier'][a]-g['mean_brier'][b])
   for cuts in (p['phase_direction_scores'],p['proxy_state_scores']):
    if sum(c['anchors'] for c in cuts.values())!=n:raise ValueError('exclusive group census')
    for c in cuts.values():group(c)
    for j in range(3):
     if sum(c['response_counts'][j] for c in cuts.values())!=g['response_counts'][j]:raise ValueError('exclusive class census')
    for name in g['mean_brier']:close(sum(c['anchors']*c['mean_brier'][name] for c in cuts.values())/n,g['mean_brier'][name])
   for c in p['scenario_scores'].values():group(c)
   occupancy=[p['scenario_scores'].get(k,{'anchors':0}) for k in ('NO_LOCAL_JOINT','LOCAL_JOINT_NOT_INSIDE_BOTH','INSIDE_BOTH')]
   relation=[c for k,c in p['scenario_scores'].items() if k.startswith('NEAREST_RELATION:')]
   if sum(c['anchors'] for c in occupancy)!=n or sum(c['anchors'] for c in relation)!=n:raise ValueError('exclusive scenario censuses')
 for j,p in enumerate(r['pairs']):
  for name in ('PRIOR','CONTINUOUS')+MODELS:close(p['mean_session_brier'][name],sum(s['pairs'][j]['scores']['mean_brier'][name] for s in ev)/len(ev))
  for a,b in COMPARISONS:close(p['paired_delta_equal_session_mean'][a+'_MINUS_'+b],sum(s['pairs'][j]['paired_deltas'][a+'_MINUS_'+b] for s in ev)/len(ev))
 for name in ('PRIOR','CONTINUOUS'):close(r['baseline_mean_session_brier'][name],sum(s['baseline_mean_brier'][name] for s in ev)/len(ev))
 baseline_checked=False
 if baseline is not None:
  previous={s['trade_date']:s for s in baseline['evaluation_sessions']}
  if set(previous)!=set(dates):raise ValueError('same previous observed calendar')
  for s in ev:
   old=previous[s['trade_date']]
   if s['common_usable_anchors']!=old['common_usable_anchors'] or s['common_state_counts']!=old['common_state_counts'] or s['common_response_counts']!=old['common_response_counts']:raise ValueError('baseline population changed')
   for name in ('PRIOR','CONTINUOUS'):close(s['baseline_mean_brier'][name],old['scores']['mean_brier'][name])
  baseline_checked=True
 for key,limit in (('total_ticks','max_total_ticks'),('response_scanned_elements','max_scan_elements_total'),('context_query_hits','max_total_context_query_hits'),('print_queries','max_total_print_queries'),('print_level_queries','max_total_print_level_queries'),('wall_seconds','wall_seconds'),('measured_runner_peak_rss_bytes','rss_bytes')):
  if not 0<=r[key]<=plan[limit]:raise ValueError('bounded resource receipt')
 return {'schema':'crossfamily_aggregate_review_v1','status':'PASS_PUBLIC_AGGREGATE_CENSUS_ARITHMETIC_NOT_PRIVATE_TICK_OR_NT8_PARITY','plan_sha256':digest(plan),'available_evaluation_sessions':len(ev),'primary_pairs_checked':18,'models_including_shared_baselines':146,'prior_population_and_baseline_checked':baseline_checked,'new_inference':False,'edge_claim':False,'canonical_brain_written':False}

def main():
 p=argparse.ArgumentParser();[p.add_argument('--'+k,required=True) for k in ('receipt','plan','roster','out')];p.add_argument('--baseline');a=p.parse_args();read=lambda name:json.loads(Path(name).read_bytes());r=review(read(a.receipt),read(a.plan),read(a.roster),read(a.baseline) if a.baseline else None);r['receipt_sha256']=hashlib.sha256(Path(a.receipt).read_bytes()).hexdigest();Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
