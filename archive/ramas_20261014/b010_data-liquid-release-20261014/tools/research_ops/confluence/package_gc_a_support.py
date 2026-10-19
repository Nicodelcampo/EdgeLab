"""Prepare-only exact private CPU bundle, no network or submission authority."""
import ast
import base64
import hashlib
import json
import zlib
from pathlib import Path
from urllib.parse import urlsplit
from .package_multiasset import BOOT as OLD_BOOT
from .gc_a_support_diagnostic import PLAN, CAL_PATH, validate
from .build_target_free_pilot import digest

BOOT = OLD_BOOT.replace("confluence.multiasset_crossfamily", "confluence.gc_a_support_diagnostic")
BOOT = BOOT.replace("'--asset',__ASSET__,", "")
BOOT = BOOT.replace("crossfamily-pilot", "a-support-pilot")
BOOT = BOOT.replace("crossfamily-receipt.json", "a-support-receipt.json")
BOOT = BOOT.replace("crossfamily_receipt_sha256", "a_support_receipt_sha256")
BOOT = BOOT.replace("DEVELOPMENT_CROSSFAMILY_COMPLETE_NOT_EDGE", "TARGET_FREE_TRAINING_SUPPORT_COMPLETE_NOT_EDGE")
BOOT = BOOT.replace("CROSSFAMILY_FAILED_NO_EDGE_CLAIM", "A_SUPPORT_FAILED_NO_EDGE_CLAIM")
BOOT = BOOT.replace("multiasset_crossfamily_boot_v1", "gc_a_support_boot_v1")
BOOT = BOOT.replace("'outcomes_requested':True", "'outcomes_requested':False").replace("state['outcomes_computed']=True", "state['outcomes_computed']=False")


def dependency_files(root):
    """Static transitive LOCAL imports; isolated startup test remains required."""
    root = Path(root)
    pending = ["tools/research_ops/confluence/gc_a_support_diagnostic.py"]
    seen = set()
    def add_module(module):
        for path in (module.replace(".", "/")+".py", module.replace(".", "/")+"/__init__.py"):
            if (root/path).is_file() and path not in seen:
                pending.append(path)
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        parts = path[:-3].split("/")
        package = parts[:-1]
        for n in range(1,len(package)+1):
            init = "/".join(package[:n])+"/__init__.py"
            if (root/init).is_file() and init not in seen:
                pending.append(init)
        for node in ast.walk(ast.parse((root/path).read_bytes())):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    add_module(alias.name)
            elif isinstance(node, ast.ImportFrom):
                base = package[:len(package)-node.level+1] if node.level else []
                module = ".".join(base + (node.module.split(".") if node.module else []))
                add_module(module)
                for alias in node.names:
                    add_module(module+"."+alias.name)
    return sorted(seen)


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
    for name in dependency_files(root)+[PLAN,CAL_PATH]:
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
        "newTitle":"EdgeLab GC A Support Diagnostic V1","hasNewTitle":True,
        "text":text,"hasText":True,"language":"python","hasLanguage":True,
        "kernelType":"script","hasKernelType":True,"isPrivate":True,"hasIsPrivate":True,
        "enableGpu":False,"hasEnableGpu":True,"enableTpu":False,"hasEnableTpu":True,
        "enableInternet":True,"hasEnableInternet":True,
        "kernelExecutionType":"SaveAndRunAll","hasKernelExecutionType":True,
        "sessionTimeoutSeconds":p["requested_notebook_timeout_seconds"],"hasSessionTimeoutSeconds":True,
        "dockerImage":"gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a","hasDockerImage":True}}
    return request, {
        "schema":"gc_a_support_package_v1","source_commit":source_commit,
        "bundle_sha256":sha,"plan_sha256":digest(p),"notebook_text_sha256":hashlib.sha256(text.encode()).hexdigest(),
        "files_sha256":{k:v["sha256"] for k,v in files.items()},"private_cpu":True,
        "signed_url_published":False,"raw_data_packaged":False,"submitted":False,
        "outcomes_requested":False,"confirmation":False,"holdout_opened":False,
    }