"""Read-only import of an externally pinned, target-free technical envelope.
The producer must verify cloud job/version, output inventory and audit custody.
This boundary verifies local bytes/schema/binding, not remote job authenticity.
No cloud login, network, downloads, source certification or implicit replay.
"""
import hashlib
from .snapshots import _read
from .learning_outbox import _json, _observation
from .post_run import _id, _sha

FIELDS={'schema','provider','observation'}
MAX_BYTES=65536


def ingest_closeout(path, outbox, *, expected_sha256, expected_provider,
                    expected_job_id, expected_version, expected_tip):
    _sha(expected_sha256);_sha(expected_tip);_id(expected_job_id)
    if expected_provider not in ('kaggle','synthetic'):
        raise ValueError('explicit registered provider binding required')
    if type(expected_version) is not int or expected_version<1:
        raise ValueError('explicit immutable version binding required')
    raw=_read(path,MAX_BYTES)
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('external closeout file pin mismatch')
    pack=_json(raw)
    if type(pack) is not dict or set(pack)!=FIELDS or pack['schema']!='research_ops_technical_closeout_v1':
        raise ValueError('closed technical envelope required; no results or free text')
    if pack['provider']!=expected_provider:
        raise ValueError('provider binding mismatch')
    observation=_observation(pack['observation'])
    if (observation.provider_job_id,observation.version)!=(expected_job_id,expected_version):
        raise ValueError('job/version binding mismatch')
    result=outbox.enqueue(expected_provider,observation,envelope_sha256=expected_sha256,expected_tip=expected_tip)
    result.update(local_envelope_verified=True,remote_provenance_attested=False,
                  scientific_source_certified=False,canonical_ledger_modified=False,
                  activation_allowed=False,execution_allowed=False)
    return result
