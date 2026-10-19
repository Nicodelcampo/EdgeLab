"""Independent bounded aggregate arithmetic/census, not private tick/NT8 audit."""
import argparse,json,math,hashlib
from pathlib import Path
from .review_crossfamily_models import close,group
from ..confluence.multiasset_crossfamily import validate_plan
from ..confluence.cross_family_design import MODELS,COUNTS
from ..confluence.cross_family_pilot import COMPARISONS
from ..confluence.build_target_free_pilot import digest

def review(r,p,asset):
 a,roster=validate_plan(p,asset)
 if r['schema']!='multiasset_crossfamily_receipt_v1' or r['status']!='DEVELOPMENT_CROSSFAMILY_COMPLETE_NOT_EDGE' or r['asset']!=asset or r['plan_sha256']!=digest(p) or r['roster_sha256']!=p['roster_sha256'] or r['tick_size']!=a['tick_size']:raise ValueError('immutable asset result identity')
 for k in ('confirmation','holdout_opened','pnl','edge_claim','raw_exported','canonical_brain_written','automatic_model_selection','overlapping_anchors_independent','near100_percent_NT8_parity_measured','detector_history_or_active_state_shared','native_AVZ_liveness_measured','physical_first_touch_measured','zone_specific_attribution'):
  if r[k] is not False:raise ValueError('no expanded asset claims')
 if r['approximate_parity_exploration_accepted'] is not True or r['bt2a_bucket_preprocessing_shared'] is not True or r['model_feature_counts']!=COUNTS or r['models_including_shared_baselines']!=146 or r['primary_pairs']!=18 or r['native_configs']!=9:raise ValueError('fixed exploratory representations')
 if p['max_gap_ns']!=2000000000 and (r.get('observation_max_gap_ns')!=p['max_gap_ns'] or r.get('observation_gap_relaxed_vs_original') is not True):raise ValueError('explicit changed observation estimand')
 c=r['calibration']
 if c['training_trade_date']!=p['calibration_date'] or c['outcomes_used'] is not False or digest({k:v for k,v in c.items() if k!='sha256'})!=c['sha256'] or r['calibration_sha256']!=c['sha256']:raise ValueError('earlier asset only calibration')
 tr=r['training_sessions'];ev=r['evaluation_sessions'];dates=[s['trade_date'] for s in ev];missing=[s['trade_date'] for s in r['unavailable_evaluation_sessions']]
 if [s['trade_date'] for s in tr]!=p['training_sessions'] or dates!=[d for d in p['evaluation_sessions'] if d in dates] or len(set(dates))!=len(dates) or missing!=[d for d in p['evaluation_sessions'] if d not in dates] or len(ev)<p['minimum_available_evaluation_sessions'] or r['available_evaluation_session_count']!=len(ev):raise ValueError('fixed original asset calendar')
 if any(s['replacement_selected'] is not False or s['status'] not in ('SOURCE_EMPTY_NO_REPLACEMENT','INSUFFICIENT_COMMON_SUPPORT_NO_REPLACEMENT') for s in r['unavailable_evaluation_sessions']):raise ValueError('no replacement dates')
 ids=[z['pair_sha256'] for z in roster['pairs']]
 if [z['pair_sha256'] for z in r['pairs']]!=ids:raise ValueError('all18assetpairs')
 for s in tr+ev:
  n=s['common_usable_anchors'];meta=s['crossfamily_context']
  if n<100 or meta['common_anchors']!=n or len(meta['pair_counts'])!=18:raise ValueError('same usable anchor census')
  for counts in meta['pair_counts']:
   if counts['anchors']!=n or sum(v for k,v in counts.items() if k.startswith('relation:'))!=n or not 0<=counts['inside_both']<=counts['both_present']<=n:raise ValueError('common scenario census')
  if s['native_scene']['whole_session_event_store'] is not False or s['native_scene']['peak_pending_mutation_records']>p['max_pending_mutation_records']:raise ValueError('bounded pending storage')
  if s in tr:continue
  if [z['pair_sha256'] for z in s['pairs']]!=ids:raise ValueError('same pair order')
  for z in s['pairs']:
   g=z['scores'];group(g)
   if g['anchors']!=n:raise ValueError('same model anchor population')
   for name in ('PRIOR','CONTINUOUS'):close(g['mean_brier'][name],s['baseline_mean_brier'][name])
   for x,y in COMPARISONS:close(z['paired_deltas'][x+'_MINUS_'+y],g['mean_brier'][x]-g['mean_brier'][y])
   for cuts in (z['phase_direction_scores'],z['proxy_state_scores']):
    if sum(v['anchors'] for v in cuts.values())!=n:raise ValueError('exclusive cut population')
    for v in cuts.values():group(v)
    for name in g['mean_brier']:close(sum(v['anchors']*v['mean_brier'][name] for v in cuts.values())/n,g['mean_brier'][name])
   for v in z['scenario_scores'].values():group(v)
   if sum(z['scenario_scores'].get(k,{'anchors':0})['anchors'] for k in ('NO_LOCAL_JOINT','LOCAL_JOINT_NOT_INSIDE_BOTH','INSIDE_BOTH'))!=n:raise ValueError('exclusive occupancy')
 for j,z in enumerate(r['pairs']):
  for name in ('PRIOR','CONTINUOUS')+MODELS:close(z['mean_session_brier'][name],sum(s['pairs'][j]['scores']['mean_brier'][name] for s in ev)/len(ev))
  for x,y in COMPARISONS:close(z['paired_delta_equal_session_mean'][x+'_MINUS_'+y],sum(s['pairs'][j]['paired_deltas'][x+'_MINUS_'+y] for s in ev)/len(ev))
 if len(r['arrival_context_summaries'])!=18:raise ValueError('all18arrival summaries')
 for cuts in r['arrival_context_summaries']:
  if len(cuts)>17:raise ValueError('fixed17arrival cuts')
  for g in cuts.values():
   n=g['anchors'];ss=g['support_sessions']
   if not 0<ss<=len(ev) or not 0<=g['arrival_improved_sessions']<=ss or n<ss:raise ValueError('arrival cut support')
   for name in ('CONTINUOUS','ARRIVAL','ARRIVAL_CC'):
    close(g['mean_brier_pooled'][name],g['loss_sums'][name]/n)
    if not 0<=g['mean_brier_pooled'][name]<=2:raise ValueError('bounded arrival Brier')
   if g['support_screen_passed_not_edge']!=(n>=p['scenario_min_pooled_anchors'] and ss>=p['scenario_min_sessions']):raise ValueError('predeclared support screen')
 for name in ('PRIOR','CONTINUOUS'):close(r['baseline_mean_session_brier'][name],sum(s['baseline_mean_brier'][name] for s in ev)/len(ev))
 for name,lim in (('wall_seconds','wall_seconds'),('measured_runner_peak_rss_bytes','rss_bytes'),('total_ticks','max_total_ticks'),('response_scanned_elements','max_scan_elements_total'),('context_query_hits','max_total_context_query_hits'),('print_queries','max_total_print_queries'),('print_level_queries','max_total_print_level_queries')):
  if not 0<=r[name]<=p[lim]:raise ValueError('bounded asset runtime')
 return {'schema':'multiasset_aggregate_review_v1','status':'PASS_PUBLIC_AGGREGATES_NOT_TICK_OR_NT8_PARITY','asset':asset,'plan_sha256':digest(p),'evaluation_sessions':len(ev),'primary_pairs_checked':18,'asset_local_earlier_calibration_checked':True,'crossasset_or_prior_MNQ_same_population_claimed':False,'new_inference':False,'edge_claim':False,'canonical_brain_written':False}

def main():
 p=argparse.ArgumentParser();[p.add_argument('--'+k,required=True) for k in ('receipt','plan','asset','out')];a=p.parse_args();read=lambda f:json.loads(Path(f).read_bytes());r=review(read(a.receipt),read(a.plan),a.asset);r['receipt_sha256']=hashlib.sha256(Path(a.receipt).read_bytes()).hexdigest();Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
