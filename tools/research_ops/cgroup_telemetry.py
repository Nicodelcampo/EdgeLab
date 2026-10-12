"""Read-only Linux cgroup-v2 kernel accounting for an externally prepared job leaf.
Never create/reset/configure a cgroup, move/kill processes or launch a workload.
The kernel peak is ACCOUNTED MEMORY (incl. cache), NOT RSS. Fresh bounded leaf
and monotone snapshots do not prove exclusive whole-workload custody: an external
coordinator must attest containment/lifecycle and supply real identities/signatures.
This module emits DIAGNOSTICS, never the single-process RSS receiver's schema.
"""
import copy,hashlib,json,os,re,stat,sys,time
from pathlib import Path
from .store import digest
MOUNT=Path('/sys/fs/cgroup')
MAX_READ=16384
EVENTS={'low','high','max','oom','oom_kill'}

def _cgroup2_mount(path):
 # Default mount only; no arbitrary mounts, symlinks or guessed hierarchy paths.
 if sys.platform!='linux' or path!=MOUNT:raise ValueError('fixed Linux cgroup2 mount required')
 lines=Path('/proc/self/mountinfo').read_text().splitlines()
 if not any(line.split(' - ',1)[0].split()[4]==str(path) and line.split(' - ',1)[1].split()[0]=='cgroup2' for line in lines if ' - ' in line):raise ValueError('verified cgroup2 filesystem required')

def _read(fd,name):
 f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
 with os.fdopen(f,'rb') as stream:
  if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('regular cgroup interface required')
  raw=stream.read(MAX_READ+1)
 if len(raw)>MAX_READ:raise ValueError('bounded cgroup interface required')
 return raw.decode('ascii').strip()

def _integer(text,*,allow_max=False):
 if allow_max and text=='max':return None
 if not re.fullmatch(r'0|[1-9][0-9]{0,19}',text):raise ValueError('finite nonnegative kernel counter required')
 value=int(text)
 if value>2**63-1:raise ValueError('kernel counter overflow')
 return value

def _pairs(text):
 out={}
 for line in text.splitlines():
  p=line.split()
  if len(p)!=2 or p[0] in out:raise ValueError('unique kernel event keys required')
  out[p[0]]=_integer(p[1])
 return out

