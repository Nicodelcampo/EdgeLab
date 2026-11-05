#!/usr/bin/env python3
"""Re-medición CAUSAL de las 7 reglas de la canasta del holdout (2026-11-02, Nico: «asegurate de que todas las estrategias sean
exactamente como se correrían en tiempo real, y dejá preparadas las candidatas para el holdout»).

Cada regla congelada (celda, cortes y tope de su ACTA_HOLDOUT.json) se corre otra vez con el código actual, que pasó el candado de
causalidad, sobre su DESC y su réplica (nunca el holdout), con la misma etapa que la eligió (ANALIZAR_REGLA). Se compara con lo
que el acta registró. Motivo: `areas_expansion.disparos` (familia U1) miraba el futuro, y CVGAP tenía dos problemas de borde
(HALLAZGO_LOOKAHEAD_DISPAROS_U1_20261102.md).

  python tools/remedir_canasta_causal.py lanzar
  python tools/remedir_canasta_causal.py traer
"""
import argparse
import glob
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
SALIDA = ROOT / "docs/research/canasta_7_20261030/remedicion_causal_20261102"
CANASTA = ["CVGAP-NQ", "CVGAP-CFD-NQ", "U1-ZONAS-AVCL-NQ", "U1-ORO-GRILLA", "U1-RACIMOS-GRILLA-NQ", "U1-YM-GRILLA", "U1-ZONAS-NQ"]
EXCLUIDAS = ["U1-ES-GRILLA", "U1-RACIMOS-GRILLA-ES", "U1-ZONAS-BT2-ES", "U1-ZONAS-BT2-NQ", "U1-ZONAS-ES"]   # nominadas al holdout, fuera de la canasta


def _cargar(cid):
    d = Path(sorted(glob.glob(str(ROOT / f"docs/research/*/embudo/{cid}/estado.json")))[0]).parent
    return json.loads((d / "estado.json").read_text(encoding="utf-8")), json.loads((d / "ACTA_HOLDOUT.json").read_text(encoding="utf-8"))


def lanzar(reglas=None):
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); cs = run.cuentas(); SALIDA.mkdir(parents=True, exist_ok=True); hf = SALIDA / "handles.json"
    hs = json.loads(hf.read_text()) if hf.exists() else {}
    for i, cid in enumerate(reglas or CANASTA):
        st, acta = _cargar(cid); sp = st["spec"]; r = acta["regla"]
        for tramo, per in (("desc", sp["desc"]), ("oos", sp["oos"])):
            clave = f"{cid}/{tramo}"
            if clave in hs: continue
            spec = dict(sp, cid=f"{cid}-CAUSAL-{tramo}", cuenta_kaggle=cs[(len(hs) + i) % len(cs)])
            params = dict(cortes=acta.get("cortes") or st.get("cortes"), celdas=[r["celda"]], tope=r.get("tope"), operaciones=True)
            try: h = run.lanzar(spec, "ANALIZAR_REGLA", params, [int(per[0]), int(per[1])])
            except Exception as ex: print("no se lanzó", clave, str(ex)[-200:]); continue
            hs[clave] = dict(handle=h, periodo=per, celda=r["celda"], tope=r.get("tope"), ts=time.time())
            hf.write_text(json.dumps(hs, indent=1)); print("lanzada", clave, h)


def _previo(st, acta, tramo):
    """Lo que el estado registró para la celda congelada: réplica OOS (`oos.replica`) o candidatas del DESC (`desc`)."""
    celda = list(acta["regla"]["celda"]); fuente = (st.get("oos") or {}).get("replica", []) if tramo == "oos" else \
        (st.get("desc") or {}).get("candidatas_detalle", []) or (st.get("desc") or {}).get("E2", [])
    for x in fuente if isinstance(fuente, list) else []:
        if list(x.get("celda", [])) == celda: return dict(n=x.get("n"), media=x.get("media_neta"), ic90=x.get("ic90"))
    return None


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); hs = json.loads((SALIDA / "handles.json").read_text()); filas = []
    for clave, h in hs.items():
        out = SALIDA / (clave.replace("/", "__") + ".json")
        if not out.exists():
            e = run.estado(h["handle"]); print(clave, e)
            if e != "complete": continue
            out.write_text(json.dumps(run.traer(h["handle"]), indent=1, default=float))
        r = json.loads(out.read_text()); rep = (r.get("reportes") or [{}])[0]; cid, tramo = clave.split("/")
        st, acta = _cargar(cid)
        filas.append(dict(regla=cid, tramo=tramo, n=rep.get("n"), media=rep.get("media"), ic90=rep.get("ic90_sesiones"),
                          p=rep.get("p_sesiones"), previo=_previo(st, acta, tramo)))
    (SALIDA / "RESUMEN.json").write_text(json.dumps(filas, indent=1, default=float))
    for f in filas: print(f)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer")); ap.add_argument("--excluidas", action="store_true"); a = ap.parse_args()
    lanzar(EXCLUIDAS if a.excluidas else None) if a.cmd == "lanzar" else traer()
