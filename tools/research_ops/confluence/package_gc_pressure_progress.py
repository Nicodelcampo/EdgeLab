"""Prepare-only exact private CPU pressure/progress atlas package."""
import base64,hashlib,json,zlib
from pathlib import Path
from urllib.parse import urlsplit
from .package_gc_a_support import BOOT as PREVIOUS_BOOT, dependency_files
from .gc_pressure_progress import PLAN,CAL_PATH,validate
from .build_target_free_pilot import digest
BOOT=PREVIOUS_BOOT.replace("confluence.gc_a_support_diagnostic","confluence.gc_pressure_progress").replace("a-support-pilot","pressure-progress-pilot").replace("a-support-receipt.json","pressure-progress-receipt.json").replace("a_support_receipt_sha256","pressure_progress_receipt_sha256").replace("TARGET_FREE_TRAINING_SUPPORT_COMPLETE_NOT_EDGE","TARGET_FREE_PRESSURE_PROGRESS_COMPLETE_NOT_EDGE").replace("A_SUPPORT_FAILED_NO_EDGE_CLAIM","PRESSURE_PROGRESS_FAILED_NO_EDGE_CLAIM").replace("gc_a_support_boot_v1","gc_pressure_progress_boot_v1")

def build_request(root, *, url, source_commit):
    root = Path(root)
    p = json.loads((root/PLAN).read_bytes())
    validate(p,json.loads((root/CAL_PATH).read_bytes()))
    pin = p["source"]["pin"]
    u = urlsplit(url)
    if (u.scheme != "https" or u.hostname != "storage.googleapis.com" or
            not u.path.startswith("/kagglesdsdata/datasets/") or
            not u.path.endswith("/"+pin["path_in_dataset"])):
        raise ValueError("exact existing GC source transport")
    if len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
        raise ValueError("full committed source")
    files = {}
    for name in dependency_files(root,"tools/research_ops/confluence/gc_pressure_progress.py")+[PLAN,CAL_PATH]:
        b = (root/name).read_bytes()
        files[name] = {"data":base64.b64encode(b).decode(),"sha256":hashlib.sha256(b).hexdigest()}
    raw = json.dumps(files,sort_keys=True,separators=(",",":")).encode()
    sha = hashlib.sha256(raw).hexdigest()
    text = BOOT.replace("__URL__",repr(url)).replace("__PIN__",repr(pin))
    text = text.replace("__DATA__",repr(base64.b64encode(zlib.compress(raw)).decode()))
    text = text.replace("__SHA__",repr(sha)).replace("__COMMIT__",repr(source_commit))
    text = text.replace("__PLAN_SHA__",repr(digest(p))).replace("__PLAN__",PLAN).replace("__ASSET__",repr("GC"))
    compile(text,"private-gc-a-support","exec")
    request = {"request":{
        "newTitle":"EdgeLab GC Pressure Progress Atlas V1","hasNewTitle":True,
        "text":text,"hasText":True,"language":"python","hasLanguage":True,
        "kernelType":"script","hasKernelType":True,"isPrivate":True,"hasIsPrivate":True,
        "enableGpu":False,"hasEnableGpu":True,"enableTpu":False,"hasEnableTpu":True,
        "enableInternet":True,"hasEnableInternet":True,
        "kernelExecutionType":"SaveAndRunAll","hasKernelExecutionType":True,
        "sessionTimeoutSeconds":p["requested_notebook_timeout_seconds"],"hasSessionTimeoutSeconds":True,
        "dockerImage":"gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a","hasDockerImage":True}}
    return request, {
        "schema":"gc_pressure_progress_package_v1","source_commit":source_commit,
        "bundle_sha256":sha,"plan_sha256":digest(p),"notebook_text_sha256":hashlib.sha256(text.encode()).hexdigest(),
        "files_sha256":{k:v["sha256"] for k,v in files.items()},"private_cpu":True,
        "signed_url_published":False,"raw_data_packaged":False,"submitted":False,
        "outcomes_requested":False,"confirmation":False,"holdout_opened":False,
    }