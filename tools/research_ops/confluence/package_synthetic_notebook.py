"""Package an offline private Kaggle engineering probe, without market inputs.

Uses an explicit source allowlist. No credentials, signed URLs or data mounts.
Creates a save_notebook request, does not submit it. SaveAndRunAll is explicit.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import zlib

SOURCE_FILES=[
 'edgelab/__init__.py','edgelab/instruments.py','edgelab/data/__init__.py','edgelab/data/nt8_contract.py',
 'edgelab/bridge/__init__.py','edgelab/bridge/ticks.py','edgelab/bridge/bars.py','edgelab/bridge/common.py','edgelab/bridge/sessions.py',
 'edgelab/bridge/indicators/__init__.py',
 *['edgelab/bridge/indicators/'+n+'.py' for n in ('aacloseopendiffs','avolcellpoi2','bigtrap2','bigtrap2absorption','gaps2','hftzones2','voltickspoc2')],
 *['tools/research_ops/confluence/'+n+'.py' for n in ('asof_intersections','racimo_asof','build_target_free_pilot','_pinned_avzp2','_pinned_total_footprint','detector_capture','episodes','arrival','replay','pilot_runtime')],
 'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json']

BOOTSTRAP='''import os,sys,json,pathlib,hashlib,base64,zlib,tempfile,subprocess,time,signal,resource
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='1',PYTHONUNBUFFERED='1')
DATA=__BUNDLE__
EXPECTED=__SHA__
LINEAGE=__LINEAGE__
raw=zlib.decompress(base64.b64decode(DATA))
assert hashlib.sha256(raw).hexdigest()==EXPECTED,'bundle mismatch'
bundle=json.loads(raw)
root=pathlib.Path(tempfile.mkdtemp(prefix='edgelab-synthetic-pilot-'))
out=pathlib.Path('/kaggle/working/confluence-synthetic-pilot');out.mkdir(exist_ok=False)
for name,rec in bundle.items():
 assert name and not name.startswith('/') and '..' not in name.split('/'),'unsafe path'
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);data=base64.b64decode(rec['data'])
 assert hashlib.sha256(data).hexdigest()==rec['sha256'],'file mismatch'
 p.write_bytes(data)
for pkg in ('tools','tools/research_ops','tools/research_ops/confluence'):
 p=root/pkg/'__init__.py';p.parent.mkdir(parents=True,exist_ok=True);p.touch()
state={'schema':'confluence_synthetic_kaggle_boot_v1','status':'STARTING_SYNTHETIC_ONLY','market_data_read':False,'holdout_opened':False,'outcomes_computed':False,'pnl_computed':False,'bundle_sha256':EXPECTED,'source_commit':LINEAGE,'input_mounts_used':False,'internet_required':False,'budgets':{'wall_seconds':900,'address_space_bytes':4294967296,'rss_stop_bytes':2147483648,'cpu_seconds':840},'limits_scope':'KNOWN_SINGLE_CHILD_PROCESS_GROUP_NOT_CGROUP'}
state_file=out/'boot-receipt.json'
def persist():state_file.write_text(json.dumps(state,indent=2)+'\\n')
def child_limits():
 os.setsid()
 resource.setrlimit(resource.RLIMIT_AS,(4294967296,4294967296))
 resource.setrlimit(resource.RLIMIT_CPU,(840,840))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
persist();started=time.monotonic();peak=0;stop=None
cmd=[sys.executable,'-m','tools.research_ops.confluence.pilot_runtime','--roster',str(root/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json'),'--out',str(out/'pilot-receipt.json'),'--sessions','25','--ticks-per-session','1200','--deadline-seconds','780']
with (out/'pilot.log').open('w') as log:
 p=subprocess.Popen(cmd,cwd=root,stdout=log,stderr=log,preexec_fn=child_limits)
 while p.poll() is None:
  try:
   for line in pathlib.Path('/proc/'+str(p.pid)+'/status').read_text().splitlines():
    if line.startswith('VmRSS:'):peak=max(peak,int(line.split()[1])*1024)
  except FileNotFoundError:pass
  if time.monotonic()-started>900:stop='WALL_LIMIT'
  if peak>2147483648:stop='RSS_LIMIT'
  if stop:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   break
  time.sleep(.25)
 rc=p.wait()
state.update(status='SYNTHETIC_COMPLETE_NOT_MNQ_RESULTS' if rc==0 and stop is None else 'SYNTHETIC_FAILED_NO_MARKET_RUN',exit_code=rc,stop_reason=stop,wall_seconds=time.monotonic()-started,sampled_child_peak_rss_bytes=peak,hard_address_space_limit_applied=True)
if rc==0 and stop is None:
 receipt=json.loads((out/'pilot-receipt.json').read_bytes())
 assert receipt['status']=='SYNTHETIC_COMPLETE_NOT_MNQ_RESULTS' and receipt['market_data_read'] is False
 state['pilot_receipt_sha256']=hashlib.sha256((out/'pilot-receipt.json').read_bytes()).hexdigest()
persist();print(json.dumps(state,indent=2),flush=True)
if rc or stop:raise RuntimeError('bounded synthetic pilot failed; see aggregate boot receipt')
'''

def build_request(root,*,source_commit,slug='nicolasbuttaro/edgelab-confluence-synthetic-pilot'):
    root=Path(root)
    if len(source_commit)!=40 or any(c not in '0123456789abcdef' for c in source_commit):raise ValueError('full source commit pin required')
    files={}
    for p in SOURCE_FILES:
        raw=(root/p).read_bytes();files[p]={'data':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
    raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest()
    text=BOOTSTRAP.replace('__BUNDLE__',repr(base64.b64encode(zlib.compress(raw,9)).decode())).replace('__SHA__',repr(sha)).replace('__LINEAGE__',repr(source_commit))
    compile(text,'synthetic-kaggle-notebook','exec')
    request={'request':{'slug':slug,'hasSlug':True,'newTitle':'EdgeLab confluence synthetic engineering pilot','hasNewTitle':True,'text':text,'hasText':True,'language':'python','hasLanguage':True,'kernelType':'script','hasKernelType':True,'isPrivate':True,'hasIsPrivate':True,'enableGpu':False,'hasEnableGpu':True,'enableTpu':False,'hasEnableTpu':True,'enableInternet':False,'hasEnableInternet':True,'kernelExecutionType':'SaveAndRunAll','hasKernelExecutionType':True,'sessionTimeoutSeconds':1200,'hasSessionTimeoutSeconds':True}}
    return request,{'schema':'confluence_synthetic_package_receipt_v1','bundle_sha256':sha,'source_commit':source_commit,'files_sha256':{p:r['sha256'] for p,r in files.items()},'market_inputs_included':False,'signed_urls_included':False,'requires_internet':False,'submitted':False}

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',type=Path,required=True);a.add_argument('--source-commit',required=True);a.add_argument('--request-out',type=Path,required=True);a.add_argument('--receipt-out',type=Path,required=True);args=a.parse_args()
    if args.request_out.exists() or args.receipt_out.exists():raise ValueError('new output paths required')
    req,receipt=build_request(args.root,source_commit=args.source_commit)
    args.request_out.write_text(json.dumps(req));args.receipt_out.write_text(json.dumps(receipt,indent=2)+'\n');print('Prepared offline synthetic-only request; not submitted')
if __name__=='__main__':main()
