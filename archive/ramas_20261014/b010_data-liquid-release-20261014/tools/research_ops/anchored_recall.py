"""Read an existing canonical operational REPOSITORY SNAPSHOT, never initialize
or append a ledger. Three externally pinned receipts and all anchors must agree.
Hashes/Git references establish snapshot identity, not global/live authority.
"""
import re, tempfile
from pathlib import Path
from .knowledge import _pinned_bytes, _json, _sha, OPERATIONAL_TYPES, recall_brain

FIELDS={'schema','source_commit','scope','ledger_path','ledger_sha256',
        'anchors_path','anchors_sha256','anchors_key','receipt_path','receipt_sha256',
        'records','tip','read_only'}

def _path(root,relative):
    if not isinstance(relative,str) or not relative or len(relative)>4096 or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('explicit bounded repository-relative path required')
    p=root/relative
    if not p.resolve().is_relative_to(root.resolve()):raise ValueError('snapshot path escapes trusted root')
    return p

def recall_anchored_snapshot(root,binding_path,*,expected_binding_sha256,query,k=5,max_chars=12000):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('trusted repository root required')
    spec=_json(_pinned_bytes(binding_path,expected_binding_sha256))
    if type(spec) is not dict or set(spec)!=FIELDS or spec['schema']!='research_ops_operational_snapshot_binding_v1':
        raise ValueError('closed read-only binding required')
    if spec['read_only'] is not True or spec['scope']!='TARGET_FREE_AGGREGATE_OPERATIONS_ONLY':
        raise ValueError('operational snapshot only; no writer or scientific history')
    if not isinstance(spec['source_commit'],str) or not re.fullmatch('[0-9a-f]{40}',spec['source_commit']):
        raise ValueError('explicit pinned source commit required')
    if type(spec['records']) is not int or not 1<=spec['records']<=10000:
        raise ValueError('bounded nonempty snapshot; absent memory is not an empty ledger')
    _sha(spec['tip'])
    ledger=_pinned_bytes(_path(root,spec['ledger_path']),spec['ledger_sha256'])
    anchors=_json(_pinned_bytes(_path(root,spec['anchors_path']),spec['anchors_sha256']))
    receipt=_json(_pinned_bytes(_path(root,spec['receipt_path']),spec['receipt_sha256']))
    if type(anchors) is not dict or not isinstance(spec['anchors_key'],str):
        raise ValueError('anchored snapshot identity required')
    aa=anchors.get(spec['anchors_key'])
    if type(aa) is not list or not 1<=len(aa)<=128:raise ValueError('complete bounded anchor list required')
    last=0
    for a in aa:
        if type(a) is not dict or not {'records','tip'}<=set(a) or type(a['records']) is not int or not last<a['records']<=spec['records']:
            raise ValueError('positive strictly increasing anchors required')
        _sha(a['tip']);last=a['records']
    if (aa[-1]['records'],aa[-1]['tip'])!=(spec['records'],spec['tip']):
        raise ValueError('binding/final anchor mismatch')
    if type(receipt) is not dict or receipt.get('schema')!='edgelab_aggregate_hippocampus_receipt_v1' or type(receipt.get('records')) is not int or (receipt['records'],receipt.get('tip'))!=(spec['records'],spec['tip']):
        raise ValueError('receipt/anchor mismatch')
    rows=[_json(x) for x in ledger.splitlines() if x.strip()]
    if len(rows)!=spec['records'] or any(type(x) is not dict or x.get('type') not in OPERATIONAL_TYPES for x in rows):
        raise ValueError('census or target-free operational type mismatch')
    if any(x['type']=='episode_registered' and x.get('payload',{}).get('outcomes_inspected') is not False for x in rows):
        raise ValueError('operational episode must explicitly exclude outcome inspection')
    from edgelab.edge_brain.hippocampus_store import verify_anchors
    # Captured bytes eliminate check/read races against a changing live file.
    with tempfile.TemporaryDirectory(prefix='research-ops-readonly-recall-') as d:
        captured=Path(d)/'snapshot.jsonl';captured.write_bytes(ledger)
        verify_anchors(captured,aa)
        result=recall_brain(captured,expected_file_sha256=spec['ledger_sha256'],
                            expected_tip=spec['tip'],query=query,k=k,max_chars=max_chars)
    result.update(snapshot_binding_sha256=expected_binding_sha256,source_commit=spec['source_commit'],
                  snapshot_scope=spec['scope'],anchors_verified=len(aa),snapshot_records=len(rows),
                  live_destination_bound=False,remote_latest_verified=False,
                  scientific_trial_history_complete=False,write_authorized=False)
    return result