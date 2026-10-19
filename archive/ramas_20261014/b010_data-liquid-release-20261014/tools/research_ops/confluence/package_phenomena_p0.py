"""Prepare one bounded PRIVATE P0 request. Does not submit or grant authority.

Signed source URL exists only in the private request. Public receipt is URL-free.
Transport uses the already approved source pin, not a repeated quality audit.
"""
import base64,hashlib,json,zlib
from pathlib import Path
from urllib.parse import urlsplit
from .package_synthetic_notebook import SOURCE_FILES
from .package_market_pilot import EXTRA
from .source_footer import validate_pin
from .build_target_free_pilot import digest
PLAN='docs/research/ops/MNQ_PHENOMENA_P0_PLAN.json'
FILES=SOURCE_FILES+EXTRA+['tools/research_ops/confluence/'+n+'.py' for n in ('geometry_counts','phenomena','phenomena_pilot')]+[PLAN]
BOOT='''import os,sys,json,pathlib,hashlib,base64,zlib,tempfile,subprocess,time,signal,resource,urllib.request
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='1',PYTHONUNBUFFERED='1')
URL=__URL__
PIN=__PIN__
DATA=__DATA__
SHA=__SHA__
COMMIT=__COMMIT__
assert pathlib.Path('/kaggle/working').is_dir(),'Kaggle host required'
raw=zlib.decompress(base64.b64decode(DATA));assert hashlib.sha256(raw).hexdigest()==SHA
bundle=json.loads(raw);root=pathlib.Path(tempfile.mkdtemp(prefix='edgelab-phenomena-private-'));out=pathlib.Path('/kaggle/working/phenomena-p0');out.mkdir(exist_ok=False)
for name,rec in bundle.items():
 assert not name.startswith('/') and '..' not in name.split('/')
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);b=base64.b64decode(rec['data']);assert hashlib.sha256(b).hexdigest()==rec['sha256'];p.write_bytes(b)
for pkg in ('tools','tools/research_ops','tools/research_ops/confluence'):
 p=root/pkg/'__init__.py';p.parent.mkdir(parents=True,exist_ok=True);p.touch()
plan=json.loads((root/'__PLAN__').read_bytes());began=time.monotonic()
state={'schema':'phenomena_p0_boot_v1','status':'RETRIEVING_PINNED_SOURCE','source_commit':COMMIT,'bundle_sha256':SHA,'plan_sha256':__PLAN_SHA__,'new_quality_audit':False,'holdout_opened':False,'outcomes_computed':False,'raw_exported':False,'pnl_computed':False,'limits_scope':'SINGLE_CHILD_PROCESS_GROUP_NOT_CGROUP'}
def save(): (out/'boot-receipt.json').write_text(json.dumps(state,indent=2)+'\\n')
save()
try:
 path=root/PIN['file'];h=hashlib.sha256();size=0
 with urllib.request.urlopen(URL,timeout=60) as response,path.open('xb') as f:
  while True:
   if time.monotonic()-began>plan['transport_wall_seconds']:raise TimeoutError('transport deadline')
   b=response.read(1048576)
   if not b:break
   size+=len(b)
   if size>PIN['bytes']:raise ValueError('transport byte budget')
   h.update(b);f.write(b)
 if size!=PIN['bytes'] or h.hexdigest()!=PIN['sha256']:raise ValueError('physical transport pin mismatch')
 state.update(status='RUNNING_MEASUREMENT_ONLY',transport_pin_verified=True,retrieval_seconds=time.monotonic()-began);save()
 def limits():
  os.setsid();resource.setrlimit(resource.RLIMIT_AS,(plan['address_space_bytes'],)*2);resource.setrlimit(resource.RLIMIT_CPU,(plan['cpu_seconds'],)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 peak=0;stop=None
 with (root/'runner-private.log').open('w') as log:
  p=subprocess.Popen([sys.executable,'-m','tools.research_ops.confluence.phenomena_pilot','--source',str(path),'--plan',str(root/'__PLAN__'),'--private-root',str(root/'feature-store-private'),'--receipt',str(out/'measurement-receipt.json')],cwd=root,stdout=log,stderr=log,preexec_fn=limits)
  while p.poll() is None:
   try:
    for line in pathlib.Path('/proc/'+str(p.pid)+'/status').read_text().splitlines():
     if line.startswith('VmRSS:'):peak=max(peak,int(line.split()[1])*1024)
   except FileNotFoundError:pass
   if time.monotonic()-began>plan['parent_wall_seconds']:stop='WALL_LIMIT'
   if peak>plan['rss_bytes']:stop='RSS_LIMIT'
   if stop:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    break
   time.sleep(.25)
  rc=p.wait()
 state.update(status='P0_MEASUREMENT_COMPLETE_NOT_EDGE' if rc==0 and stop is None else 'P0_FAILED_NO_EDGE_CLAIM',exit_code=rc,stop_reason=stop,sampled_child_peak_rss_bytes=peak,wall_seconds=time.monotonic()-began)
 if rc==0 and stop is None:state['measurement_receipt_sha256']=hashlib.sha256((out/'measurement-receipt.json').read_bytes()).hexdigest()
 save();print(state['status'],flush=True)
 if rc or stop:raise SystemExit(1)
except Exception as exc:
 state.update(status='P0_FAILED_NO_EDGE_CLAIM',exception_type=type(exc).__name__,wall_seconds=time.monotonic()-began);save();print(state['status'],type(exc).__name__,flush=True);raise SystemExit(1)
'''

