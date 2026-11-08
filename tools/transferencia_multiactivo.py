#!/usr/bin/env python3
"""TRANSFERENCIA-MULTIACTIVO (pre-registro docs/research/transferencia_multiactivo_20261108/PREREGISTRO.md): reglas congeladas
corridas en activos donde no se eligieron. Reusa KaggleRunner y ANALIZAR_REGLA como tools/holdout_en_r.py.
  python tools/transferencia_multiactivo.py avanzar    # lanza lo pendiente si hay cupo, baja lo terminado y, si está todo, analiza
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/transferencia_multiactivo_20261108"; HF = DIR / "handles.json"
PERIODO = [20250805, 20260930]
ACTIVOS = ["NQ", "ES", "YM", "RTY", "GC", "ZB", "6E", "6B", "6J", "MBT"]
REGLAS = {"PREAPERTURA-ES": ("PREAPERTURA-ES-R", [2, 0, 1, 0, 0, 5]), "PREAPERTURA-NQ": ("PREAPERTURA-NQ-R", [2, 0, 0, 0, 1, 5]),
          "ASIA-NQ": ("ASIA-NQ-R", [1, 1, 0, 2, 3, 3, 3, 2, 2, 8]), "ASIA-GC": ("ASIA-GC-R", [1, 1, 0, 2, 3, 0, 2, 2, 0, 5]),
          "CVGAP-NQ": ("CVGAP-NQ-R", [0, 0, 0, 2, 2, 3, 3, 2, 0, 2, 8])}


def pares():
    from atlas_contexto_r import _todas_las_campanas_r
    camp = dict(_todas_las_campanas_r())
    for regla, (cid, celda) in REGLAS.items():
        st = camp[cid]; origen = st["spec"]["sensor"]
        for a in ACTIVOS:
            if a != origen: yield f"{regla}@{a}", st, celda, a


def avanzar():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); hs = json.loads(HF.read_text()) if HF.exists() else {}; estado = {}
    for i, (clave, st, celda, a) in enumerate(pares()):
        f = DIR / "operaciones" / f"{clave.replace('@', '_')}.json"
        if f.exists(): estado[clave] = "lista"; continue
        if clave in hs:
            e = run.estado(hs[clave]["handle"])
            if e == "complete":
                f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(run.traer(hs[clave]["handle"]), default=float)); estado[clave] = "lista"; continue
            if e in ("running",): estado[clave] = "corriendo"; continue
            if e == "error" and hs[clave].get("intentos", 1) >= 2: estado[clave] = "error"; continue
        sp = {k: v for k, v in st["spec"].items() if k not in ("confirmador",)}
        sp.update(cid=f"TM-{clave.replace('@', '-')}", sensor=a, ejecucion=a, cuenta_kaggle=("nicolasbuttaro", "nicobuttaro")[i % 2])
        try:
            h = run.lanzar(sp, "ANALIZAR_REGLA", dict(cortes=st["cortes"], celdas=[celda], operaciones=True), PERIODO)
            hs[clave] = dict(handle=h, intentos=hs.get(clave, {}).get("intentos", 0) + 1); estado[clave] = "lanzada"
        except Exception as ex:
            estado[clave] = "sin lanzar: " + str(ex)[-80:]
        HF.write_text(json.dumps(hs, indent=1))
    n = {k: sum(1 for v in estado.values() if v.startswith(k)) for k in ("lista", "corriendo", "lanzada", "error", "sin lanzar")}
    print(json.dumps(n))
    if n["lista"] + n["error"] == len(estado): analizar()


def analizar():
    por = {}
    for f in sorted((DIR / "operaciones").glob("*.json")):
        o = json.loads(f.read_text()).get("operaciones") or {}
        por[f.stem] = (np.array(o.get("ses", []), int), np.array(o.get("neto", []), float))
    dias = sorted({int(d) for s, _ in por.values() for d in s}); pos = {d: i for i, d in enumerate(dias)}
    X = np.zeros((len(dias), len(por)))
    for j, (s, r) in enumerate(por.values()):
        for d, v in zip(s, r):
            if np.isfinite(v): X[pos[int(d)], j] += v
    c = X.mean(1); sd = c.std(ddof=1); t = float(c.mean() / (sd / np.sqrt(len(c)))) if sd > 0 else 0.0
    rng = np.random.default_rng(20261108); Z = (rng.choice((-1.0, 1.0), size=(10000, len(c))) * c).mean(1)
    p = float((1 + (Z >= c.mean()).sum()) / 10001)
    pr = {k: dict(n=int(len(s)), r_medio=float(np.nanmean(r)) if len(r) else None, r_total=float(np.nansum(r))) for k, (s, r) in por.items()}
    reglas = {}
    for k, v in pr.items():
        g = k.split("_")[0]; reglas.setdefault(g, []).append(v)
    resumen = {g: dict(activos=len(v), positivos=sum(1 for x in v if (x["r_medio"] or 0) > 0), ops=sum(x["n"] for x in v)) for g, v in reglas.items()}
    out = dict(pares=len(por), sesiones=len(dias), ops=int(sum(x["n"] for x in pr.values())), media_r_sesion=float(c.mean()), t=t, p=p,
               pasa=bool(p < 0.10 and c.mean() > 0), por_regla=resumen, por_par=pr)
    (DIR / "RESULTADO.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("pares", "sesiones", "ops", "media_r_sesion", "t", "p", "pasa")}))


if __name__ == "__main__":
    avanzar() if sys.argv[1:] in ([], ["avanzar"]) else analizar()
