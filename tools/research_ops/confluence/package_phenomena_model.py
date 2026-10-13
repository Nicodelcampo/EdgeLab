"""Prepare-only private model representation package; no dispatch authority."""
import base64,hashlib,json,zlib
from pathlib import Path
from urllib.parse import urlsplit
from .package_phenomena_atlas import ATLAS_BOOT,FILES as ATLAS_FILES
from .source_footer import validate_pin
from .build_target_free_pilot import digest
from .phenomena_model_pilot import validate_plan,CAL_PATH
PLAN='docs/research/ops/MNQ_PHENOMENA_MODEL_PLAN.json'
FILES=ATLAS_FILES+['tools/research_ops/confluence/'+n+'.py' for n in ('phenomena_states','phenomena_response','phenomena_science_pilot','phenomena_models','phenomena_model_pilot','source_footer')]+[PLAN,CAL_PATH]
BOOT=ATLAS_BOOT.replace('edgelab-atlas-private-','edgelab-model-private-').replace('/phenomena-atlas','/phenomena-model-pilot').replace('phenomena_atlas_boot_v1','phenomena_model_boot_v1').replace('confluence.phenomena_atlas','confluence.phenomena_model_pilot').replace('atlas-receipt.json','model-receipt.json').replace('atlas_receipt_sha256','model_receipt_sha256').replace('ATLAS_MEASUREMENT_COMPLETE_NOT_EDGE','DEVELOPMENT_MODEL_COMPLETE_NOT_EDGE').replace('ATLAS_FAILED_NO_EDGE_CLAIM','MODEL_FAILED_NO_EDGE_CLAIM').replace('RUNNING_MEASUREMENT_ONLY','RUNNING_FIXED_REPRESENTATION_BENCHMARK').replace("'outcomes_computed':False","'outcomes_requested':True,'outcomes_computed':False")
BOOT=BOOT.replace("if rc==0 and stop is None:state['model_receipt_sha256']=hashlib.sha256((out/'model-receipt.json').read_bytes()).hexdigest()", "if rc==0 and stop is None:state['model_receipt_sha256']=hashlib.sha256((out/'model-receipt.json').read_bytes()).hexdigest();state['outcomes_computed']=True")
def build_request(root,*,url,source_commit):
    root=Path(root);plan=validate_plan(json.loads((root/PLAN).read_bytes()));pin=plan['pin'];validate_pin(pin)
    if type(source_commit) is not str or len(source_commit)!=40 or any(c not in '0123456789abcdef' for c in source_commit):raise ValueError('full committed build')
    u=urlsplit(url)
    if u.scheme!='https' or u.hostname!='storage.googleapis.com' or not u.path.startswith('/kagglesdsdata/datasets/') or not u.path.endswith('/MNQ/'+pin['file']):raise ValueError('exact approved source URL')
    files={}
    for name in dict.fromkeys(FILES):
        b=(root/name).read_bytes();files[name]={'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
    raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest()
    text=BOOT.replace('__URL__',repr(url)).replace('__PIN__',repr(pin)).replace('__DATA__',repr(base64.b64encode(zlib.compress(raw)).decode())).replace('__SHA__',repr(sha)).replace('__COMMIT__',repr(source_commit)).replace('__PLAN_SHA__',repr(digest(plan))).replace('__PLAN__',PLAN)
    compile(text,'private-phenomena-model-pilot','exec')
    request={'request':{'slug':'nicolasbuttaro/edgelab-mnq-phenomena-model-pilot','hasSlug':True,'newTitle':'EdgeLab MNQ phenomena model benchmark','hasNewTitle':True,'text':text,'hasText':True,'language':'python','hasLanguage':True,'kernelType':'script','hasKernelType':True,'isPrivate':True,'hasIsPrivate':True,'enableGpu':False,'hasEnableGpu':True,'enableTpu':False,'hasEnableTpu':True,'enableInternet':True,'hasEnableInternet':True,'kernelExecutionType':'SaveAndRunAll','hasKernelExecutionType':True,'sessionTimeoutSeconds':3600,'hasSessionTimeoutSeconds':True,'dockerImage':'gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a','hasDockerImage':True}}
    receipt={'schema':'phenomena_model_package_v1','source_commit':source_commit,'bundle_sha256':sha,'plan_sha256':digest(plan),'notebook_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'files_sha256':{k:v['sha256'] for k,v in files.items()},'private_cpu':True,'signed_url_published':False,'raw_data_packaged':False,'submitted':False,'outcomes_requested':True,'inference':False,'confirmation':False}
    return request,receipt
