"""Parameter-only broad cross-family roster; no market reader/dispatcher/outcomes.

Main pairs always AVOLZONEPOI2 x a BigTrap family. Existing native parameter
profiles are reused without choosing a winner from scores or observed density.
"""
import argparse,json
from pathlib import Path
from .build_target_free_pilot import digest

SELECTION={'avolzonepoi2':(2,0,5),'bigtrap2':(2,1,23),'bigtrap2absorption':(2,0,19)}
ROLES=('DENSE_PARAMETER_PROFILE_NOT_DENSITY_GUARANTEE','REFERENCE_STRICTER_PROFILE','DIFFERENT_SCALE_AND_RULE_PROFILE')


def build(source):
    if source.get('schema')!='mnq_confluence_target_free_pilot_roster_v1':raise ValueError('known parameter roster only')
    configs=[]
    for family,indices in SELECTION.items():
        items=[c for c in source['configs'] if c['indicator']==family]
        if len(items)!=32:raise ValueError('complete original32 per family')
        for i,role in zip(indices,ROLES):
            c=items[i];record={k:c[k] for k in ('indicator','bar_spec','params')}
            if digest(record)!=c['config_sha256']:raise ValueError('profile parameter hash mismatch')
            configs.append({**record,'config_sha256':c['config_sha256'],'original_family_index':i,'role':role})
    if len({c['config_sha256'] for c in configs})!=9:raise ValueError('nine distinct parameter profiles')
    avz=[c for c in configs if c['indicator']=='avolzonepoi2'];big=[c for c in configs if c['indicator']!='avolzonepoi2']
    pairs=[{'left_indicator':a['indicator'],'right_indicator':b['indicator'],'left_config_sha256':a['config_sha256'],'right_config_sha256':b['config_sha256'],'pair_sha256':digest([a['config_sha256'],b['config_sha256']])} for a in avz for b in big]
    result={'schema':'mnq_crossfamily_parameter_roster_v1','status':'PREPARED_NOT_LAUNCHED_NOT_COMPLETE_RUNTIME_PLAN','source_roster_sha256':digest(source),'configuration_selection':'FIXED_EXISTING_PARAMETER_PROFILES_NO_SCORE_OR_DENSITY_WINNER','configs':configs,'pairs':pairs,'config_count':9,'primary_pair_count':18,'unique_bar_specs':['tick:25','tick:200'],'unique_bt2a_tape_windows':[25,50],'principal_family_pairs':['AVZP2_X_BT2','AVZP2_X_BT2A'],'AVZ_racimo_primary_pairs':False,'BT2_BT2A_primary_pairs':False,'age_bins_seconds':[{'left':0,'right':20,'closed_right':True},{'left':20,'right':120,'closed_right':True},{'left':120,'right':600,'closed_right':True}],'primary_exposure_horizon_seconds':600,'exposure_horizon_is_measurement_scope_not_detector_pruning':True,'geometry_relations':['DISJOINT','EDGE_CONTACT','PARTIAL_OVERLAP','CONTAINMENT','IDENTICAL'],'arrival_direction':['FROM_BELOW','FROM_ABOVE','ALREADY_INSIDE','UNKNOWN'],'event_states':['BIRTH_RECOGNIZED','CONFLUENCE_RECOGNIZED','APPROACH','FIRST_OBSERVED_PRINT_TOUCH','SUBSEQUENT_OBSERVED_PRINT_TOUCH','GAP_THROUGH_WITHOUT_OBSERVED_TOUCH','NATIVE_INVALIDATION_OR_EXPIRY','EXPOSURE_END'],'state_or_scenario_cells_are_not_all_independent_tests':True,'cross_family_flow_geometry_interactions_requested':True,'full_cartesian_four_family_zone_graph':False,'approximate_NT8_parity_accepted_for_exploration':True,'near100_percent_NT8_parity_is_not_measured':True,'synthetic_fast_native_output_equivalence_required':True,'datasets_reaudited':False,'market_data_read':False,'new_results':False,'launched':False,'holdout_opened':False,'pnl':False,'canonical_brain_written':False,'unresolved_runtime_gates':['immutable source/session/train/eval split and budgets before outcomes','capacity-matched flow x geometry interactions and matched zone-free geometry null','generic per-config context indexes with native removals and measurement-age expiry separate','true observed-print touch queries without interpolation or touch-only population','BT2A shared native bucket preprocessing exact parity and measured cost','aggregate schema/support/census/cost receipts plus isolated package/negative tests','new durable single-attempt journal linked to latest terminal, never old batch reuse']}
    result['roster_sha256']=digest(result);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();target=Path(a.out)
    if target.exists():raise ValueError('new output path required; no silent replacement')
    target.write_text(json.dumps(build(json.loads(Path(a.source).read_bytes())),indent=2,ensure_ascii=False)+'\n');print('PREPARED9PROFILES18CROSS_FAMILY_PAIRS_NOT_LAUNCHED')

if __name__=='__main__':main()
