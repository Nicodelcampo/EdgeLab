"""Private market pilot bootstrap: approved pinned source only in Kaggle tmp.

No new footer/quality audit. Hash during transfer binds transport to existing pin.
Known child process-group budgets; not cgroup or unrestricted automation.
"""
import base64,hashlib,json,zlib
from pathlib import Path
from urllib.parse import urlsplit
from .package_synthetic_notebook import SOURCE_FILES
from .source_footer import validate_pin
from .build_target_free_pilot import digest

EXTRA=['tools/research_ops/confluence/'+n+'.py' for n in ('avz_stream','bt2_stream','bt2a_stream','session_primitives','kaggle_session_reader','geometry_replay','market_pilot','failure_telemetry','geometry_counts')]+['docs/research/ops/MNQ_CONFLUENCE_MARKET_PILOT_PLAN.json','docs/research/ops/MNQ_CONFLUENCE_MARKET_PILOT_RETRY_PLAN.json','docs/research/ops/MNQ_CONFLUENCE_MARKET_DIAGNOSTIC_PLAN.json']
BOOT='''import os,sys,json,pathlib,hashlib,base64,zlib,tempfile,subprocess,time,signal,resource,urllib.request
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='1',PYTHONUNBUFFERED='1')
URL=__URL__
PIN=__PIN__
DATA=__DATA__
BUNDLE_SHA=__SHA__
COMMIT=__COMMIT__
raw=zlib.decompress(base64.b64decode(DATA));assert hashlib.sha256(raw).hexdigest()==BUNDLE_SHA
bundle=json.loads(raw);root=pathlib.Path(tempfile.mkdtemp(prefix='edgelab-mnq-private-pilot-'));out=pathlib.Path('/kaggle/working/confluence-market-pilot');out.mkdir(exist_ok=False)
for name,rec in bundle.items():
 assert not name.startswith('/') and '..' not in name.split('/')
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);data=base64.b64decode(rec['data']);assert hashlib.sha256(data).hexdigest()==rec['sha256'];p.write_bytes(data)
for pkg in ('tools','tools/research_ops','tools/research_ops/confluence'):
 p=root/pkg/'__init__.py';p.parent.mkdir(parents=True,exist_ok=True);p.touch()
plan=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_MARKET_DIAGNOSTIC_PLAN.json').read_bytes());started=time.monotonic()
state={'schema':'mnq_confluence_market_pilot_boot_v1','status':'RETRIEVING_APPROVED_SOURCE','source_commit':COMMIT,'bundle_sha256':BUNDLE_SHA,'holdout_opened':False,'outcomes_computed':False,'pnl_computed':False,'raw_exported':False,'source_quality_certified':False,'new_dataset_quality_audit':False,'limits_scope':'KNOWN_SINGLE_CHILD_PROCESS_GROUP_NOT_CGROUP'}
def save(): (out/'boot-receipt.json').write_text(json.dumps(state,indent=2)+'\\n')
save()
try:
 path=root/PIN['file'];h=hashlib.sha256();count=0
 with urllib.request.urlopen(URL,timeout=60) as response,path.open('xb') as f:
  while True:
   if time.monotonic()-started>600:raise TimeoutError('retrieval deadline')
   block=response.read(1048576)
   if not block:break
   count+=len(block)
   if count>PIN['bytes']:raise ValueError('transport byte budget')
   h.update(block);f.write(block)
 if count!=PIN['bytes'] or h.hexdigest()!=PIN['sha256']:raise ValueError('transport pin mismatch')
 state.update(status='RUNNING_TARGET_FREE_MARKET_PILOT',transport_pin_verified=True,retrieval_seconds=time.monotonic()-started);save()
 def limits():
  os.setsid();resource.setrlimit(resource.RLIMIT_AS,(plan['address_space_bytes'],)*2);resource.setrlimit(resource.RLIMIT_CPU,(plan['cpu_seconds'],)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 peak=0;stop=None
 with (root/'pilot-private.log').open('w') as log:
  p=subprocess.Popen([sys.executable,'-m','tools.research_ops.confluence.market_pilot','--source',str(path),'--root',str(root),'--out',str(out/'pilot-receipt.json')],cwd=root,stdout=log,stderr=log,preexec_fn=limits)
  while p.poll() is None:
   try:
    for line in pathlib.Path('/proc/'+str(p.pid)+'/status').read_text().splitlines():
     if line.startswith('VmRSS:'):peak=max(peak,int(line.split()[1])*1024)
   except FileNotFoundError:pass
   if time.monotonic()-started>plan['parent_wall_seconds']:stop='WALL_LIMIT'
   if peak>plan['rss_stop_bytes']:stop='RSS_LIMIT'
   if stop:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    break
   time.sleep(.5)
  rc=p.wait()
 # Only known aggregate progress lines, not arbitrary traceback/raw payload.
 lines=(root/'pilot-private.log').read_text(errors='replace').splitlines()
 (out/'aggregate-progress.log').write_text('\\n'.join(s for s in lines if s.startswith(('SESSION_COMPLETE ','GEOMETRY_TRIAD_COMPLETE ','TARGET_FREE_MARKET_PILOT_COMPLETE','PILOT_FAILED ')))+'\\n')
 state.update(status='TARGET_FREE_MARKET_PILOT_COMPLETE_NOT_VALIDATED_EDGE' if rc==0 and stop is None else 'MARKET_PILOT_FAILED_NO_EDGE_CLAIM',exit_code=rc,stop_reason=stop,sampled_child_peak_rss_bytes=peak,wall_seconds=time.monotonic()-started)
 if (out/'partial-receipt.json').exists():state['partial_receipt_sha256']=hashlib.sha256((out/'partial-receipt.json').read_bytes()).hexdigest()
 if (out/'failure-receipt.json').exists():
  state['failure_receipt_sha256']=hashlib.sha256((out/'failure-receipt.json').read_bytes()).hexdigest()
  state['failure_category']=json.loads((out/'failure-receipt.json').read_bytes())['failure_category']
 if rc==0 and stop is None:state['pilot_receipt_sha256']=hashlib.sha256((out/'pilot-receipt.json').read_bytes()).hexdigest()
 save();print(state['status'],flush=True)
 if rc or stop:raise SystemExit(1)
except Exception as exc:
 state.update(status='MARKET_PILOT_FAILED_NO_EDGE_CLAIM',error_type=type(exc).__name__,wall_seconds=time.monotonic()-started);save();print(state['status'],type(exc).__name__,flush=True);raise SystemExit(1)
'''

