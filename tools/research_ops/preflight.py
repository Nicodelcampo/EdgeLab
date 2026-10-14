"""Metadata-only canonical gate bridge. Never authorizes execution or coerces exploratory sources.
Expected digest must come from an external reviewed record; hashes are not authentication.
"""
import hashlib,json,os,stat
from edgelab.data.research_data_gate import require_research_eligibility
MAX_BYTES=1_048_576
FIELDS=frozenset(('certificate','regime_manifest','root','trade_date','liquidity_limits','expected_certificate_sha256','expected_regime_sha256','expected_liquidity_limits_sha256'))
def _object(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ValueError('duplicate metadata key')
        out[k]=v
    return out
def _nonfinite(value): raise ValueError('nonfinite metadata')
def check_bundle(path,expected_sha256):
    if not isinstance(expected_sha256,str) or len(expected_sha256)!=64 or any(c not in '0123456789abcdef' for c in expected_sha256): raise ValueError('external lowercase SHA256 required')
    if os.name!='posix' or not hasattr(os,'O_NOFOLLOW'): raise ValueError('POSIX no-follow reader required')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        before=os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size>MAX_BYTES: raise ValueError('bounded regular metadata required')
        raw=f.read(MAX_BYTES+1);after=os.fstat(f.fileno())
    if len(raw)>MAX_BYTES or (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns): raise ValueError('metadata changed or exceeded bound')
    if hashlib.sha256(raw).hexdigest()!=expected_sha256: raise ValueError('external bundle digest mismatch')
    bundle=json.loads(raw,object_pairs_hook=_object,parse_constant=_nonfinite)
    if type(bundle) is not dict or set(bundle)!={'schema_version','request'} or bundle['schema_version']!='research_gate_request_v1': raise ValueError('canonical bundle required; exploratory adapters remain separate')
    request=bundle['request']
    if type(request) is not dict or set(request)!=FIELDS: raise ValueError('closed canonical request schema required')
    decision=require_research_eligibility(**request)
    return dict(status='PASS_METADATA_ONLY_EXECUTION_DISABLED',bundle_sha256=expected_sha256,decision=decision,market_data_read=False,authority_authenticated=False,execution_allowed=False,holdout_opened=False,promotion_allowed=False)
