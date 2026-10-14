"""Local read-only technical projection of pinned MNQ closeout receipts.
Remote acquisition, publisher authentication, source permissions and independent
scientific audit are external prerequisites, NOT authenticated by this module.
Never exposes target rates/candidates to operational learning or imputes RSS.
"""
import hashlib
import re
from pathlib import Path
from .snapshots import _read, _exclusive
from .learning_outbox import _json
from .post_run import RunObservation, _id, _sha, _number
from .store import canonical, digest

INPUTS={'campaign-status.json','independent-review.json','timing-evidence.json','artifact-inventory.json'}
IDENTITY_FIELDS={'run_id','provider_job_id','version','source_sha256','selection_sha256','scientific_protocol_sha256','engine_build_sha256','manifest_sha256'}


def inspect_mnq_closeout(root, *, expected_pins, expected_contract, scope, expected_code_commit):
    if scope not in ('focal','matrix'):raise ValueError('explicit scientific work scope required')
    _id(expected_contract)
    if not isinstance(expected_code_commit,str) or not re.fullmatch('[0-9a-f]{40}',expected_code_commit):raise ValueError('pinned scientific code commit required')
    if type(expected_pins) is not dict or set(expected_pins)!=INPUTS:raise ValueError('all four external input pins required')
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('trusted regular bundle directory required')
    records={}
    for name,pin in expected_pins.items():
        _sha(pin);raw=_read(root/name,1024*1024)
        if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('closeout input hash mismatch: '+name)
        record=_json(raw)
        if type(record) is not dict:raise ValueError('object receipt required')
        records[name]=record
    state=records['campaign-status.json'];audit=records['independent-review.json'];timing=records['timing-evidence.json'];inventory=records['artifact-inventory.json']
    if any(x.get('contract')!=expected_contract for x in (state,audit,timing,inventory)):
        raise ValueError('cross-file contract mismatch')
    if state.get('code_commit')!=expected_code_commit:raise ValueError('scientific code binding mismatch')
    if state.get('stage')!='complete':raise ValueError('semantic stage not complete')
    items=inventory.get('artifacts')
    if type(items) is not list or not 1<=len(items)<=2000:raise ValueError('bounded complete inventory required')
    paths=set();state_pin=None
    for item in items:
        if type(item) is not dict or not {'path','bytes','sha256'}<=set(item):raise ValueError('inventory artifact required')
        path=item['path']
        if not isinstance(path,str) or path in paths or Path(path).is_absolute() or '..' in Path(path).parts:raise ValueError('unique relative inventory path required')
        paths.add(path);_sha(item['sha256'])
        if type(item['bytes']) is not int or item['bytes']<0:raise ValueError('artifact byte count required')
        if path=='recovery/campaign-status.json':state_pin=item
    if state_pin is None or state_pin['sha256']!=expected_pins['campaign-status.json']:
        raise ValueError('inventory does not bind semantic state')
    if state_pin['bytes']!=(root/'campaign-status.json').stat().st_size:raise ValueError('semantic state size mismatch')
    if inventory.get('status')!=state.get('status'):raise ValueError('inventory/state status mismatch')
    if scope=='focal':
        if state.get('status')!='LONGEVITY_FOCAL_COMPLETE_MATRIX_PENDING_NOT_VALIDATED_EDGE' or audit.get('status')!='PASS_EXPORTED_FOCAL_INDEPENDENT_SQL_RECOUNT':raise ValueError('focal semantic closeout/audit required')
        expected=594*5400;complete=state.get('completed_focal_definitions')
        if audit.get('all_594_cohorts_have_5400_represented_definitions') is not True or type(audit.get('focal_definitions')) is not int or audit.get('focal_definitions')!=expected:raise ValueError('focal represented-definition census mismatch')
    else:
        if state.get('status')!='MATRIX_1935360_PAIRS_COMPLETE_NOT_VALIDATED_EDGE' or audit.get('status')!='PASS_EXPORTED_MATRIX_INDEPENDENT_REVIEW':raise ValueError('matrix semantic closeout/audit required')
        expected=1536*1260;complete=state.get('matrix_pairs_complete')
        if audit.get('all_pairs_unique_and_present') is not True or type(audit.get('config_rule_pairs')) is not int or audit.get('config_rule_pairs')!=expected or type(state.get('matrix_pairs_pending')) is not int or state.get('matrix_pairs_pending')!=0:raise ValueError('matrix pair census mismatch')
    if type(complete) is not int or complete!=expected:raise ValueError('incomplete registered scope')
    wall=timing.get('seconds_to_final_status');_number(wall,True)
    stages=timing.get('stage_seconds')
    if type(stages) is not dict or not 1<=len(stages)<=32:raise ValueError('bounded stage timing required')
    for k,v in stages.items():_id(k);_number(v)
    if sum(stages.values())>wall+1e-6:raise ValueError('nonoverlapping timing contract violated')
    projection=dict(schema='research_ops_mnq_technical_projection_v1',contract=expected_contract,
                    scope=scope,expected_units=expected,completed_units=complete,
                    wall_seconds=wall,stages=sorted(stages.items()),input_sha256=dict(expected_pins),
                    declared_code_commit=expected_code_commit,local_input_hashes_verified=True,
                    remote_provenance_attested=False,source_certified=False,
                    scientific_outcomes_exported=False,execution_allowed=False,activation_allowed=False)
    projection['projection_sha256']=digest(projection)
    return projection