def build_request(root,*,url,source_commit):
    root=Path(root);plan=json.loads((root/EXTRA[-1]).read_bytes());pin=plan['pin'];validate_pin(pin)
    if len(source_commit)!=40 or any(c not in '0123456789abcdef' for c in source_commit):raise ValueError('full committed code pin')
    u=urlsplit(url)
    if u.scheme!='https' or u.hostname!='storage.googleapis.com' or not u.path.startswith('/kagglesdsdata/datasets/') or not u.path.endswith('/MNQ/'+pin['file']):raise ValueError('exact Kaggle source URL')
    files={}
    for name in SOURCE_FILES+EXTRA:
        b=(root/name).read_bytes();files[name]={'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
    raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest();data=base64.b64encode(zlib.compress(raw)).decode()
    text=BOOT.replace('__URL__',repr(url)).replace('__PIN__',repr(pin)).replace('__DATA__',repr(data)).replace('__SHA__',repr(sha)).replace('__COMMIT__',repr(source_commit));compile(text,'private-mnq-pilot','exec')
    req={'request':{'newTitle':'EdgeLab MNQ dense confluence engineering pilot','hasNewTitle':True,'text':text,'hasText':True,'language':'python','hasLanguage':True,'kernelType':'script','hasKernelType':True,'isPrivate':True,'hasIsPrivate':True,'enableGpu':False,'hasEnableGpu':True,'enableTpu':False,'hasEnableTpu':True,'enableInternet':True,'hasEnableInternet':True,'kernelExecutionType':'SaveAndRunAll','hasKernelExecutionType':True,'sessionTimeoutSeconds':7200,'hasSessionTimeoutSeconds':True}}
    receipt={'schema':'mnq_confluence_market_package_v1','source_commit':source_commit,'bundle_sha256':sha,'private_source_sha256':hashlib.sha256(text.encode()).hexdigest(),'code_files_sha256':{k:v['sha256'] for k,v in files.items()},'plan_sha256':digest(plan),'source_pin_sha256':validate_pin(pin),'signed_url_published':False,'raw_data_packaged':False,'scope':plan['scope'],'configs':96,'aligned_triads':32,'submitted':False}
    return req,receipt