def _open_leaf(path):
 _cgroup2_mount(MOUNT)
 p=Path(path)
 if not p.is_absolute() or '..' in p.parts or not p.is_relative_to(MOUNT) or p==MOUNT:raise ValueError('explicit job leaf beneath fixed mount required; never root')
 fd=os.open(MOUNT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  for part in p.relative_to(MOUNT).parts:
   nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
  return fd
 except BaseException:os.close(fd);raise

def _snapshot(fd):
 info=os.fstat(fd)
 events=_pairs(_read(fd,'memory.events'));cg=_pairs(_read(fd,'cgroup.events'))
 if not EVENTS<=set(events) or not {'populated','frozen'}<=set(cg) or cg['populated'] not in (0,1) or cg['frozen'] not in (0,1):raise ValueError('complete kernel event scope required')
 # Subgroups are disallowed for this leaf-only adapter. Children processes in
 # the SAME leaf are included by kernel accounting; direct pid list is no peak.
 dirs=[]
 for name in os.listdir(fd):
  if stat.S_ISDIR(os.stat(name,dir_fd=fd,follow_symlinks=False).st_mode):dirs.append(name)
 if dirs:raise ValueError('job leaf must have no subgroups')
 procs=_read(fd,'cgroup.procs').splitlines();pidvalues=[_integer(p) for p in procs]
 if len(set(pidvalues))!=len(pidvalues) or any(p==0 for p in pidvalues):raise ValueError('valid unique direct memberships required')
 s={'device':info.st_dev,'inode':info.st_ino,'memory_current_bytes':_integer(_read(fd,'memory.current')),'memory_peak_bytes':_integer(_read(fd,'memory.peak')),'memory_max_bytes':_integer(_read(fd,'memory.max'),allow_max=True),'pids_current':_integer(_read(fd,'pids.current')),'pids_max':_integer(_read(fd,'pids.max'),allow_max=True),'populated':cg['populated'],'frozen':cg['frozen'],'direct_members':len(procs),'memory_events':events}
 if s['memory_current_bytes']>s['memory_peak_bytes'] or s['pids_current']<s['direct_members']:raise ValueError('inconsistent sampled kernel counters; retry externally, never impute')
 return s

class CgroupAccountingSession:
 def __init__(self,path,*,identity_sha256,code_commit,max_memory_bytes,max_tasks):
  if not isinstance(identity_sha256,str) or not re.fullmatch('[0-9a-f]{64}',identity_sha256) or not isinstance(code_commit,str) or not re.fullmatch('[0-9a-f]{40}',code_commit):raise ValueError('external execution/code pins required')
  if type(max_memory_bytes) is not int or not 1<=max_memory_bytes<=4*1024**3 or type(max_tasks) is not int or not 1<=max_tasks<=64:raise ValueError('bounded externally prepared controls required')
  self.fd=_open_leaf(path);self.closed=False;self.failed=False;self.owner=os.getpid()
  try:
   s=_snapshot(self.fd)
   if s['memory_max_bytes']!=max_memory_bytes or s['pids_max']!=max_tasks:raise ValueError('exact externally approved controls required')
   if s['populated'] or s['frozen'] or s['pids_current'] or s['direct_members'] or s['memory_current_bytes'] or s['memory_peak_bytes'] or any(s['memory_events'].values()):raise ValueError('fresh empty zero-history job leaf required')
  except BaseException:self.close();raise
  self.initial=s;self.last=s;self.started=time.monotonic();self.samples=1;self.max_tasks_seen=0
  self.identity_sha256=identity_sha256;self.code_commit=code_commit
 def close(self):
  if not self.closed:os.close(self.fd);self.closed=True
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
 def poll(self):
  if self.closed or self.failed or os.getpid()!=self.owner:raise ValueError('live successful same-observer session required')
  try:
   s=_snapshot(self.fd)
   for k in ['device','inode','memory_max_bytes','pids_max']:
    if s[k]!=self.initial[k]:raise ValueError('group identity/controls changed')
   if s['frozen'] or s['memory_peak_bytes']<self.last['memory_peak_bytes'] or set(s['memory_events'])!=set(self.last['memory_events']) or any(s['memory_events'][k]<v for k,v in self.last['memory_events'].items()):raise ValueError('frozen/reset/nonmonotone kernel state')
   # Kernel limits can temporarily overshoot; preserve a FAILURE diagnostic,
   # never replace the observed counter with the configured cap.
   self.max_tasks_seen=max(self.max_tasks_seen,s['pids_current'])
   self.last=s;self.samples+=1;return copy.deepcopy(s)
  except BaseException:self.failed=True;raise
 def finish(self):
  try:
   s=self.poll()
   if s['populated'] or s['direct_members'] or s['pids_current']:raise ValueError('all job members must be gone; empty does not prove successful workload')
   limit_events=any(s['memory_events'].get(k,0)>0 for k in ['max','oom','oom_kill','oom_group_kill']) or s['memory_peak_bytes']>s['memory_max_bytes'] or self.max_tasks_seen>s['pids_max']
   return {'schema':'research_ops_cgroup_memory_diagnostic_v1','status':'KERNEL_LIMIT_EVENT_DIAGNOSTIC_NOT_SUCCESS' if limit_events else 'KERNEL_ACCOUNTING_DIAGNOSTIC_NOT_CUSTODY','identity_sha256':self.identity_sha256,'code_commit':self.code_commit,'measurement':'LINUX_CGROUP_V2_MEMORY_PEAK_ACCOUNTED_BYTES_NOT_RSS','peak_accounted_memory_bytes':s['memory_peak_bytes'],'configured_memory_max_bytes':s['memory_max_bytes'],'configured_max_tasks':s['pids_max'],'memory_events':s['memory_events'],'samples':self.samples,'max_sampled_tasks':self.max_tasks_seen,'task_count_is_sampled_lower_bound':True,'wall_seconds':time.monotonic()-self.started,'fresh_empty_begin_observed':True,'empty_end_observed':True,'leaf_identity_sha256':digest({'device':s['device'],'inode':s['inode']}),'kernel_counter_not_sampling_peak':True,'exclusive_scope_attested':False,'whole_workload_coverage_attested':False,'workload_success_proven':False,'authenticated_custody':False,'historical_job_rss_available':False,'execution_allowed':False,'adoption_authorized':False,'canonical_write_authorized':False}
  finally:self.close()

def capability_probe():
 """No cgroup writes; no workloads; no usage values/process ids exported."""
 result={'schema':'research_ops_cgroup_capability_probe_v1','linux':sys.platform=='linux','cgroup2_mount_verified':False,'memory_peak_readable':False,'memory_controller_available':False,'mount_readonly':None,'directory_write_access_hint':False,'self_scope_sha256':None,'delegated_job_leaf_proven':False,'whole_workload_coverage_attested':False,'rss_measurement':False,'execution_allowed':False,'mutations_performed':False}
 try:
  _cgroup2_mount(MOUNT);result['cgroup2_mount_verified']=True
  result['mount_readonly']=bool(os.statvfs(MOUNT).f_flag&os.ST_RDONLY)
  result['directory_write_access_hint']=os.access(MOUNT,os.W_OK)
  result['memory_controller_available']='memory' in (MOUNT/'cgroup.controllers').read_text().split()
  result['self_scope_sha256']=hashlib.sha256(Path('/proc/self/cgroup').read_bytes()).hexdigest()
  fd=os.open(MOUNT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try:_integer(_read(fd,'memory.peak'));result['memory_peak_readable']=True
  finally:os.close(fd)
 except (OSError,ValueError):result['probe_incomplete']=True
 return result
if __name__=='__main__':print(json.dumps(capability_probe(),sort_keys=True,allow_nan=False))
