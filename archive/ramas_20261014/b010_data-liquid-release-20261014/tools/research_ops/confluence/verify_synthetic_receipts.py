"""Check engineering receipts against external package/roster pins, not market approval."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from .build_target_free_pilot import digest
from .pilot_runtime import validate_roster,FAMILIES


def verify(boot_raw,pilot_raw,*,package,roster,local_reference=None):
    boot=json.loads(boot_raw);pilot=json.loads(pilot_raw);configs=validate_roster(roster)
    if boot.get('schema')!='confluence_synthetic_kaggle_boot_v1' or pilot.get('schema')!='mnq_confluence_synthetic_pilot_receipt_v1':raise ValueError('receipt schema mismatch')
    if any(x.get('status')!='SYNTHETIC_COMPLETE_NOT_MNQ_RESULTS' for x in (boot,pilot)):raise ValueError('semantic completion missing')
    for x in (boot,pilot):
        for k in ('market_data_read','holdout_opened','outcomes_computed','pnl_computed'):
            if x.get(k) is not False:raise ValueError('synthetic scope flag mismatch')
    if boot.get('source_commit')!=package['source_commit'] or boot.get('bundle_sha256')!=package['bundle_sha256']:raise ValueError('source/bundle mismatch')
    if boot.get('pilot_receipt_sha256')!=hashlib.sha256(pilot_raw).hexdigest():raise ValueError('output bytes mismatch')
    if boot.get('exit_code')!=0 or boot.get('stop_reason') is not None or boot.get('hard_address_space_limit_applied') is not True:raise ValueError('process limits/completion mismatch')
    if boot.get('input_mounts_used') is not False or boot.get('internet_required') is not False:raise ValueError('unexpected input/network scope')
    if digest({k:v for k,v in pilot.items() if k!='receipt_sha256'})!=pilot.get('receipt_sha256'):raise ValueError('pilot content hash mismatch')
    if pilot.get('roster_sha256')!=roster['roster_sha256']:raise ValueError('wrong roster')
    rows=pilot.get('configs',[]);expected={c['config_sha256']:FAMILIES[c['indicator']] for c in configs}
    if len(rows)!=96 or Counter(x['config_sha256'] for x in rows)!=Counter(expected.keys()):raise ValueError('config missing/duplicate/extra')
    if any(x['family']!=expected[x['config_sha256']] or x.get('exact_native_output_verified') is not True for x in rows):raise ValueError('native reference not verified for every config')
    groups=[[c for c in configs if c['indicator']==name] for name in FAMILIES]
    combos=[tuple(g[i]['config_sha256'] for g in groups) for i in range(32)]
    if Counter(tuple(t['configs']) for t in pilot.get('triads',[]))!=Counter(combos):raise ValueError('triad coverage mismatch')
    if pilot.get('coverage')!='96_DETECTORS_32_ALIGNED_TRIADS_NOT_CARTESIAN':raise ValueError('coverage misrepresented')
    matched=None
    if local_reference is not None:
        if pilot['synthetic_fixture']!=local_reference['synthetic_fixture']:raise ValueError('different fixture cannot compare exact outputs')
        ref={x['config_sha256']:x for x in local_reference['configs']}
        for row in rows:
            for k in ('native_output_sha256','capture_sha256','record_counts','unavailable_close_events'):
                if row[k]!=ref[row['config_sha256']][k]:raise ValueError('local/Kaggle detector output mismatch')
        rt={tuple(t['configs']):t for t in local_reference['triads']}
        for triad in pilot['triads']:
            for k in ('episode_event_counts','arrival_counts','scope_excluded_records','nonempty_frame_stream_sha256'):
                if triad[k]!=rt[tuple(triad['configs'])][k]:raise ValueError('local/Kaggle replay output mismatch')
        matched=True
    return {'schema':'confluence_synthetic_output_verification_v1','status':'PASS_SYNTHETIC_RECEIPT_BINDING_ONLY','source_commit':package['source_commit'],'bundle_sha256':package['bundle_sha256'],'boot_file_sha256':hashlib.sha256(boot_raw).hexdigest(),'pilot_file_sha256':hashlib.sha256(pilot_raw).hexdigest(),'exact_native_configs':96,'aligned_triads':32,'local_kaggle_exact_outputs_match':matched,'source_quality_certified':False,'new_market_results':False,'market_launch_authorized':False,'kaggle_child_wall_seconds':boot['wall_seconds'],'kaggle_sampled_child_peak_rss_bytes':boot['sampled_child_peak_rss_bytes'],'measurement_scope':boot['limits_scope'],'speedup_claimed':False}
