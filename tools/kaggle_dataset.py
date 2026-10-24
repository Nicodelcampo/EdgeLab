#!/usr/bin/env python3
"""Sube una carpeta como NUEVA VERSIÓN de un dataset PRIVADO existente de Kaggle, con la credencial que el entorno ya inyecta para www.kaggle.com.
  python tools/kaggle_dataset.py version --slug nicolasbuttaro/edgelab-discovery-cache --dir /data/cache/discovery --notes "texto"
Una versión reemplaza el conjunto de archivos: se suben todos los de la carpeta (recursivo; Kaggle exige nombres únicos y planos: `ZB/meta.json` queda `ZB__meta.json`). No guarda ni imprime credenciales."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path

def _curl(args:list[str])->str:
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));from kaggle_auth import curl_auth          # misma credencial que el resto de las herramientas
    url=next((x for x in args if str(x).startswith("https://")),"");r=subprocess.run(["curl","-sS","--fail-with-body"]+curl_auth(url)+args,capture_output=True,text=True)
    if r.returncode:raise SystemExit(f"curl falló ({r.returncode}): {r.stdout[:300]} {r.stderr[:300]}")
    return r.stdout

def upload_blob(path:Path,rel:str)->str:
    sz=path.stat().st_size;r=json.loads(_curl(["-X","POST","https://www.kaggle.com/api/v1/blobs/upload","-H","Content-Type: application/json","-d",
        json.dumps({"type":"dataset","name":rel,"contentLength":sz,"lastModifiedEpochSeconds":int(path.stat().st_mtime)})]))
    _curl(["-o",os.devnull,"-X","PUT",r["createUrl"],"-H","Content-Type: application/octet-stream","-T",str(path)]);return r["token"]      # -T transmite desde el disco: --data-binary cargaba el archivo entero en memoria y fallaba con los ticks (3 GB)

def holdout_en(files:list[Path])->list[str]:
    """Parquets con filas desde la apertura del holdout (columna de tiempo en ns). Auditoría 2026-10-24: seis datasets SPOT se
    subieron con corte por fecha UTC y traían 22:00-23:59 del 30-sep. Subir datos del holdout exige el OK de Nico."""
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS as F
    malos=[]
    for p in files:
        if p.suffix!=".parquet":continue
        import pyarrow.parquet as pq
        md=pq.ParquetFile(p).metadata;cols=[md.schema.column(i).name for i in range(md.num_columns)]
        for c in (c for c in cols if c in("time_utc_ns","ts_utc_ns","ts_event_ns","timestamp_ns")):
            j=cols.index(c);mx=[md.row_group(r).column(j).statistics for r in range(md.num_row_groups)]
            if any(st is None or not st.has_min_max or st.max>=F for st in mx):malos.append(f"{p.name}:{c}")
    return malos

def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True);v=sp.add_parser("version");v.add_argument("--slug",required=True);v.add_argument("--dir",required=True);v.add_argument("--notes",default="");v.add_argument("--permitir-holdout",action="store_true");c=sp.add_parser("create");c.add_argument("--slug",required=True);c.add_argument("--dir",required=True);c.add_argument("--title",default="");c.add_argument("--description",default="");c.add_argument("--permitir-holdout",action="store_true")
    a=ap.parse_args();owner,slug=a.slug.split("/");root=Path(a.dir);files=sorted(p for p in root.rglob("*") if p.is_file());toks=[]
    if (m:=holdout_en(files)) and not a.permitir_holdout:raise SystemExit(f"NO SE SUBE: {m} tienen filas del holdout (o sin estadísticas para verificarlo). Recortar con tools/recortar_spot_holdout.py; subir holdout sólo con OK de Nico y --permitir-holdout")
    for p in files:
        rel=str(p.relative_to(root)).replace("/","__");toks.append({"token":upload_blob(p,rel)});print("subido",rel,p.stat().st_size,flush=True)
    import tempfile
    with tempfile.NamedTemporaryFile("w",suffix=".json",delete=False) as tf:json.dump({"versionNotes":getattr(a,"notes",""),"files":toks,"deleteOldVersions":False},tf);body=tf.name      # el cuerpo va por archivo: con cientos de archivos no cabe como argumento
    if a.cmd=="create":
        import tempfile as _t
        with _t.NamedTemporaryFile("w",suffix=".json",delete=False) as tf:json.dump({"ownerSlug":owner,"slug":slug,"title":a.title or slug,"subtitle":a.title or slug,"description":a.description or slug,"licenseName":"CC0-1.0","isPrivate":True,"files":toks,"convertToCsv":False,"categoryIds":[]},tf);cb=tf.name
        out=None
        for k in range(5):
            try:out=json.loads(_curl(["-X","POST","https://www.kaggle.com/api/v1/datasets/create/new","-H","Content-Type: application/json","--data-binary",f"@{cb}"]));break
            except SystemExit as e:print("reintento",k+1,str(e)[:100],flush=True);time.sleep(15*(k+1))
        os.unlink(cb)
        if out is None:raise SystemExit("no se pudo crear el dataset")
        print(json.dumps({k:out.get(k) for k in("status","error","url","ref")}));return
    out=None
    for k in range(4):
        try:out=json.loads(_curl(["-X","POST",f"https://www.kaggle.com/api/v1/datasets/create/version/{owner}/{slug}","-H","Content-Type: application/json","--data-binary",f"@{body}"]));break
        except SystemExit as e:
            print("reintento",k+1,str(e)[:120],flush=True);time.sleep(10*(k+1))
    os.unlink(body)
    if out is None:raise SystemExit("no se pudo crear la versión (los archivos subidos caducan: reintentar el comando completo)")
    print(json.dumps({k:out.get(k) for k in("status","error","url")}))
if __name__=="__main__":main()
