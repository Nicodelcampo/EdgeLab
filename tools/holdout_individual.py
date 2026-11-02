#!/usr/bin/env python3
"""Evaluación de las aperturas INDIVIDUALES del holdout (canasta_7_20261030/ACTA_APERTURAS_INDIVIDUALES_20261102.md): cada nominada
según su ACTA_HOLDOUT.json (primeras n_fijo operaciones, paso reservado de LORD++). Con n < n_fijo queda EN CURSO: se informan n,
media e IC90 por sesiones (interinos), con todas las sesiones y sólo con las válidas (SELLADO_CONTEO.json). Reusa _cargar
(remedir_canasta_causal) y resumen_sesiones (escalera); no resuelve LORD antes de n_fijo.
  python tools/holdout_individual.py
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from remedir_canasta_causal import _cargar  # noqa: E402
from edgelab.funnel.escalera import resumen_sesiones  # noqa: E402

C = ROOT / "docs/research/canasta_7_20261030"; H = C / "holdout_v3"
REGLAS = ["CVGAP-NQ", "CVGAP-CFD-NQ", "U1-ZONAS-AVCL-NQ", "U1-RACIMOS-GRILLA-NQ", "U1-ZONAS-NQ", "U1-ORO-GRILLA", "U1-YM-GRILLA",
          "U1-ES-GRILLA", "U1-RACIMOS-GRILLA-ES", "U1-ZONAS-BT2-ES", "U1-ZONAS-BT2-NQ", "U1-ZONAS-ES"]


def fuente(x):
    return x[3:] if x.startswith("DK:") else x


def validas(instrumentos):
    cnt = json.loads((C / "SELLADO_CONTEO.json").read_text()); por = {}
    for k, v in cnt.items():
        b = k.split("_")[0]
        for s, n in v.items(): por.setdefault(b, {}); por[b][int(s)] = por[b].get(int(s), 0) + n
    ok = None
    for i in instrumentos:
        v = {s: n for s, n in por.get(i, {}).items() if 20261001 <= s <= 20261030}; med = np.median(list(v.values()))
        b = {s for s, n in v.items() if n >= 0.5 * med}; ok = b if ok is None else ok & b
    return ok or set()


def evaluar(cid):
    st, acta = _cargar(cid); sp = st["spec"]; f = H / f"{cid}.json"
    if not f.exists(): return dict(regla=cid, estado="SIN_CORRIDA")
    o = json.loads(f.read_text()).get("operaciones") or {}; ses = np.array(o.get("ses", []), int); x = np.array(o.get("neto", []), float)
    val = validas({fuente(sp["sensor"]), fuente(sp.get("ejecucion") or sp["sensor"])})
    def res(m):
        if m.sum() < 2: return dict(n=int(m.sum()), media=float(x[m].mean()) if m.any() else None)
        r = resumen_sesiones(x[m], ses[m], n_boot=4000); return dict(n=int(m.sum()), media=float(x[m].mean()), ic90=r["ic"], sesiones=r["n_sesiones"])
    nf = int(acta.get("n_fijo", 150)); todo = res(np.ones(len(x), bool)); solo = res(np.isin(ses, list(val)))
    return dict(regla=cid, n_fijo=nf, alfa=acta.get("alfa"), estado="EN_CURSO" if len(x) < nf else "DECIDIR", todas=todo, solo_validas=solo,
                ops_en_sesiones_invalidas=int((~np.isin(ses, list(val))).sum()))


if __name__ == "__main__":
    out = [evaluar(c) for c in REGLAS]
    (H / "INDIVIDUAL.json").write_text(json.dumps(out, indent=1, default=float)); [print(r) for r in out]
