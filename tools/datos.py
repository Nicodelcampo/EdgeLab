#!/usr/bin/env python3
"""Acceso estándar a los datos de research fuera de Kaggle: un nombre, una ruta canónica local, verificación contra el origen.

Antes (hasta el 2026-11-18) el M1 de NT8 se bajaba a mano a una carpeta temporal y cada herramienta recibía esa ruta como argumento:
nadie podía reproducir una corrida sin saber de dónde salió la carpeta, y un archivo viejo o incompleto pasaba igual. Ahora:

  python tools/datos.py estado                   # qué hay local, contra el origen (tamaño y fecha de cada archivo)
  python tools/datos.py traer M1NT8              # baja lo que falta o cambió a data/m1nt8/ (gitignorado) y escribe PROCEDENCIA.json
  python tools/datos.py importar M1NT8 <carpeta> # usa una copia ya bajada, sólo si coincide archivo por archivo con el origen
  python tools/datos.py ruta M1NT8               # imprime la ruta verificada (falla si falta algo)

En código: `from tools.datos import ruta; ruta("M1NT8")`. Las herramientas que leen M1 local la usan por defecto.
El dataset M1NT8 contiene datos del holdout terminal: se lee SIEMPRE con `fuentes_ticks.bloques_m1nt8`, que corta en la frontera.
"""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get("EDGELAB_DATOS") or ROOT / "data")
API = "https://www.kaggle.com/api/v1"
DATASETS = {
    "M1NT8": dict(dataset="nicolasbuttaro/edgelab-nt8-m1-futuros", carpeta="m1nt8",
                  nota="M1 real de futuros de NT8 desde 2006/2008 (NQ, ES, YM, GC, EMD, RTY). Lector: fuentes_ticks.bloques_m1nt8"),
}


def _api(path):
    r = subprocess.run(["curl", "-sS", "-m", "60", f"{API}/{path}"], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def origen(nombre) -> dict:
    """{archivo: (bytes, fecha de creación)} según la API de Kaggle."""
    d = DATASETS[nombre]["dataset"]
    return {f["name"]: (int(f["totalBytes"]), f.get("creationDate", "")) for f in _api(f"datasets/list/{d}")["datasetFiles"]}


def _dir(nombre) -> Path:
    return BASE / DATASETS[nombre]["carpeta"]


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def diferencias(nombre, org=None) -> list:
    """Archivos que faltan o no coinciden en tamaño con el origen (vacía = copia local completa)."""
    org = org or origen(nombre); d = _dir(nombre)
    return [a for a, (n, _) in org.items() if not (d / a).exists() or (d / a).stat().st_size != n]


def _procedencia(nombre, org):
    d = _dir(nombre)
    (d / "PROCEDENCIA.json").write_text(json.dumps(dict(
        dataset=DATASETS[nombre]["dataset"], archivos={a: dict(bytes=n, creado=c, sha256=_sha(d / a)) for a, (n, c) in org.items()}),
        indent=1), encoding="utf-8")


def traer(nombre):
    org = origen(nombre); d = _dir(nombre); d.mkdir(parents=True, exist_ok=True)
    for a in diferencias(nombre, org):
        print("bajando", a, flush=True)
        subprocess.run(["curl", "-sS", "-L", "-m", "1800", "-o", str(d / a), f"{API}/datasets/download/{DATASETS[nombre]['dataset']}/{a}"], check=True)
    if (falta := diferencias(nombre, org)): raise SystemExit(f"{nombre}: siguen sin coincidir {falta}")
    _procedencia(nombre, org); print(d)


def importar(nombre, carpeta):
    org = origen(nombre); src = Path(carpeta); d = _dir(nombre); d.mkdir(parents=True, exist_ok=True)
    malos = [a for a, (n, _) in org.items() if not (src / a).exists() or (src / a).stat().st_size != n]
    if malos: raise SystemExit(f"{carpeta} no coincide con el origen en {malos}: usar `traer`")
    for a in org:
        if not (d / a).exists() or (d / a).stat().st_size != org[a][0]: shutil.copy2(src / a, d / a)
    _procedencia(nombre, org); print(d)


def ruta(nombre, verificar_origen=False) -> str:
    """Ruta local verificada. Sin red: exige PROCEDENCIA.json y que cada archivo tenga el tamaño registrado. Con `verificar_origen`,
    además contra la API (una copia vieja frente a un dataset actualizado falla)."""
    d = _dir(nombre); pj = d / "PROCEDENCIA.json"
    if not pj.exists(): raise SystemExit(f"{nombre}: no hay copia local verificada en {d} — python tools/datos.py traer {nombre}")
    reg = json.loads(pj.read_text(encoding="utf-8"))["archivos"]
    malos = [a for a, v in reg.items() if not (d / a).exists() or (d / a).stat().st_size != v["bytes"]]
    if malos: raise SystemExit(f"{nombre}: copia local alterada {malos} — python tools/datos.py traer {nombre}")
    if verificar_origen and (dif := diferencias(nombre)): raise SystemExit(f"{nombre}: el origen cambió {dif} — python tools/datos.py traer {nombre}")
    return str(d)


def estado():
    for nombre, cfg in DATASETS.items():
        try: org = origen(nombre); dif = diferencias(nombre, org)
        except Exception as e: org, dif = {}, [f"sin acceso al origen: {str(e)[:80]}"]
        print(f"{nombre}: {_dir(nombre)} — {'COMPLETA' if not dif else 'FALTA/DIFIERE ' + str(dif)} ({len(org)} archivos en el origen). {cfg['nota']}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "estado": estado()
    elif a[0] == "traer": traer(a[1])
    elif a[0] == "importar": importar(a[1], a[2])
    elif a[0] == "ruta": print(ruta(a[1], verificar_origen=True))
    else: raise SystemExit(__doc__)
