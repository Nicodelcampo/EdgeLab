"""Prepare-only repaired one-shot support package; no dispatch or journal reset."""
import json,hashlib,zlib,base64,subprocess
from pathlib import Path
from .package_multiasset import FILES
from .build_target_free_pilot import digest
BOOT="""import os,sys,json,pathlib,hashlib,base64,zlib,tempfile,subprocess,time,signal,resource,urllib.request
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='1',PYTHONUNBUFFERED='1')
SOURCES=__SOURCES__
DATA=__DATA__
SHA=__SHA__
COMMIT=__COMMIT__
PLAN_SHA=__PLAN_SHA__
OUT=pathlib.Path('/kaggle/working/multiasset-support');OUT.mkdir(parents=True,exist_ok=True)
state={'schema':'multiasset_support_boot_v1','source_commit':COMMIT,'bundle_sha256':SHA,'plan_sha256':PLAN_SHA,'status':'STARTING','raw_exported':False,'holdout_opened':False,'model_scores_computed':False}
start=time.monotonic()
try:
 state['stage']='CREATE_PRIVATE_ROOT'
 root=pathlib.Path(tempfile.mkdtemp(prefix='multiasset-support-'))
 state['stage']='UNPACK_COMMITTED_BUNDLE'
 raw=zlib.decompress(base64.b64decode(DATA));assert hashlib.sha256(raw).hexdigest()==SHA
 for name,v in json.loads(raw).items():
  p=root/name;assert '..' not in pathlib.Path(name).parts and not pathlib.Path(name).is_absolute();p.parent.mkdir(parents=True,exist_ok=True);b=base64.b64decode(v['data']);assert hashlib.sha256(b).hexdigest()==v['sha256'];p.write_bytes(b)
 src=root/'private-source';src.mkdir()
 state['stage']='TRANSPORT_PINNED_SOURCES'
 for asset,v in SOURCES.items():
  pin=v['pin'];p=src/pin['file'];h=hashlib.sha256();n=0
  with urllib.request.urlopen(v['url'],timeout=90) as r,p.open('wb') as f:
   while True:
    b=r.read(1048576)
    if not b:break
    n+=len(b);assert n<=pin['bytes'];h.update(b);f.write(b)
    if time.monotonic()-start>300:raise TimeoutError()
  assert n==pin['bytes'] and h.hexdigest()==pin['sha256']
  import pyarrow.parquet as pq
  assert pq.ParquetFile(p).metadata.num_rows==pin['rows']
 state['transport_pins_verified']=True
 def limits():
  os.setsid();resource.setrlimit(resource.RLIMIT_CPU,(600,600));resource.setrlimit(resource.RLIMIT_AS,(6442450944,6442450944));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 state['stage']='RUN_BOUNDED_SUPPORT'
 with (root/'private.log').open('wb') as log:
  child=subprocess.Popen([sys.executable,'-m','tools.research_ops.confluence.multiasset_support_probe','--source-root',str(src),'--receipt',str(OUT/'support-receipt.json')],cwd=root,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits)
  try:code=child.wait(timeout=900)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait();raise TimeoutError()
 state['exit_code']=code;state['status']='SUPPORT_DIAGNOSIS_COMPLETE_NOT_MODEL_RESULTS' if code==0 else 'SUPPORT_DIAGNOSIS_FAILED'
 p=OUT/'support-receipt.json'
 if code==0:
  assert p.stat().st_size<=262144;state['support_receipt_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
except Exception as e:
 state['status']='SUPPORT_DIAGNOSIS_FAILED';state['exception_type']=type(e).__name__ if type(e) in (TimeoutError,AssertionError,MemoryError,FileNotFoundError) else 'UNCLASSIFIED_EXCEPTION'
state['wall_seconds']=time.monotonic()-start;(OUT/'boot-receipt.json').write_text(json.dumps(state)+'\\n')
if state['status']!='SUPPORT_DIAGNOSIS_COMPLETE_NOT_MODEL_RESULTS':raise SystemExit(1)
"""

def build_request(root,*,urls,source_commit):
 root=Path(root);files={}
 for f in list(dict.fromkeys(FILES+['tools/research_ops/confluence/multiasset_support_probe.py','docs/research/ops/MULTIASSET_SUPPORT_PROBE_PLAN.json','tools/research_ops/confluence/package_support_probe.py'])):
  b=(root/f).read_bytes();files[f]={'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
 raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode();bsha=hashlib.sha256(raw).hexdigest();probe=json.loads((root/'docs/research/ops/MULTIASSET_SUPPORT_PROBE_PLAN.json').read_bytes());plan=json.loads((root/'docs/research/ops/MULTIASSET_CROSSFAMILY_PLAN.json').read_bytes())
 from urllib.parse import urlsplit
 sources={}
 for a in probe['assets']:
  pin=plan['assets'][a]['pin'];u=urlsplit(urls[a]);assert u.scheme=='https' and u.hostname=='storage.googleapis.com' and u.path.endswith('/'+pin['path_in_dataset']);sources[a]={'url':urls[a],'pin':pin}
 text=BOOT
 for k,v in {'__SOURCES__':repr(sources),'__DATA__':repr(base64.b64encode(zlib.compress(raw)).decode()),'__SHA__':repr(bsha),'__COMMIT__':repr(source_commit),'__PLAN_SHA__':repr(digest(probe))}.items():text=text.replace(k,v)
 compile(text,'private_support_v2','exec')
 req={'request':{'newTitle':'EdgeLab Multiasset Support Diagnosis V2','hasNewTitle':True,'text':text,'hasText':True,'language':'python','hasLanguage':True,'kernelType':'script','hasKernelType':True,'isPrivate':True,'hasIsPrivate':True,'enableGpu':False,'hasEnableGpu':True,'enableTpu':False,'hasEnableTpu':True,'enableInternet':True,'hasEnableInternet':True,'kernelExecutionType':'SaveAndRunAll','hasKernelExecutionType':True,'sessionTimeoutSeconds':1200,'hasSessionTimeoutSeconds':True,'dockerImage':'gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a','hasDockerImage':True}}
 pkg={'schema':'multiasset_support_package_v2','source_commit':source_commit,'bundle_sha256':bsha,'plan_sha256':digest(probe),'notebook_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'files_sha256':{k:v['sha256'] for k,v in files.items()},'assets':probe['assets'],'private_cpu':True,'signed_urls_published':False,'raw_exported':False,'model_scores_computed':False,'private_temp_root_uses_standard_tempfile':True};return req,pkg
