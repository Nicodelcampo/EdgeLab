"""Offline receiver for externally signed Kaggle acquisition + measured RSS.
It verifies authenticated custody, not Kaggle's original dataset certification.
No scraping, arbitrary download URLs, login, network or relaunch is implemented.
An approved coordinator must acquire complete outputs and sign their binding.
"""
import hashlib
from pathlib import Path
from .signed_authority import verify_signed
from .mnq_closeout import INPUTS, IDENTITY_FIELDS, inspect_mnq_closeout, build_mnq_envelope
from .snapshots import _read
from .learning_outbox import _json
from .post_run import _id, _sha
from .store import digest

FIELDS = {'schema','principal','issued_at','expires_at','provider','account',
          'kernel_id','version','execution_id','terminal','contract','scope',
          'scientific_code_commit','identity','pins','memory_sha256'}
MEMORY_FIELDS = {'schema','identity_sha256','code_commit','measurement',
                 'peak_rss_bytes','children_seen','workload_complete'}


def receive_authenticated_closeout(root, signed_custody, *, trusted_keys, now,
                                  expected_account, expected_kernel_id,
                                  expected_version, expected_execution_id,
                                  expected_contract, expected_scope,
                                  expected_code_commit):
    for ident in (expected_account,expected_execution_id,expected_contract):_id(ident)
    if any(type(x) is not int or x<1 for x in (expected_kernel_id,expected_version)):
        raise ValueError('explicit external integer notebook/version required')
    v=verify_signed(signed_custody,trusted_keys=trusted_keys,role='KAGGLE_CUSTODY',now=now)
    p=v['payload']
    if set(p)!=FIELDS or p['schema']!='research_ops_kaggle_custody_v1' or p['provider']!='kaggle':
        raise ValueError('closed Kaggle acquisition receipt required')
    for name in ('principal','account','execution_id','contract'): _id(p[name])
    if any(type(p.get(k)) is not int or p[k]<1 for k in ('kernel_id','version')):
        raise ValueError('immutable integer notebook identity required')
    if (p['account'],p['kernel_id'],p['version'],p['execution_id'],p['contract'],p['scope'],p['scientific_code_commit']) != (
            expected_account,expected_kernel_id,expected_version,expected_execution_id,
            expected_contract,expected_scope,expected_code_commit):
        raise ValueError('external expected provider/scope/code binding mismatch')
    if p['terminal']!='COMPLETE':
        raise ValueError('complete semantic MNQ adapter only; failures need their own closeout')
    identity=p['identity']
    if type(identity) is not dict or set(identity)!=IDENTITY_FIELDS or (identity['provider_job_id'],identity['version'])!=(expected_execution_id,expected_version):
        raise ValueError('execution/input/build identity mismatch')
    if type(p['pins']) is not dict or set(p['pins'])!=INPUTS:
        raise ValueError('complete independently reviewed bundle pins required')
    _sha(p['memory_sha256'])
    raw=_read(Path(root)/'memory-measurement.json',65536)
    if hashlib.sha256(raw).hexdigest()!=p['memory_sha256']:
        raise ValueError('memory receipt pin mismatch')
    memory=_json(raw)
    if type(memory) is not dict or set(memory)!=MEMORY_FIELDS or memory['schema']!='research_ops_memory_measurement_v1':
        raise ValueError('closed memory measurement receipt required')
    if memory['identity_sha256']!=digest(identity) or memory['code_commit']!=expected_code_commit:
        raise ValueError('memory is not from this exact execution/build/input')
    if memory['measurement']!='LINUX_SINGLE_PROCESS_RUSAGE_SELF_HIGH_WATER_RSS' or memory['children_seen'] is not False or memory['workload_complete'] is not True:
        raise ValueError('isolated single-process whole-workload RSS required; no caps/samples/imputation')
    projection=inspect_mnq_closeout(root,expected_pins=p['pins'],expected_contract=expected_contract,
                                   scope=expected_scope,expected_code_commit=expected_code_commit)
    result=build_mnq_envelope(projection,identity=identity,
                             measured_peak_rss_bytes=memory['peak_rss_bytes'],
                             memory_receipt_sha256=p['memory_sha256'])
    result.update(custody_receipt_sha256=v['receipt_sha256'],
                  custody_signature_verified=True,
                  source_certified=False,review_required=True,
                  canonical_ledger_modified=False,execution_allowed=False)
    return result