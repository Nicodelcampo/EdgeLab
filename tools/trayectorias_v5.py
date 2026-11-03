#!/usr/bin/env python3
"""Trayectorias en R por operación (etapa TRAYECTORIAS) de las 8 reglas de la canasta v5, en DESC y réplica (nunca el holdout).
Insumo del programa de mejora de R (docs/research/programa_r_20261103/): políticas de salida y filtros se evalúan offline sobre
estos caminos. Reusa `periodos` (desarrollo_en_r) y `_cargar` (remedir_canasta_causal).
  python tools/trayectorias_v5.py lanzar | traer
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from remedir_canasta_causal import _cargar  # noqa: E402
from desarrollo_en_r import periodos  # noqa: E402

V5 = ["U1-ZONAS-BT2-ES", "CVGAP-ES-C", "U1-ZONAS-AVCL-ES-C", "U1-ZONAS-BT2-NQ", "U1-RACIMOS-GRILLA-NQ", "CVGAP-CFD-NQ", "CVGAP-CFD-ES-C",
      "U1-ZONAS-AVCL-NQ"]
SAL = ROOT / "docs/research/programa_r_20261103/trayectorias"


def lanzar():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); cs = run.cuentas(); SAL.mkdir(parents=True, exist_ok=True); hf = SAL / "handles.json"
    hs = json.loads(hf.read_text()) if hf.exists() else {}
    for cid in V5:
        st, acta = _cargar(cid); r = acta["regla"]
        for t, per in periodos(cid).items():
            k = f"{cid}/{t}"
            if k in hs: continue
            try: h = run.lanzar(dict(st["spec"], cid=f"{cid}-TR-{t}", cuenta_kaggle=cs[len(hs) % len(cs)]), "TRAYECTORIAS",
                                dict(cortes=acta.get("cortes") or st.get("cortes"), celdas=[r["celda"]], tope=r.get("tope"), k=240), [int(per[0]), int(per[1])])
            except Exception as ex: print("no se lanzó", k, str(ex)[-160:], flush=True); continue
            hs[k] = h; hf.write_text(json.dumps(hs, indent=1)); print("lanzada", k, h, flush=True)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); hs = json.loads((SAL / "handles.json").read_text()); pend = 0
    for k, h in hs.items():
        f = SAL / (k.replace("/", "__") + ".json")
        if f.exists(): continue
        e = run.estado(h)
        if e != "complete": pend += 1; print(k, e); continue
        f.write_text(json.dumps(run.traer(h), default=float))
    print("pendientes", pend); return pend


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer")); a = ap.parse_args()
    {"lanzar": lanzar, "traer": traer}[a.cmd]()
