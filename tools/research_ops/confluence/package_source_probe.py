"""Prepare a private Kaggle-only pinned-footer probe. No submit or market loader.

The signed retrieval URL exists only in the private request, never in receipts.
Internet is for retrieval bootstrap; no detector, event or outcome is computed.
"""
from __future__ import annotations
import argparse,base64,hashlib,json
from pathlib import Path
from urllib.parse import urlsplit
from .source_footer import validate_pin

BOOT='''import os,sys,json,pathlib,tempfile,base64,hashlib,time,urllib.request,resource
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONUNBUFFERED='1')
PIN=__PIN__
URL=__URL__
FILES=__FILES__
COMMIT=__COMMIT__
root=pathlib.Path(tempfile.mkdtemp(prefix='edgelab-private-source-footer-'))
out=pathlib.Path('/kaggle/working/confluence-source-preflight');out.mkdir(exist_ok=False)
for name,rec in FILES.items():
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);data=base64.b64decode(rec['data']);assert hashlib.sha256(data).hexdigest()==rec['sha256'];p.write_bytes(data)
for pkg in ('tools','tools/research_ops','tools/research_ops/confluence'):
 p=root/pkg/'__init__.py';p.parent.mkdir(parents=True,exist_ok=True);p.touch()
sys.path.insert(0,str(root))
from tools.research_ops.confluence.source_footer import validate_pin,inspect_footer
validate_pin(PIN)
resource.setrlimit(resource.RLIMIT_AS,(4294967296,4294967296))
resource.setrlimit(resource.RLIMIT_CPU,(420,420))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
started=time.monotonic();state={'schema':'mnq_confluence_source_probe_boot_v1','status':'STARTING_METADATA_ONLY','source_commit':COMMIT,'contract':PIN['contract'],'price_payload_deserialized':False,'market_trials_executed':0,'holdout_opened':False,'pnl_computed':False,'raw_file_exported':False,'source_quality_certified':False,'execution_allowed':False,'transport':'SIGNED_URL_ONLY_INSIDE_PRIVATE_KAGGLE','limits_scope':'KNOWN_SINGLE_PROCESS_RLIMIT_AS_CPU_COOPERATIVE_DOWNLOAD_DEADLINE'}
def save(): (out/'boot-receipt.json').write_text(json.dumps(state,indent=2)+'\\n')
save()
try:
 file=root/PIN['file'];part=root/'source.partial';h=hashlib.sha256();count=0
 with urllib.request.urlopen(URL,timeout=60) as response,part.open('xb') as target:
  while True:
   if time.monotonic()-started>600:raise TimeoutError('source retrieval deadline')
   data=response.read(1024*1024)
   if not data:break
   count+=len(data)
   if count>PIN['bytes']:raise ValueError('source exceeds pin size')
   h.update(data);target.write(data)
 if count!=PIN['bytes'] or h.hexdigest()!=PIN['sha256']:raise ValueError('retrieved source pin mismatch')
 part.rename(file)
 receipt=inspect_footer(file,PIN)
 (out/'source-footer-receipt.json').write_text(json.dumps(receipt,indent=2)+'\\n')
 state.update(status=receipt['status'],physical_bytes_hashed=True,source_footer_receipt_sha256=hashlib.sha256((out/'source-footer-receipt.json').read_bytes()).hexdigest(),wall_seconds=time.monotonic()-started,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 save();print(state['status'],flush=True)
 if receipt['status']!='PASS_PINNED_FOOTER_ONLY_NOT_MARKET_APPROVAL':raise ValueError('source footer requirements blocked')
except Exception as exc:
 state.update(status='SOURCE_PROBE_FAILED_NOT_MARKET_APPROVAL',error_type=type(exc).__name__,wall_seconds=time.monotonic()-started);save();print('SOURCE_PROBE_FAILED',type(exc).__name__,flush=True);raise SystemExit(1)
'''


def build_request(root,*,pin,url,source_commit):
    validate_pin(pin)
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname!='storage.googleapis.com' or not parsed.path.startswith('/kagglesdsdata/datasets/') or not parsed.path.endswith('/MNQ/'+pin['file']):raise ValueError('expected exact Kaggle storage URL required')
    if len(source_commit)!=40 or any(c not in '0123456789abcdef' for c in source_commit):raise ValueError('full commit pin')
    files={}
    for name in ('tools/research_ops/confluence/source_footer.py','tools/research_ops/confluence/build_target_free_pilot.py'):
        raw=(Path(root)/name).read_bytes();files[name]={'data':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
    text=BOOT.replace('__PIN__',repr(pin)).replace('__URL__',repr(url)).replace('__FILES__',repr(files)).replace('__COMMIT__',repr(source_commit));compile(text,'private-source-probe','exec')
    req={'request':{'newTitle':'EdgeLab MNQ confluence source footer preflight','hasNewTitle':True,'text':text,'hasText':True,'language':'python','hasLanguage':True,'kernelType':'script','hasKernelType':True,'isPrivate':True,'hasIsPrivate':True,'enableGpu':False,'hasEnableGpu':True,'enableTpu':False,'hasEnableTpu':True,'enableInternet':True,'hasEnableInternet':True,'kernelExecutionType':'SaveAndRunAll','hasKernelExecutionType':True,'sessionTimeoutSeconds':900,'hasSessionTimeoutSeconds':True}}
    receipt={'schema':'mnq_confluence_source_probe_package_v1','source_commit':source_commit,'source_pin_sha256':validate_pin(pin),'code_files_sha256':{p:x['sha256'] for p,x in files.items()},'private_request_source_sha256':hashlib.sha256(text.encode()).hexdigest(),'signed_url_published':False,'raw_input_included':False,'scope':'PHYSICAL_PIN_AND_PARQUET_FOOTER_ONLY_NO_PRICE_ROWS','submitted':False}
    return req,receipt


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--pin',type=Path,required=True);ap.add_argument('--url-tool-result',type=Path,required=True);ap.add_argument('--source-commit',required=True);ap.add_argument('--request-out',type=Path,required=True);ap.add_argument('--receipt-out',type=Path,required=True);a=ap.parse_args()
    if a.request_out.exists() or a.receipt_out.exists():raise ValueError('new output paths required')
    tool=json.loads(a.url_tool_result.read_bytes());url=json.loads(tool['content'][0]['text'])['url'];req,r=build_request(a.root,pin=json.loads(a.pin.read_bytes()),url=url,source_commit=a.source_commit)
    a.request_out.write_text(json.dumps(req));a.receipt_out.write_text(json.dumps(r,indent=2)+'\n');print('Prepared Kaggle-only source footer probe; not submitted; no rows read')
if __name__=='__main__':main()
