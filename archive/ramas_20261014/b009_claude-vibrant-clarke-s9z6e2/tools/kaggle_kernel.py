#!/usr/bin/env python3
"""Lanza y consulta kernels PRIVADOS de Kaggle (con GPU opcional) por la API de www.kaggle.com, usando la credencial que el entorno inyecta
para ese host (no hay tokens en este archivo). Verificado el 2026-10-04: push (HTTP 200), status y output funcionan con esa credencial.

  python tools/kaggle_kernel.py push  --slug dueño/slug --title "titulo" --script archivo.py [--gpu] [--internet] [--dataset dueño/dataset ...]
  python tools/kaggle_kernel.py status --slug dueño/slug
  python tools/kaggle_kernel.py output --slug dueño/slug --file discovery_parity.json --out local.json
Solo datos que ya estén en datasets privados de Kaggle; respetar siempre la custodia (nada desde 2026-10-01)."""
import argparse,json,subprocess,sys
API="https://www.kaggle.com/api/v1"
def curl(args,body=None):
    cmd=["curl","-sS","-m","120"]+args
    if body is not None:cmd+=["-H","Content-Type: application/json","--data-binary","@-"]
    r=subprocess.run(cmd,input=body,capture_output=True,text=True);return r.stdout
def main():
    ap=argparse.ArgumentParser();ap.add_argument("cmd",choices=["push","status","output"]);ap.add_argument("--slug",required=True);ap.add_argument("--title");ap.add_argument("--script");ap.add_argument("--gpu",action="store_true")
    ap.add_argument("--internet",action="store_true");ap.add_argument("--dataset",action="append",default=[]);ap.add_argument("--file");ap.add_argument("--out");a=ap.parse_args()
    owner,slug=a.slug.split("/")
    if a.cmd=="push":
        body=json.dumps({"slug":a.slug,"newTitle":a.title or slug,"text":open(a.script).read(),"language":"python","kernelType":"script","isPrivate":True,"enableGpu":a.gpu,"enableInternet":a.internet,
                         "datasetDataSources":a.dataset,"competitionDataSources":[],"kernelDataSources":[],"modelDataSources":[],"categoryIds":[]})
        print(curl([f"{API}/kernels/push"],body))
    elif a.cmd=="status":print(curl([f"{API}/kernels/status?userName={owner}&kernelSlug={slug}"]))
    else:
        d=json.loads(curl([f"{API}/kernels/output?userName={owner}&kernelSlug={slug}"]));fs={f["fileName"]:f["url"] for f in d.get("files",[])}
        if not a.file:print(json.dumps(sorted(fs),indent=1));return
        subprocess.run(["curl","-sS","-m","120","-o",a.out or a.file,fs[a.file]],check=True);print("guardado",a.out or a.file)
if __name__=="__main__":main()
