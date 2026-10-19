"""Conservative metadata-only memory admission. Not a lease or job launcher.
Observations come from a trusted supervisor; no reclaimable-cache subtraction and
no automatic oversubscription or heavy overlap while the current campaign runs.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ResourceSnapshot:
    memory_current_bytes: int
    memory_limit_bytes: int
    heavy_worker_active: bool
    def validate(self):
        if type(self.memory_current_bytes) is not int or self.memory_current_bytes<0:raise ValueError('explicit nonnegative memory measurement required')
        if type(self.memory_limit_bytes) is not int or self.memory_limit_bytes<=0:raise ValueError('finite memory limit required')
        if type(self.heavy_worker_active) is not bool:raise ValueError('explicit heavy-worker observation required')

def assess_admission(snapshot,*,requested_peak_bytes,headroom_bytes,heavy_job=True):
    snapshot.validate()
    for value in (requested_peak_bytes,headroom_bytes):
        if type(value) is not int or value<=0:raise ValueError('positive finite resource bounds required')
    if type(heavy_job) is not bool:raise ValueError('explicit heavy job flag required')
    reasons=[]
    if snapshot.memory_current_bytes+requested_peak_bytes+headroom_bytes>snapshot.memory_limit_bytes:reasons.append('INSUFFICIENT_CONSERVATIVE_MEMORY_HEADROOM')
    if heavy_job and snapshot.heavy_worker_active:reasons.append('HEAVY_WORKER_ALREADY_ACTIVE')
    return dict(status='RESOURCE_CAPACITY_ONLY_NOT_AUTHORITY' if not reasons else 'BLOCKED_RESOURCES',reasons=reasons,resource_fit=not reasons,execution_allowed=False,authority_authenticated=False,reservation_created=False,observation_is_not_a_lease=True)
