#!/usr/bin/env python3
"""Lanza un kernel de Kaggle SOLO si todos los datos que necesita existen hoy en Kaggle. Antes de gastar tiempo de kernel:
  1) por cada pedido INST:DESDE:HASTA, toma las sesiones aprobadas del resolver y comprueba, contra la lista VIVA de archivos de Kaggle, que haya el primario o una alternativa
     consistente; si alguna sesión no tiene ninguna fuente, NO lanza y dice exactamente qué falta;
  2) adjunta solo los datasets necesarios (primarios + alternativas usadas) más edgelab-data-catalog y los extras pedidos;
  3) respeta el holdout (el resolver ni lista sesiones desde 2026-10-01).
  python tools/kaggle_launch.py --slug nicolasbuttaro/mi-kernel --script mi_script.py --need MES:2025-07-01:2026-09-30 --extra-dataset nicolasbuttaro/edgelab-dukascopy-es-usa500 [--internet] [--gpu] [--dry-run]"""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"tools"));sys.path.insert(0,str(ROOT/"docs/data_catalog"))
import edgelab_data as ed
from data_inventory import list_files

def _curl(url):
    r=subprocess.run(["curl","-sS","-m","120",url],capture_output=True,text=True);return json.loads(r.stdout)
def version_of(ds):
    """Versión actual del dataset en Kaggle (se registra al lanzar; no se usa `latest` a ciegas)."""
    owner,slug=ds.split("/");return _curl(f"https://www.kaggle.com/api/v1/datasets/view/{owner}/{slug}").get("currentVersionNumber")
def files_of(ds):
    return {f["name"]:f["bytes"] for f in list_files(ds.split("/")[1])}
def inject_manifest(script,manifest,env=None):
    """Copia del script con EDGELAB_LAUNCH_MANIFEST fijado tras el docstring y los `from __future__` (edgelab_data lo verifica en el primer check_inputs)."""
    import ast,tempfile
    src=Path(script).read_text(encoding="utf-8");tree=ast.parse(src);k=0
    for i,n in enumerate(tree.body):
        if (i==0 and isinstance(n,ast.Expr) and isinstance(getattr(n,"value",None),ast.Constant) and isinstance(n.value.value,str)) or (isinstance(n,ast.ImportFrom) and n.module=="__future__"):k=i+1
        else:break
    lines=src.splitlines(keepends=True);at=tree.body[k].lineno-1 if k<len(tree.body) else len(lines)
    ins="import os as _os\n_os.environ['EDGELAB_LAUNCH_MANIFEST']="+repr(json.dumps(manifest))+"\n"+"".join(f"_os.environ[{k!r}]={v!r}\n" for k,v in (env or {}).items())
    out=Path(tempfile.mkdtemp())/Path(script).name;out.write_text("".join(lines[:at])+ins+"".join(lines[at:]),encoding="utf-8");return str(out)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--slug",required=True);ap.add_argument("--script",required=True);ap.add_argument("--title");ap.add_argument("--need",action="append",default=[],help="INST:DESDE:HASTA")
    ap.add_argument("--extra-dataset",action="append",default=[]);ap.add_argument("--internet",action="store_true");ap.add_argument("--gpu",action="store_true");ap.add_argument("--dry-run",action="store_true");ap.add_argument("--env",action="append",default=[],help="KEY=VALOR inyectado como variable de entorno en el kernel (debe figurar en el pre-registro)");ap.add_argument("--allow-missing",action="store_true",help="lanza igual omitiendo las sesiones sin fuente (decisión explícita; el script debe declararlas)");a=ap.parse_args()
    reqs=[tuple(x.split(":")) for x in a.need];live={};sizes={};used=set();missing={};alt_used={};pins={}
    def files(ds):
        if ds not in live:
            try:fl=list_files(ds);live[ds]={f["name"] for f in fl};sizes[ds]={f["name"]:f["bytes"] for f in fl}
            except Exception:live[ds]=set();sizes[ds]={}
        return live[ds]
    for inst,d0,d1 in reqs:
        for r in ed.sessions(inst,d0,d1).itertuples(index=False):
            if r.file in files(r.dataset):used.add(r.dataset);pins[(r.dataset,r.file)]=sizes[r.dataset][r.file];continue
            alt=next((x for x in (r.alts if isinstance(getattr(r,"alts",None),list) else []) if x.get("consistent") and x["file"] in files(x["dataset"])),None)
            if alt:used.add(alt["dataset"]);pins[(alt["dataset"],alt["file"])]=sizes[alt["dataset"]][alt["file"]];alt_used[(inst,r.dataset)]=alt_used.get((inst,r.dataset),0)+1
            else:missing.setdefault((inst,r.dataset,r.file),[]).append(r.date)
    for (inst,ds),n in alt_used.items():print(f"AVISO {inst}: {n} sesiones saldrán de una alternativa consistente porque `{ds}` no tiene el archivo en Kaggle")
    if missing and a.allow_missing:
        print("SE LANZA SIN ESTAS SESIONES (--allow-missing):")
        for (inst,ds,fl),ds_ in sorted(missing.items()):print(f"  {inst}: {len(ds_)} sesiones de `{ds}` / {fl}: {', '.join(ds_)}")
        missing={}
    if missing:
        print("NO SE LANZA: sesiones aprobadas sin ninguna fuente en Kaggle (el análisis perdería sesiones o fallaría):")
        for (inst,ds,fl),ds_ in sorted(missing.items()):print(f"  {inst}: {len(ds_)} sesiones de `{ds}` / {fl} ({ds_[0]}..{ds_[-1]})")
        print("Subí esos archivos (o corregí el resolver) y volvé a lanzar.");raise SystemExit(2)
    datasets=sorted({"nicolasbuttaro/"+d for d in used}|{"nicolasbuttaro/edgelab-data-catalog"}|set(a.extra_dataset))
    print("datasets a adjuntar:",datasets)
    versions={d:version_of(d) for d in datasets}
    for d in datasets:
        if d.split("/")[1]=="edgelab-data-catalog" or d in a.extra_dataset:
            for n,b in files_of(d).items():pins[(d.split("/")[1],n)]=b      # catálogo y extras: todos sus archivos (pocos)
    manifest=dict(slug=a.slug,script=a.script,versions=versions,files=[dict(dataset=k[0],file=k[1],bytes=v) for k,v in sorted(pins.items())])
    (ROOT/"docs/data_catalog/launches").mkdir(exist_ok=True);(ROOT/"docs/data_catalog/launches"/(a.slug.split("/")[1]+".json")).write_text(json.dumps(manifest,indent=1),encoding="utf-8")
    print(f"manifiesto de lanzamiento: {len(pins)} archivos, versiones {versions}")
    if a.dry_run:return
    script_path=inject_manifest(a.script,manifest,dict(x.split('=',1) for x in a.env))
    cmd=[sys.executable,str(ROOT/"tools/kaggle_kernel.py"),"push","--slug",a.slug,"--title",a.title or a.slug.split("/")[1],"--script",script_path]+(["--gpu"] if a.gpu else [])+(["--internet"] if a.internet else [])
    for d in datasets:cmd+=["--dataset",d]
    out=subprocess.run(cmd,capture_output=True,text=True).stdout;print(out)
    if '"hasError":false' in out or '"error":""' in out:                                     # registro común de lanzamientos de la cuenta (tope diario de prudencia)
        try:
            sys.path.insert(0,str(ROOT));from edgelab.autopilot import account;account.record(a.slug)
        except Exception as e:print("AVISO: no se pudo registrar el lanzamiento en el registro de cuenta:",e)
if __name__=="__main__":main()
