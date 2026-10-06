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

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--slug",required=True);ap.add_argument("--script",required=True);ap.add_argument("--title");ap.add_argument("--need",action="append",default=[],help="INST:DESDE:HASTA")
    ap.add_argument("--extra-dataset",action="append",default=[]);ap.add_argument("--internet",action="store_true");ap.add_argument("--gpu",action="store_true");ap.add_argument("--dry-run",action="store_true");ap.add_argument("--allow-missing",action="store_true",help="lanza igual omitiendo las sesiones sin fuente (decisión explícita; el script debe declararlas)");a=ap.parse_args()
    reqs=[tuple(x.split(":")) for x in a.need];live={};used=set();missing={};alt_used={}
    def files(ds):
        if ds not in live:
            try:live[ds]={f["name"] for f in list_files(ds)}
            except Exception:live[ds]=set()
        return live[ds]
    for inst,d0,d1 in reqs:
        for r in ed.sessions(inst,d0,d1).itertuples(index=False):
            if r.file in files(r.dataset):used.add(r.dataset);continue
            alt=next((x for x in (r.alts if isinstance(getattr(r,"alts",None),list) else []) if x.get("consistent") and x["file"] in files(x["dataset"])),None)
            if alt:used.add(alt["dataset"]);alt_used[(inst,r.dataset)]=alt_used.get((inst,r.dataset),0)+1
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
    if a.dry_run:return
    cmd=[sys.executable,str(ROOT/"tools/kaggle_kernel.py"),"push","--slug",a.slug,"--title",a.title or a.slug.split("/")[1],"--script",a.script]+(["--gpu"] if a.gpu else [])+(["--internet"] if a.internet else [])
    for d in datasets:cmd+=["--dataset",d]
    print(subprocess.run(cmd,capture_output=True,text=True).stdout)
if __name__=="__main__":main()