def build_request(root,*,url,source_commit):
    root=Path(root);plan=json.loads((root/PLAN).read_bytes());pin=plan['pin'];validate_pin(pin)
    if type(source_commit) is not str or len(source_commit)!=40 or any(c not in '0123456789abcdef' for c in source_commit):raise ValueError('full committed build')
    if plan['schema']!='mnq_phenomena_p0_plan_v1' or plan['window_seconds']!=[5,20,60] or plan['grid_seconds']!=5:raise ValueError('fixed P0 roster')
    for k in ('outcomes','classify_states','holdout','pnl','raw_export','inference','canonical_brain_write'):
        if plan[k] is not False:raise ValueError('measurement-only P0')
    if (plan['wall_seconds'],plan['rss_bytes'],plan['max_session_ticks'],plan['max_anchors'],plan['max_private_bytes'],plan['cpu_seconds'],plan['address_space_bytes'],plan['transport_wall_seconds'],plan['parent_wall_seconds'])!=(900,4294967296,5000000,250000,536870912,900,6442450944,600,1500):raise ValueError('fixed finite host limits')
    u=urlsplit(url)
    if u.scheme!='https' or u.hostname!='storage.googleapis.com' or not u.path.startswith('/kagglesdsdata/datasets/') or not u.path.endswith('/MNQ/'+pin['file']):raise ValueError('exact approved source URL')
    files={}
    for name in dict.fromkeys(FILES):
        b=(root/name).read_bytes();files[name]={'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
    raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest()
    text=BOOT.replace('__URL__',repr(url)).replace('__PIN__',repr(pin)).replace('__DATA__',repr(base64.b64encode(zlib.compress(raw)).decode())).replace('__SHA__',repr(sha)).replace('__COMMIT__',repr(source_commit)).replace('__PLAN_SHA__',repr(digest(plan))).replace('__PLAN__',PLAN)
    compile(text,'private-phenomena-p0','exec')
    request={'request':{'slug':'nicolasbuttaro/edgelab-mnq-phenomena-p0','hasSlug':True,'newTitle':'EdgeLab MNQ phenomena P0','hasNewTitle':True,'text':text,'hasText':True,'language':'python','hasLanguage':True,'kernelType':'script','hasKernelType':True,'isPrivate':True,'hasIsPrivate':True,'enableGpu':False,'hasEnableGpu':True,'enableTpu':False,'hasEnableTpu':True,'enableInternet':True,'hasEnableInternet':True,'kernelExecutionType':'SaveAndRunAll','hasKernelExecutionType':True,'sessionTimeoutSeconds':1800,'hasSessionTimeoutSeconds':True,'dockerImage':'gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a','hasDockerImage':True}}
    receipt={'schema':'phenomena_p0_package_v1','source_commit':source_commit,'bundle_sha256':sha,'plan_sha256':digest(plan),'notebook_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'files_sha256':{k:v['sha256'] for k,v in files.items()},'private_cpu':True,'signed_url_published':False,'raw_data_packaged':False,'submitted':False,'outcomes_enabled':False}
    return request,receipt
