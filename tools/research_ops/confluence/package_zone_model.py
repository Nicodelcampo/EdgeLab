"""Prepare-only private zone-context notebook; no network or dispatch authority."""
import base64,hashlib,json,zlib
from pathlib import Path
from urllib.parse import urlsplit
from .package_phenomena_model import BOOT as MODEL_BOOT, FILES as MODEL_FILES
from .zone_model_pilot import PLAN, validate_plan
from .build_target_free_pilot import digest

FILES=MODEL_FILES+['tools/research_ops/confluence/'+n+'.py' for n in
                 ('zone_context','zone_model_design','zone_scene','zone_model_pilot')]+[PLAN]
BOOT=MODEL_BOOT.replace('edgelab-model-private-','edgelab-zone-private-').replace('/phenomena-model-pilot','/zone-context-pilot').replace('phenomena_model_boot_v1','zone_context_boot_v1').replace('confluence.phenomena_model_pilot','confluence.zone_model_pilot').replace('model-receipt.json','zone-receipt.json').replace('model_receipt_sha256','zone_receipt_sha256').replace('DEVELOPMENT_MODEL_COMPLETE_NOT_EDGE','DEVELOPMENT_ZONE_COMPLETE_NOT_EDGE').replace('MODEL_FAILED_NO_EDGE_CLAIM','ZONE_MODEL_FAILED_NO_EDGE_CLAIM').replace('RUNNING_FIXED_REPRESENTATION_BENCHMARK','RUNNING_FIXED_ZONE_CONTEXT_BENCHMARK')


def build_request(root,*,url,source_commit):
    root=Path(root);plan=validate_plan(json.loads((root/PLAN).read_bytes()));pin=plan['pin']
    if type(source_commit) is not str or len(source_commit)!=40 or any(c not in '0123456789abcdef' for c in source_commit):raise ValueError('full committed build')
    u=urlsplit(url)
    if u.scheme!='https' or u.hostname!='storage.googleapis.com' or not u.path.startswith('/kagglesdsdata/datasets/') or not u.path.endswith('/MNQ/'+pin['file']):raise ValueError('exact approved source URL')
    files={}
    for name in dict.fromkeys(FILES):
        b=(root/name).read_bytes();files[name]={'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
    raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest()
    text=BOOT.replace('__URL__',repr(url)).replace('__PIN__',repr(pin)).replace('__DATA__',repr(base64.b64encode(zlib.compress(raw)).decode())).replace('__SHA__',repr(sha)).replace('__COMMIT__',repr(source_commit)).replace('__PLAN_SHA__',repr(digest(plan))).replace('__PLAN__',PLAN)
    compile(text,'private-zone-context-pilot','exec')
    request={'request':{'slug':'nicolasbuttaro/edgelab-mnq-zone-context-benchmark','hasSlug':True,'newTitle':'EdgeLab MNQ continuous plus zone context benchmark','hasNewTitle':True,'text':text,'hasText':True,'language':'python','hasLanguage':True,'kernelType':'script','hasKernelType':True,'isPrivate':True,'hasIsPrivate':True,'enableGpu':False,'hasEnableGpu':True,'enableTpu':False,'hasEnableTpu':True,'enableInternet':True,'hasEnableInternet':True,'kernelExecutionType':'SaveAndRunAll','hasKernelExecutionType':True,'sessionTimeoutSeconds':plan['requested_notebook_timeout_seconds'],'hasSessionTimeoutSeconds':True,'dockerImage':'gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a','hasDockerImage':True}}
    receipt={'schema':'zone_context_package_v1','source_commit':source_commit,'bundle_sha256':sha,'plan_sha256':digest(plan),'notebook_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'files_sha256':{k:v['sha256'] for k,v in files.items()},'private_cpu':True,'signed_url_published':False,'raw_data_packaged':False,'submitted':False,'outcomes_requested':True,'evaluation_outcomes_previously_inspected':True,'inference':False,'confirmation':False}
    return request,receipt
