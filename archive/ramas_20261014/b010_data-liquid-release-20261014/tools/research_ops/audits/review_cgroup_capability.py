"""Source-pinned capability evidence, never delegation or a resource receipt."""
import math,re
from tools.research_ops.knowledge import _pinned_bytes,_json,_sha
FIELDS={'schema','linux','cgroup2_mount_verified','memory_peak_readable','memory_controller_available','mount_readonly','directory_write_access_hint','self_scope_sha256','delegated_job_leaf_proven','whole_workload_coverage_attested','rss_measurement','execution_allowed','mutations_performed','source_checkpoint','program_sha256','wall_seconds'}
PROGRAMS={'tools/research_ops/cgroup_telemetry.py','tools/research_ops/store.py'}
BOOLS={'linux','cgroup2_mount_verified','memory_peak_readable','memory_controller_available','directory_write_access_hint','delegated_job_leaf_proven','whole_workload_coverage_attested','rss_measurement','execution_allowed','mutations_performed'}
CEILING={'delegated_job_leaf_proven','whole_workload_coverage_attested','rss_measurement','execution_allowed','mutations_performed'}
def review(path,*,expected_sha256,expected_source_commit,expected_program_sha256):
 if not isinstance(expected_source_commit,str) or not re.fullmatch('[0-9a-f]{40}',expected_source_commit):raise ValueError('external source commit required')
 if type(expected_program_sha256) is not dict or set(expected_program_sha256)!=PROGRAMS:raise ValueError('complete external program pins required')
 for h in expected_program_sha256.values():_sha(h)
 p=_json(_pinned_bytes(path,expected_sha256))
 if type(p) is not dict or set(p) not in (FIELDS,FIELDS|{'probe_incomplete'}) or p['schema']!='research_ops_cgroup_capability_probe_v1':raise ValueError('closed capability-only receipt required')
 if p['source_checkpoint']!=expected_source_commit or p['program_sha256']!=expected_program_sha256:raise ValueError('probe source identity mismatch')
 if any(type(p[k]) is not bool for k in BOOLS) or any(p[k] is not False for k in CEILING) or p['mount_readonly'] is not None and type(p['mount_readonly']) is not bool:raise ValueError('capability booleans/authority ceiling required')
 if 'probe_incomplete' in p and p['probe_incomplete'] is not True:raise ValueError('incomplete flag cannot imply successful scope')
 if p['self_scope_sha256'] is not None:_sha(p['self_scope_sha256'])
 if type(p['wall_seconds']) not in (int,float) or not math.isfinite(p['wall_seconds']) or not 0<p['wall_seconds']<=30:raise ValueError('bounded finite probe wall time required')
 if p['memory_peak_readable'] and (not p['linux'] or not p['cgroup2_mount_verified']):raise ValueError('counter without verified Linux cgroup mount')
 ready=p['linux'] and p['cgroup2_mount_verified'] and p['memory_peak_readable'] and not p.get('probe_incomplete',False)
 return {'schema':'research_ops_cgroup_capability_review_v1','status':'COUNTER_READABLE_SCOPE_UNATTESTED' if ready else 'COUNTER_INTERFACE_UNAVAILABLE_OR_INCOMPLETE','receipt_sha256':expected_sha256,'source_checkpoint':expected_source_commit,'counter_interface_available':bool(ready),'mount_readonly':p['mount_readonly'],'memory_controller_available_for_subtree_hint':p['memory_controller_available'],'in_kernel_directory_write_access_hint':p['directory_write_access_hint'],'approved_job_scope_bound':False,'whole_workload_coverage_attested':False,'authenticated_custody':False,'historical_job_rss_available':False,'execution_allowed':False,'production_receiver_compatible':False,'canonical_write_authorized':False,'required_next_step':'Externally approved isolated lifecycle/containment and resource-kind-aware receipt migration; never infer job usage from root/shared/unattested counter.'}
