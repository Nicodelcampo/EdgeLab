"""Prepare-only immutable per-asset private CPU package. No network/dispatch."""
import base64,hashlib,json,zlib
from pathlib import Path
from urllib.parse import urlsplit
from .package_crossfamily import BOOT as OLD_BOOT,FILES as OLD_FILES
from .multiasset_crossfamily import PLAN,validate_plan
from .build_target_free_pilot import digest
FILES=list(dict.fromkeys(OLD_FILES+['tools/research_ops/confluence/bt2a_footprint_cache.py','tools/research_ops/confluence/multiasset_crossfamily.py',PLAN]))
BOOT=OLD_BOOT.replace('crossfamily_boot_v1','multiasset_crossfamily_boot_v1').replace('confluence.cross_family_pilot','confluence.multiasset_crossfamily').replace("'--source',str(path)","'--asset',__ASSET__,'--source',str(path)").replace("'new_quality_audit':False", "'asset':__ASSET__,'new_quality_audit':False")
BOOT=BOOT.replace("state.update(status='RUNNING_FIXED_CROSSFAMILY_BENCHMARK'", "import pyarrow.parquet as pq\n if pq.ParquetFile(path).metadata.num_rows!=PIN['rows']:raise ValueError('asset pinned row identity')\n state.update(status='RUNNING_FIXED_CROSSFAMILY_BENCHMARK'")

def build_request(root,*,asset,url,source_commit):
 root=Path(root);p=json.loads((root/PLAN).read_bytes());a,_=validate_plan(p,asset);pin=a['pin'];u=urlsplit(url)
 if u.scheme!='https' or u.hostname!='storage.googleapis.com' or not u.path.startswith('/kagglesdsdata/datasets/') or not u.path.endswith('/'+pin['path_in_dataset']):raise ValueError('exact asset transport URL')
 if len(source_commit)!=40 or any(c not in '0123456789abcdef' for c in source_commit):raise ValueError('full committed multiasset source')
 files={}
 for name in FILES:
  b=(root/name).read_bytes();files[name]={'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
 raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest();text=BOOT.replace('__URL__',repr(url)).replace('__PIN__',repr(pin)).replace('__DATA__',repr(base64.b64encode(zlib.compress(raw)).decode())).replace('__SHA__',repr(sha)).replace('__COMMIT__',repr(source_commit)).replace('__PLAN_SHA__',repr(digest(p))).replace('__PLAN__',PLAN).replace('__ASSET__',repr(asset));compile(text,'private-multiasset-'+asset,'exec')
 req={'request':{'newTitle':'EdgeLab '+asset+' Crossfamily Arrival V1','hasNewTitle':True,'text':text,'hasText':True,'language':'python','hasLanguage':True,'kernelType':'script','hasKernelType':True,'isPrivate':True,'hasIsPrivate':True,'enableGpu':False,'hasEnableGpu':True,'enableTpu':False,'hasEnableTpu':True,'enableInternet':True,'hasEnableInternet':True,'kernelExecutionType':'SaveAndRunAll','hasKernelExecutionType':True,'sessionTimeoutSeconds':p['requested_notebook_timeout_seconds'],'hasSessionTimeoutSeconds':True,'dockerImage':'gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a','hasDockerImage':True}}
 receipt={'schema':'multiasset_package_v1','asset':asset,'source_commit':source_commit,'plan_sha256':digest(p),'bundle_sha256':sha,'notebook_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'files_sha256':{k:v['sha256'] for k,v in files.items()},'private_cpu':True,'signed_url_published':False,'raw_data_packaged':False,'confirmation':False,'holdout_opened':False,'canonical_brain_written':False};return req,receipt
