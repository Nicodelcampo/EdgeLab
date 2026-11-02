#!/usr/bin/env python3
"""Holdout de la canasta v3 (ACTA_APERTURA_V3_20261102.md). Cada regla con su celda, cortes y tope congelados, sobre el dataset
sellado, más la prueba principal de la revisión a 20 sesiones. Reusa `_cargar` de remedir_canasta_causal (mismos estados y actas).
  python tools/canasta_v3_holdout.py lanzar
  python tools/canasta_v3_holdout.py traer
"""
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from remedir_canasta_causal import _cargar  # noqa: E402

SALIDA = ROOT / "docs/research/canasta_7_20261030/holdout_v3"
ACTA = "docs/research/canasta_7_20261030/ACTA_APERTURA_V3_20261102.md"
ACTA_INDIVIDUAL = "docs/research/canasta_7_20261030/ACTA_APERTURAS_INDIVIDUALES_20261102.md"
S = {"CVGAP-NQ": 78.0207, "U1-RACIMOS-GRILLA-NQ": 33.9181, "CVGAP-CFD-NQ": 48.7089, "U1-ZONAS-AVCL-NQ": 17.2718, "U1-ZONAS-NQ": 74.4533}
S4 = dict(S, **{"U1-ZONAS-BT2-NQ": 38.50, "U1-ZONAS-BT2-ES": 6.00})   # v4: desvío de las operaciones causales DESC+réplica
RESTO = ["U1-ORO-GRILLA", "U1-YM-GRILLA", "U1-ES-GRILLA", "U1-RACIMOS-GRILLA-ES", "U1-ZONAS-BT2-ES", "U1-ZONAS-BT2-NQ", "U1-ZONAS-ES"]
PERIODO = [20261001, 20261030]; UMBRAL = {20: 2.39, 40: 1.69, 60: 1.38}


def lanzar(commit, reglas=None, acta=ACTA):
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado", raiz=None)
    SALIDA.mkdir(parents=True, exist_ok=True); hf = SALIDA / "handles.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}
    for cid in (reglas or S):
        if cid in hs: continue
        st, acta = _cargar(cid); sp = dict(st["spec"], cid=f"{cid}-V3H"); r = acta["regla"]
        params = dict(cortes=acta.get("cortes") or st.get("cortes"), celdas=[r["celda"]], tope=r.get("tope"), operaciones=True,
                      acta=dict(tipo="holdout", acta=acta, commit=commit, cid=cid))
        try: h = run.lanzar(sp, "ANALIZAR_REGLA", params, PERIODO)
        except Exception as ex: print("no se lanzó", cid, str(ex)[-300:]); continue
        hs[cid] = dict(handle=h); hf.write_text(json.dumps(hs, indent=1)); print("lanzada", cid, h, flush=True)


def serie(ops: dict, sesiones: list) -> np.ndarray:
    """ops: {cid: (ses, neto)}. Suma por sesión de neto/S; sesión sin operaciones = 0."""
    x = dict.fromkeys(sesiones, 0.0)
    for cid, (ses, neto) in ops.items():
        for s, v in zip(ses, neto):
            if s in x: x[s] += v / S[cid]
    return np.array([x[s] for s in sesiones])


def tstat(x):
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 1 and x.std(ddof=1) > 0 else float("nan")


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado", raiz=None)
    hs = json.loads((SALIDA / "handles.json").read_text()); ops, por_regla = {}, {}
    for cid, h in hs.items():
        out = SALIDA / f"{cid}.json"
        if not out.exists():
            e = run.estado(h["handle"]); print(cid, e)
            if e != "complete": return
            out.write_text(json.dumps(run.traer(h["handle"]), indent=1, default=float))
        r = json.loads(out.read_text()); o = r.get("operaciones") or ((r.get("reportes") or [{}])[0].get("operaciones")) or {}
        ses, neto = [int(s) for s in o.get("ses", [])], [float(v) for v in o.get("neto", [])]
        ops[cid] = (ses, neto)
        por_regla[cid] = dict(n=len(neto), media=float(np.mean(neto)) if neto else None)
    import pandas as pd
    ses = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range("2026-10-01", "2026-10-30")]   # días hábiles CME de octubre (sin feriados)
    out = dict(por_regla=por_regla, sesiones=len(ses))
    for n in (20, 40, 60):
        if len(ses) < n: break
        x = serie(ops, ses[:n]); out[f"rev_{n}"] = dict(t=tstat(x), umbral=UMBRAL[n], aprueba=bool(tstat(x) >= UMBRAL[n]), media=float(x.mean()))
    solo = serie(ops, sorted({s for v in ops.values() for s in v[0]})); out["informativo_solo_con_ops"] = dict(n=len(solo), t=tstat(solo))
    (SALIDA / "RESULTADO.json").write_text(json.dumps(out, indent=1, default=float)); return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer")); ap.add_argument("--commit", default=""); ap.add_argument("--resto", action="store_true")
    a = ap.parse_args()
    if a.cmd == "lanzar": lanzar(a.commit, RESTO if a.resto else None, ACTA_INDIVIDUAL if a.resto else ACTA)
    else: print(traer())
