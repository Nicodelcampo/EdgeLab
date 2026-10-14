"""Check this proposed design's metadata only; never read market data or authorize a run.

The catalog is a candidate inventory, not an implemented runner or approved protocol.
This checker deliberately rejects every execution/approval flag. It is not an
experiment admission gate, source certificate, parity test, or scientific review.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

EXPECTED_COUNTS = {'avolzonepoi2':1728, 'racimo':48, 'bigtrap2':2880, 'bigtrap2absorption':17280}

def check_metadata(spec):
    if not isinstance(spec, dict) or spec.get('schema') != 'mnq_dense_confluence_design_v1':
        raise ValueError('not this design schema')
    if spec.get('status') != 'DESIGN_ONLY_NOT_PREREGISTERED':
        raise ValueError('design is not a preregistered or execution status')
    if spec.get('proposal_not_evidence') is not True or spec.get('asserts_edge') is not False:
        raise ValueError('proposal is not evidence')
    auth=spec['authorization']
    expected=('launch_authorized','market_reads_authorized_by_this_file','outcomes_opened','pnl_allowed','canonical_brain_write_authorized','independent_review_completed')
    if set(auth) != set(expected) or any(auth[k] is not False for k in expected):
        raise ValueError('design metadata cannot authorize or claim execution/review')
    data=spec['data_policy']
    if (data['instrument']!='MNQ' or data['market_and_private_events_location']!='KAGGLE_ONLY'
        or data['holdout_start_trade_date']!='2026-10-01'
        or data['frozen_or_previously_reserved_partitions_also_excluded'] is not True
        or data['previously_inspected_data_label']!='EXPLORATION_NOT_VIRGIN_HOLDOUT'
        or data['natural_contract_prices_required'] is not True
        or data['approved_source_manifest'] is not None or data['approved_sessions'] is not None):
        raise ValueError('proposed design has no approved market source/sessions')
    cat=spec['catalog']
    if cat['execution_status']!='NOT_EXECUTED' or cat['full_cross_indicator_cartesian_execution'] is not False or cat['all_nominal_trials_and_aliases_retained'] is not True:
        raise ValueError('not executed; preserve nominal trials and aliases')
    axes=cat['axes']
    if set(axes)!=set(EXPECTED_COUNTS): raise ValueError('wrong indicator family')
    counts={}
    for fam,a in axes.items():
        if not a: raise ValueError('missing axes')
        for name,values in a.items():
            if not isinstance(values,list) or not values: raise ValueError('nonempty axis required')
            keys=[json.dumps(v,sort_keys=True,allow_nan=False) for v in values]
            if len(set(keys))!=len(keys): raise ValueError('duplicate axis level')
        counts[fam]=math.prod(len(v) for v in a.values())
    if counts!=EXPECTED_COUNTS or cat['nominal_counts']!=counts: raise ValueError('catalog counts changed; version the design')
    if cat['detector_definitions_total']!=21888 or cat['avz_racimo_combined_definitions']!=82944: raise ValueError('wrong nominal totals')
    ids=[s['id'] for s in spec['scenario_catalog']]
    if ids!=[f'S{i:02d}' for i in range(1,25)] or any(s['status']!='PROPOSED_NEEDS_FROZEN_PREDICATE' for s in spec['scenario_catalog']):
        raise ValueError('24 proposed scenarios, not frozen predicates')
    ex=spec['execution_contract']
    for k in ('runner_implemented','end_to_end_optimization_validated','fastmath_allowed','canonical_fs_durability_may_be_weakened','export_private_events','legacy_pit_v1_allowed','legacy_all_inputs_loader_allowed'):
        if ex[k] is not False: raise ValueError('execution path not implemented/authorized by design')
    if ex['hardware_walltime_ram_estimate'] is not None: raise ValueError('no real benchmark estimates yet')
    an=spec['analysis_contract']
    if an['confirmation_authorized'] is not False or an['support_mde_thresholds'] is not None:
        raise ValueError('inference prerequisites pending')
    if not spec['launch_blockers']: raise ValueError('launch blockers still required')
    return {'status':'PASS_DESIGN_METADATA_ONLY_NOT_RUN_ADMISSION','counts':counts,'detector_definitions_total':21888,'avz_racimo_combined_definitions':82944,'scenario_families':24,'launch_authorized':False,'market_data_read':False,'scientific_or_parity_claim_verified':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True);a=p.parse_args()
    raw=a.spec.read_bytes(); spec=json.loads(raw); result=check_metadata(spec);result['spec_sha256']=hashlib.sha256(raw).hexdigest(); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
