"""Prepare one exact bounded technical profile; no submit/network authority."""
import base64,hashlib,json,zlib
from pathlib import Path
from urllib.parse import urlsplit
from .package_multiasset import FILES as OLD_FILES,BOOT as OLD_BOOT
from .bt2a_rolling_benchmark import PLAN,validate
from .build_target_free_pilot import digest
FILES=list(dict.fromkeys(OLD_FILES+['tools/research_ops/confluence/bt2a_multisession_profile.py','tools/research_ops/confluence/bt2a_rolling_benchmark.py','tools/research_ops/confluence/rolling_native_percentile.py',PLAN]))
BOOT=OLD_BOOT.replace('confluence.multiasset_crossfamily','confluence.bt2a_rolling_benchmark').replace("'outcomes_requested':True","'outcomes_requested':False").replace("state['outcomes_computed']=True","state['outcomes_computed']=False")
def build_request(root,*,url,source_commit):
 root=Path(root);p=json.loads((root/PLAN).read_bytes());a=validate(p,'GC');pin=a['pin'];u=urlsplit(url)
 if u.scheme!='https' or u.hostname!='storage.googleapis.com' or not u.path.endswith('/'+pin['path_in_dataset']):raise ValueError('exact profile source transport')
 if len(source_commit)!=40 or any(c not in '0123456789abcdef' for c in source_commit):raise ValueError('full committed profile source')
 files={}
 for name in FILES:
  b=(root/name).read_bytes();files[name]={'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
 raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest();text=BOOT.replace('__URL__',repr(url)).replace('__PIN__',repr(pin)).replace('__DATA__',repr(base64.b64encode(zlib.compress(raw)).decode())).replace('__SHA__',repr(sha)).replace('__COMMIT__',repr(source_commit)).replace('__PLAN_SHA__',repr(digest(p))).replace('__PLAN__',PLAN).replace('__ASSET__',repr('GC'));compile(text,'private-bt2a-profile','exec')
 request={'request':{'newTitle':'EdgeLab GC BT2A Rolling Percentile V1','hasNewTitle':True,'text':text,'hasText':True,'language':'python','hasLanguage':True,'kernelType':'script','hasKernelType':True,'isPrivate':True,'hasIsPrivate':True,'enableGpu':False,'hasEnableGpu':True,'enableTpu':False,'hasEnableTpu':True,'enableInternet':True,'hasEnableInternet':True,'kernelExecutionType':'SaveAndRunAll','hasKernelExecutionType':True,'sessionTimeoutSeconds':p['requested_notebook_timeout_seconds'],'hasSessionTimeoutSeconds':True,'dockerImage':'gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a','hasDockerImage':True}}
 return request,{'source_commit':source_commit,'bundle_sha256':sha,'plan_sha256':digest(p),'notebook_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'files_sha256':{k:v['sha256'] for k,v in files.items()},'private_cpu':True,'raw_exported':False,'outcomes_requested':False}