def build_mnq_envelope(projection, *, identity=None, measured_peak_rss_bytes=None, memory_receipt_sha256=None):
    if type(projection) is not dict or projection.get('schema')!='research_ops_mnq_technical_projection_v1':raise ValueError('technical projection required')
    unsigned={k:v for k,v in projection.items() if k!='projection_sha256'}
    if digest(unsigned)!=projection.get('projection_sha256'):raise ValueError('projection changed')
    missing=[]
    if identity is None:missing.append('VERIFIED_EXECUTION_AND_INPUT_BUILD_BINDING')
    elif type(identity) is not dict or set(identity)!=IDENTITY_FIELDS:raise ValueError('closed external execution identity required')
    if measured_peak_rss_bytes is None:missing.append('MEASURED_PEAK_RSS_BYTES')
    elif type(measured_peak_rss_bytes) is not int or measured_peak_rss_bytes<=0:raise ValueError('positive measured RSS required; no imputation')
    if memory_receipt_sha256 is None:missing.append('PINNED_MEMORY_MEASUREMENT_RECEIPT')
    else:_sha(memory_receipt_sha256)
    if missing:
        return dict(status='BLOCKED_MISSING_MEASUREMENTS_OR_BINDING',missing=missing,
                    projection_sha256=projection['projection_sha256'],envelope=None,
                    local_technical_projection_verified=True,remote_provenance_attested=False,
                    execution_allowed=False,activation_allowed=False)
    observation=RunObservation(**identity,state='COMPLETE',receipt_sha256=projection['input_sha256']['independent-review.json'],
                               wall_seconds=projection['wall_seconds'],peak_rss_bytes=measured_peak_rss_bytes,
                               expected_units=projection['expected_units'],completed_units=projection['completed_units'],
                               stages=tuple(tuple(v) for v in projection['stages']),integrity='PASS')
    observation.validate()
    from dataclasses import asdict
    envelope=dict(schema='research_ops_technical_closeout_v1',provider='kaggle',observation=asdict(observation))
    # Evidence linkage is in the sidecar, not an assertion of remote authority.
    return dict(status='LOCAL_TECHNICAL_ENVELOPE_CANDIDATE_NOT_AUTHORITY',envelope=envelope,
                projection_sha256=projection['projection_sha256'],memory_receipt_sha256=memory_receipt_sha256,
                remote_provenance_attested=False,source_certified=False,execution_allowed=False,activation_allowed=False)


def write_mnq_envelope(candidate, destination):
    if type(candidate) is not dict or candidate.get('status')!='LOCAL_TECHNICAL_ENVELOPE_CANDIDATE_NOT_AUTHORITY' or candidate.get('envelope') is None:
        raise ValueError('complete local candidate required; blocked producer must not emit envelope')
    pack=candidate['envelope']
    if type(pack) is not dict or set(pack)!={'schema','provider','observation'} or pack['schema']!='research_ops_technical_closeout_v1' or pack['provider']!='kaggle':
        raise ValueError('closed Kaggle technical envelope required')
    from .learning_outbox import _observation
    _observation(pack['observation']);_sha(candidate['projection_sha256']);_sha(candidate['memory_receipt_sha256'])
    raw=(canonical(pack)+'\n').encode()
    if len(raw)>65536:raise ValueError('bounded envelope required')
    _exclusive(destination,raw)
    return dict(status='LOCAL_ENVELOPE_WRITTEN_NOT_ENQUEUED',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                projection_sha256=candidate['projection_sha256'],memory_receipt_sha256=candidate['memory_receipt_sha256'],
                remote_provenance_attested=False,canonical_ledger_modified=False,execution_allowed=False)
