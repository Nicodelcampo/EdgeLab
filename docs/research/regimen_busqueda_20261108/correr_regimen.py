import json, sys, time, subprocess
sys.path.insert(0, "/home/user/EdgeLab"); sys.path.insert(0, "/home/user/EdgeLab/tools")
from pathlib import Path
from edgelab.research import regimen_offline as RO
ROOT = Path("/home/user/EdgeLab"); CACHE = ROOT / "data/cubos"; OUT = ROOT / "docs/research/regimen_busqueda_20261108"
def _carga(f): return lambda: RO.decodificar(json.loads(f.read_text())["cubo"], f.stem)
fuentes = []
for f in sorted(CACHE.glob("*.json")):
    c = (json.loads(f.read_text()) or {}).get("cubo")
    if c and c.get("n"): fuentes.append((f.stem, _carga(f)))
head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
sucio = bool(subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "edgelab", "tools"], capture_output=True, text=True).stdout.strip())
t0 = time.time(); print("cubos", len(fuentes), flush=True)
r = RO.buscar_streaming(fuentes, k=3, B=100, seed=0, punto_control=ROOT / "data/regimen_pc", log=lambda m: print(time.strftime("%H:%M:%S"), m, flush=True))
r.update(procedencia=dict(head_start=head, codigo_sucio=sucio, segundos=round(time.time() - t0), cubos_lista=[n for n, _ in fuentes]))
(OUT / "RESULTADO_BUSQUEDA.json").write_text(json.dumps(r, indent=1, default=float))
for n, v in r["variantes"].items():
    o = v["observado"]; print(n, o["n_ventanas"], round(o["delta_azar"], 4), round(o["t_azar"], 2), round(o["delta_estatica"], 4), v["p_familia"], flush=True)
print("FIN", round(time.time() - t0), flush=True)
