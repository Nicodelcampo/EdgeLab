#!/usr/bin/env python3
"""Desarrollo en R (Nico 2026-11-02): las 16 reglas del holdout (12 nominadas + U1-CRUZADO + 3 forzadas) re-corridas sobre DESC y réplica
con el riesgo inicial por operación. Compara media en puntos contra media en R (neto/riesgo) y marca discrepancias de signo. Reusa
_cargar (remedir_canasta_causal), REGLAS (holdout_individual) y resumen_sesiones (escalera); nunca toca el holdout.
  python tools/desarrollo_en_r.py lanzar | traer
"""
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from remedir_canasta_causal import _cargar  # noqa: E402
from holdout_individual import REGLAS  # noqa: E402

SAL = ROOT / "docs/research/canasta_7_20261030/desarrollo_en_r"


def periodos(cid):
    if cid == "U1-CRUZADO": return {"desc": [20250805, 20260331], "rep": [20260401, 20260930]}
    st, _ = _cargar(cid); sp = st["spec"]
    rep = (st.get("pistas_replica") or {}).get("ventana") if cid.endswith("-C") else sp["oos"]
    return {"desc": sp["desc"], "rep": rep}


def lanzar():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); cs = run.cuentas(); SAL.mkdir(parents=True, exist_ok=True); hf = SAL / "handles.json"
    hs = json.loads(hf.read_text()) if hf.exists() else {}
    for cid in REGLAS + ["U1-CRUZADO"]:
        for t, per in periodos(cid).items():
            k = f"{cid}/{t}"
            if k in hs: continue
            try:
                if cid == "U1-CRUZADO":
                    sp = dict(cid=f"U1-CRUZADO-DR-{t}", experimento="edgelab.research.u1_cruzado_papel", sensor="DK:USATECHIDXUSD", ejecucion="NQ",
                              cuenta_kaggle=cs[len(hs) % len(cs)])
                    h = run.lanzar(sp, "OPERAR", {}, [int(per[0]), int(per[1])])
                else:
                    st, acta = _cargar(cid); r = acta["regla"]
                    h = run.lanzar(dict(st["spec"], cid=f"{cid}-DR-{t}", cuenta_kaggle=cs[len(hs) % len(cs)]), "ANALIZAR_REGLA",
                                   dict(cortes=acta.get("cortes") or st.get("cortes"), celdas=[r["celda"]], tope=r.get("tope"), operaciones=True),
                                   [int(per[0]), int(per[1])])
            except Exception as ex: print("no se lanzó", k, str(ex)[-200:]); continue
            hs[k] = h; hf.write_text(json.dumps(hs, indent=1)); print("lanzada", k, h, flush=True)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    from edgelab.funnel.escalera import resumen_sesiones
    run = KaggleRunner(raiz=None); hs = json.loads((SAL / "handles.json").read_text()); filas = []; pend = 0
    for k, h in hs.items():
        f = SAL / (k.replace("/", "__") + ".json")
        if not f.exists():
            e = run.estado(h)
            if e != "complete": print(k, e); pend += 1; continue
            f.write_text(json.dumps(run.traer(h), indent=1, default=float))
    for cid in REGLAS + ["U1-CRUZADO"]:
        fila = dict(regla=cid)
        for t in ("desc", "rep"):
            f = SAL / f"{cid}__{t}.json"
            if not f.exists(): continue
            o = json.loads(f.read_text()).get("operaciones") or {}
            x = np.array(o.get("neto", []), float); rg = np.array([np.nan if v is None else v for v in o.get("riesgo", [])], float); s = np.array(o.get("ses", []), int)
            if not len(x): continue
            R = x / rg; ok = np.isfinite(R)
            rs = resumen_sesiones(R[ok], s[ok], n_boot=4000) if ok.sum() >= 5 else {}
            fila[t] = dict(n=int(len(x)), media_pts=float(x.mean()), media_R=float(np.nanmean(R)), ic90_R=rs.get("ic"), p_R=rs.get("p_unilateral"),
                           riesgo_medio=float(np.nanmean(rg)), corr_riesgo_resultado=float(np.corrcoef(rg[ok], x[ok])[0, 1]) if ok.sum() > 2 else None,
                           signo_distinto=bool(np.sign(x.mean()) != np.sign(np.nanmean(R))))
        filas.append(fila)
    (SAL / "RESULTADO.json").write_text(json.dumps(dict(pendientes=pend, reglas=filas), indent=1, default=float)); return pend, filas


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer")); a = ap.parse_args()
    if a.cmd == "lanzar": lanzar()
    else:
        p, F = traer(); print("pendientes", p)
        for f in F: print(f)
