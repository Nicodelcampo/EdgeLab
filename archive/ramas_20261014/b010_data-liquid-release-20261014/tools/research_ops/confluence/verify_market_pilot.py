"""Bind aggregate market engineering receipts, not dataset QA or edge approval."""
import hashlib,json
from .build_target_free_pilot import digest

def verify(boot_bytes,pilot_bytes,*,package,plan,roster):
    boot=json.loads(boot_bytes);pilot=json.loads(pilot_bytes)
    def need(condition,message):
        if not condition:raise ValueError(message)
    need(boot['status']=='TARGET_FREE_MARKET_PILOT_COMPLETE_NOT_VALIDATED_EDGE','boot incomplete/failed')
    need(boot['source_commit']==package['source_commit'] and boot['bundle_sha256']==package['bundle_sha256'],'wrong code/bundle')
    need(boot['exit_code']==0 and boot['stop_reason'] is None,'budget or child failure')
    need(boot['pilot_receipt_sha256']==hashlib.sha256(pilot_bytes).hexdigest(),'pilot bytes do not match boot seal')
    need(boot['transport_pin_verified'] is True,'transport binding absent')
    need(pilot['status']=='TARGET_FREE_MARKET_PILOT_COMPLETE_NOT_VALIDATED_EDGE','pilot incomplete')
    need(pilot['source_pin']==plan['pin'] and pilot['plan_sha256']==digest(plan) and pilot['roster_sha256']==digest(roster),'wrong fixed source/plan/roster')
    need(pilot['contract']==plan['contract'] and pilot['target_session']==plan['target_session'],'wrong target scope')
    need(pilot['configs_completed']==96 and pilot['aligned_triads_completed']==32,'coverage incomplete')
    need(0<pilot['target_ticks']<=pilot['ticks_processed']<=plan['max_total_ticks'],'input budget/count')
    false_fields=('full_cartesian_coverage','arrival_labels_evaluated','occupancy_nulls_evaluated','outcomes_evaluated','pnl_computed','holdout_opened','source_quality_certified','raw_ticks_or_events_exported','selection_by_outcomes','canonical_brain_written','inference_or_edge_claim')
    need(all(pilot[k] is False for k in false_fields),'scope/claim expansion')
    need(all(boot[k] is False for k in ('holdout_opened','outcomes_computed','pnl_computed','raw_exported','source_quality_certified','new_dataset_quality_audit')),'boot scope/claim expansion')
    need(len(pilot['config_counts'])==96 and len(pilot['geometry_triads'])==32,'receipt rows incomplete')
    for c,row in zip(roster['configs'],pilot['config_counts']):
        need(row['config_sha256']==c['config_sha256'] and row['indicator']==c['indicator'] and row['bar_spec']==c['bar_spec'],'config row binding')
        all_counts=row['all_capture_counts'];target=row['target_capture_counts']
        need(set(all_counts)<=set(('BIRTH','TOUCH','REMOVE','CLASSIFY')),'unknown capture kind')
        need(all(type(n) is int and n>=0 for n in all_counts.values()),'invalid count')
        need(all(type(n) is int and 0<=n<=all_counts.get(k,0) for k,n in target.items()),'target count exceeds scope')
        need(len(row['ordered_private_capture_sha256'])==64,'capture seal absent')
    families={f:[c['config_sha256'] for c in roster['configs'] if c['indicator']==f] for f in ('avolzonepoi2','bigtrap2','bigtrap2absorption')}
    for i,row in enumerate(pilot['geometry_triads']):
        need(row['aligned_triad_index']==i and row['config_sha256']==[families[f][i] for f in families],'triad binding mismatch')
        need(all(type(v) is int and v>=0 for v in row['target_geometry_counts'].values()),'invalid geometry count')
    return {'schema':'mnq_confluence_market_output_binding_v1','status':'PASS_BOUNDED_TARGET_FREE_RECEIPTS_NOT_EDGE','source_commit':package['source_commit'],'bundle_sha256':package['bundle_sha256'],'boot_physical_bytes_sha256':hashlib.sha256(boot_bytes).hexdigest(),'pilot_physical_bytes_sha256':hashlib.sha256(pilot_bytes).hexdigest(),'plan_sha256':digest(plan),'roster_sha256':digest(roster),'coverage_checked_configs':96,'coverage_checked_aligned_triads':32,'source_quality_certified':False,'raw_data_or_events_downloaded':False,'outcomes_or_edge_verified':False,'interpretation':'GEOMETRIC_OPPORTUNITIES_ON_ONE_EXPLORATORY_TARGET_NOT_INDEPENDENT_TRIALS'}
