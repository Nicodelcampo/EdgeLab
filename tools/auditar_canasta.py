#!/usr/bin/env python3
"""Experimento 4 (canasta_7_20261030/auditoria_vela_a_vela/PREREGISTRO.md): auditoría vela a vela de las 7 reglas de la canasta
sobre DESC y réplica, con su celda, cortes y tope congelados y el código causal (`grilla_generica.auditar_operaciones`).
Reusa `_cargar` y el esquema de handles de remedir_canasta_causal; éste agrega `auditoria=True` y otra carpeta de salida.
  python tools/auditar_canasta.py lanzar     (idempotente: relanzar completa lo que no entró por cupo de Kaggle)
  python tools/auditar_canasta.py traer
"""
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from remedir_canasta_causal import CANASTA, _cargar  # noqa: E402

SALIDA = ROOT / "docs/research/canasta_7_20261030/auditoria_vela_a_vela"


def lanzar():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); cs = run.cuentas(); hf = SALIDA / "handles.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}
    for cid in CANASTA:
        st, acta = _cargar(cid); sp = st["spec"]; r = acta["regla"]
        for tramo, per in (("desc", sp["desc"]), ("oos", sp["oos"])):
            clave = f"{cid}/{tramo}"
            if clave in hs: continue
            spec = dict(sp, cid=f"{cid}-AUD-{tramo}", cuenta_kaggle=cs[len(hs) % len(cs)])
            params = dict(cortes=acta.get("cortes") or st.get("cortes"), celdas=[r["celda"]], tope=r.get("tope"), auditoria=True)
            try: h = run.lanzar(spec, "ANALIZAR_REGLA", params, [int(per[0]), int(per[1])])
            except Exception as ex: print("no se lanzó", clave, str(ex)[-160:]); continue
            hs[clave] = dict(handle=h, periodo=per, ts=time.time()); hf.write_text(json.dumps(hs, indent=1)); print("lanzada", clave, h, flush=True)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); hs = json.loads((SALIDA / "handles.json").read_text()); filas = []
    for clave, h in hs.items():
        out = SALIDA / (clave.replace("/", "__") + ".json")
        if not out.exists():
            e = run.estado(h["handle"]); print(clave, e)
            if e != "complete": continue
            out.write_text(json.dumps(run.traer(h["handle"]), indent=1, default=float))
        a = json.loads(out.read_text()).get("auditoria") or {}
        filas.append(dict(regla=clave, **{k: v for k, v in a.items() if k != "detalle"}))
    (SALIDA / "RESUMEN.json").write_text(json.dumps(filas, indent=1)); [print(f) for f in filas]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer")); a = ap.parse_args()
    {"lanzar": lanzar, "traer": traer}[a.cmd]()
