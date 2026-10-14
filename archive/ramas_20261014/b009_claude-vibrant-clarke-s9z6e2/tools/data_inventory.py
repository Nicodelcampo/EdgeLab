#!/usr/bin/env python3
"""Inventario crudo de TODOS los datasets propios de Kaggle: lista de archivos, textos pequeños (README, manifiestos) y un escaneo de cada parquet de ticks
(esquema, rango, tipos de tick, perfil por sesión). Escribe en --out/{datasets.json, scan/<dataset>/<archivo>.json, text/<dataset>/<archivo>}.
Descarga un archivo a la vez por hilo, lo escanea y lo borra. Usa archivos locales si existen (/data/raw/<ACTIVO>/...). Reanuda: lo ya escaneado se salta.
  python tools/data_inventory.py --out /data/catalog [--only slug1,slug2] [--workers 3] [--force]"""
import argparse,json,os,subprocess,sys,time,traceback
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.catalog.scan import scan_parquet
OWNER="nicolasbuttaro";TMP=Path("/data/tmp_inventory");TEXT_EXT=(".md",".txt",".json",".sha256",".csv",".yml",".yaml",".jsonl")

def api(path:str)->dict|list:
    import random
    err=""
    for k in range(7):
        r=subprocess.run(["curl","-sS","--fail-with-body",f"https://www.kaggle.com/api/v1/{path}"],capture_output=True,text=True)
        if r.returncode==0:return json.loads(r.stdout)
        err=(r.stdout[:150]+r.stderr[:100])
        if "404" in err:break
        time.sleep(min(60,4*2**k)+random.random()*3)
    raise RuntimeError(f"{path}: {err}")

def list_datasets()->list[dict]:
    out=[];p=1
    while True:
        d=api(f"datasets/list?group=my&page={p}")
        if not d:break
        out+=d;p+=1
    return out

def list_files(slug:str)->list[dict]:
    files=[];tok=None
    while True:
        j=api(f"datasets/list/{OWNER}/{slug}?pageSize=200"+(f"&pageToken={tok}" if tok else ""));files+=j.get("datasetFiles",[]);tok=j.get("nextPageToken")
        if not tok:break
    return [{"name":x["name"],"bytes":x["totalBytes"],"created":x.get("creationDate")} for x in files]

def download(slug:str,name:str,dest:Path,owner:str=OWNER)->None:
    """Descarga con reintentos ante 429/5xx (retroceso creciente con jitter)."""
    import random
    dest.parent.mkdir(parents=True,exist_ok=True);err=""
    for k in range(5):
        r=subprocess.run(["curl","-sSL","--fail","-o",str(dest),f"https://www.kaggle.com/api/v1/datasets/download/{owner}/{slug}?fileName={quote(name)}"],capture_output=True,text=True)
        if r.returncode==0:return
        err=r.stderr[:200]
        if "404" in err:break
        time.sleep(min(60,3*2**k)+random.random()*3)
    raise RuntimeError(f"descarga {slug}/{name}: {err}")

def local_path(slug:str,name:str)->Path|None:
    if slug.startswith("edgelab-ticks-") and slug.endswith("-preholdout"):
        a=slug.split("-")[2].upper();p=Path(f"/data/raw/{a}/{name}")
        if p.exists():return p
    return None

def work(job:tuple,out:Path,force:bool):
    slug,f=job;name=f["name"];res=out/"scan"/slug/(name.replace("/","__")+".json");res.parent.mkdir(parents=True,exist_ok=True)
    if res.exists() and not force:return slug,name,"salteado"
    t=time.time()
    try:
        lp=local_path(slug,name);tmp=None
        if lp is None:tmp=TMP/slug/name.replace("/","__");download(slug,name,tmp);lp=tmp
        r=scan_parquet(str(lp));r.update({"dataset":slug,"file":name,"bytes":f["bytes"],"source":"local" if tmp is None else "kaggle","scan_seconds":round(time.time()-t,1)})
        res.write_text(json.dumps(r,default=float))
        if tmp is not None:tmp.unlink(missing_ok=True)
        return slug,name,f"ok {r.get('trades','-')} trades {r['scan_seconds']}s"
    except Exception as e:
        return slug,name,"ERROR "+repr(e)[:300]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);ap.add_argument("--only",default=None);ap.add_argument("--workers",type=int,default=3);ap.add_argument("--force",action="store_true");ap.add_argument("--min-bytes",type=int,default=5_000_000);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
    ds=list_datasets();only=set(a.only.split(",")) if a.only else None;listing=[];jobs=[];texts=[]
    for d in ds:
        ref=d["ref"].strip("/").split("/")[-1];own=d["ref"].strip("/").split("/")[1]
        if only and ref not in only:continue
        cf=out/'listing_cache'/f'{ref}.json'
        if cf.exists():files=json.loads(cf.read_text())
        else:
            files=list_files(ref);cf.parent.mkdir(parents=True,exist_ok=True);cf.write_text(json.dumps(files));time.sleep(1)
        listing.append({"slug":ref,"owner":own,"private":bool(d.get("isPrivate")),"bytes":d.get("totalBytes"),"last_updated":d.get("lastUpdated"),"title":d.get("title"),"files":files})
        for f in files:
            if f["name"].endswith(".parquet"):
                if f["bytes"]>=a.min_bytes or "ticks" in f["name"].lower() or "dukascopy" in ref:jobs.append((ref,f))
            elif f["name"].lower().endswith(TEXT_EXT) and f["bytes"]<=300_000 and "/" not in f["name"] and ("readme" in f["name"].lower() or "sha256" in f["name"].lower() or "catalog" in f["name"].lower() or "manifest" in f["name"].lower()):texts.append((ref,f,own))
    (out/"datasets.json").write_text(json.dumps(listing,indent=1));print("datasets",len(listing),"parquet",len(jobs),flush=True)
    jobs.sort(key=lambda j:-j[1]["bytes"])
    with ThreadPoolExecutor(a.workers) as ex:
        for s,n,m in ex.map(lambda j:work(j,out,a.force),jobs):print(s,n,m,flush=True)
    for ref,f,own in texts:
        p=out/"text"/ref/f["name"].replace("/","__")
        if not p.exists():
            try:download(ref,f["name"],p,own);time.sleep(2)
            except Exception as e:print("texto no descargado",ref,f["name"],str(e)[:120],flush=True)
    print("FIN",flush=True)
if __name__=="__main__":main()
