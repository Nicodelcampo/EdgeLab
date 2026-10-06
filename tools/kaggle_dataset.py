#!/usr/bin/env python3
"""Sube una carpeta como NUEVA VERSIÓN de un dataset PRIVADO existente de Kaggle, con la credencial que el entorno ya inyecta para www.kaggle.com.
  python tools/kaggle_dataset.py version --slug nicolasbuttaro/edgelab-discovery-cache --dir /data/cache/discovery --notes "texto"
Una versión reemplaza el conjunto de archivos: se suben todos los de la carpeta (recursivo; Kaggle exige nombres únicos y planos: `ZB/meta.json` queda `ZB__meta.json`). No guarda ni imprime credenciales."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path

def _curl(args:list[str])->str:
    r=subprocess.run(["curl","-sS","--fail-with-body"]+args,capture_output=True,text=True)
    if r.returncode:raise SystemExit(f"curl falló ({r.returncode}): {r.stdout[:300]} {r.stderr[:300]}")
    return r.stdout

def upload_blob(path:Path,rel:str)->str:
    sz=path.stat().st_size;r=json.loads(_curl(["-X","POST","https://www.kaggle.com/api/v1/blobs/upload","-H","Content-Type: application/json","-d",
        json.dumps({"type":"dataset","name":rel,"contentLength":sz,"lastModifiedEpochSeconds":int(path.stat().st_mtime)})]))
    _curl(["-o","/dev/null","-X","PUT",r["createUrl"],"-H","Content-Type: application/octet-stream","--data-binary",f"@{path}"]);return r["token"]

def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True);v=sp.add_parser("version");v.add_argument("--slug",required=True);v.add_argument("--dir",required=True);v.add_argument("--notes",default="")
    a=ap.parse_args();owner,slug=a.slug.split("/");root=Path(a.dir);files=sorted(p for p in root.rglob("*") if p.is_file());toks=[]
    for p in files:
        rel=str(p.relative_to(root)).replace("/","__");toks.append({"token":upload_blob(p,rel)});print("subido",rel,p.stat().st_size,flush=True)
    import tempfile
    with tempfile.NamedTemporaryFile("w",suffix=".json",delete=False) as tf:json.dump({"versionNotes":a.notes,"files":toks,"deleteOldVersions":False},tf);body=tf.name      # el cuerpo va por archivo: con cientos de archivos no cabe como argumento
    out=None
    for k in range(4):
        try:out=json.loads(_curl(["-X","POST",f"https://www.kaggle.com/api/v1/datasets/create/version/{owner}/{slug}","-H","Content-Type: application/json","--data-binary",f"@{body}"]));break
        except SystemExit as e:
            print("reintento",k+1,str(e)[:120],flush=True);time.sleep(10*(k+1))
    os.unlink(body)
    if out is None:raise SystemExit("no se pudo crear la versión (los archivos subidos caducan: reintentar el comando completo)")
    print(json.dumps({k:out.get(k) for k in("status","error","url")}))
if __name__=="__main__":main()
