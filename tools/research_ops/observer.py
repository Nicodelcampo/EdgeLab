"""Read-only adapter for existing campaign state. No job control or raw data access."""
import datetime, json
from pathlib import Path

ALLOWED = {'RUNNING_RECOVERED_CAMPAIGNS', 'STOPPED_FAIL_CLOSED',
           'RECOVERED_MISSING_PASSES_COMPLETE_NOT_STRATEGY_VALIDATION'}

def observe(path, max_age_seconds=900):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        return {'status':'UNAVAILABLE', 'completion_inferred':False}
    before = p.stat()
    if before.st_size > 65536:
        return {'status':'REJECTED_OVERSIZE', 'completion_inferred':False}
    try:
        with p.open('rb') as stream:
            raw = stream.read(65537)
        if len(raw)>65536:
            return {'status':'REJECTED_OVERSIZE','completion_inferred':False}
        data = json.loads(raw)
    except (OSError, ValueError):
        return {'status':'UNREADABLE', 'completion_inferred':False}
    after = p.stat()
    if (before.st_ino,before.st_mtime_ns,before.st_size) != (after.st_ino,after.st_mtime_ns,after.st_size):
        return {'status':'CHANGED_DURING_READ','completion_inferred':False}
    if not isinstance(data,dict) or data.get('status') not in ALLOWED:
        return {'status':'UNRECOGNIZED','completion_inferred':False}
    now = datetime.datetime.now(datetime.timezone.utc)
    age = max(0,now.timestamp()-after.st_mtime)
    return {'status':'OBSERVED', 'observed_utc':now.isoformat(), 'campaign_status':data['status'],
            'active_contract':data.get('active_contract'), 'stage':data.get('stage'),
            'state_age_seconds':age, 'stale_state_warning':age>max_age_seconds,
            'completion_inferred':False, 'controller_or_worker_liveness_verified':False,
            'raw_payload_read':False, 'job_controls_available':False}
