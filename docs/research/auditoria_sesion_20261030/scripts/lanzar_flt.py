"""Lanza en Kaggle (cuenta nicolasbutta) la etapa REP de las reglas con acta sobre DESC+OOS (20250805..20260930), sin holdout."""
import json, os, subprocess, sys
from pathlib import Path
os.environ.update(KAGGLE_AUTH_HEADER_FILE=str(Path.home() / ".kaggle_auth_header"), EDGELAB_KAGGLE_CUENTAS="nicolasbutta,nicolasbuttaro,nicobuttaro",
                  EDGELAB_KAGGLE_API="https://www.kaggle.com/api/v1")
sys.path.insert(0, os.getcwd())
from edgelab.research import embudo_runners as ER
B = "origin/foundation/f0b-compatibility-probe"
ps = [x for x in subprocess.run(["git", "ls-tree", "-r", "--name-only", B, "docs/research"], capture_output=True, text=True).stdout.split()
      if "/embudo/" in x and x.endswith("/estado.json")]
solo = set(sys.argv[1:])
k = ER.KaggleRunner("nicolasbutta", raiz=Path("tmp_bt"))
out = {}
for p in ps:
    d = json.loads(subprocess.run(["git", "show", f"{B}:{p}"], capture_output=True, text=True, encoding="utf-8").stdout)
    if not d.get("acta"): continue
    cid = d["spec"]["cid"]
    if solo and cid not in solo: continue
    spec = dict(d["spec"], cid=f"FLT-{cid}", cuenta_kaggle="nicolasbutta")
    params = dict(cortes=d["acta"]["cortes"], celdas=[d["acta"]["regla"]["celda"]], tope=d["acta"]["regla"].get("tope"))
    try:
        h = k.lanzar(spec, "REP", params, [20250805, 20260930]); out[cid] = h; print(cid, "->", h, flush=True)
    except Exception as e: out[cid] = f"ERROR {e}"[:300]; print(cid, "ERROR", str(e)[:300], flush=True)
Path(r"C:\Users\Gonza-PC\PruebaDeAgente\flt_handles.json").write_text(json.dumps(out, indent=1))
