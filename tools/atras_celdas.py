#!/usr/bin/env python3
"""ATRAS (2026-10-26): celdas positivas sin señal de las campañas con señal en CFD, sobre la historia NUNCA mirada antes de su DESC.

Pre-registro: docs/research/atras_20261026/PREREGISTRO_ATRAS.md. Reutiliza `analizar_embudo.celdas_de` y la etapa ANALIZAR_REGLA; la
ejecución pasa al CFD de la señal (proxy declarado: no hay ticks del futuro de esa época) con los costos del futuro de referencia.
  python tools/atras_celdas.py lanzar | traer
"""
import argparse
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from analizar_embudo import celdas_de  # noqa: E402

SALIDA = ROOT / "docs/research/atras_20261026"
CAMPANAS = {"EXPZ-CFD": [20230103, 20250804], "ZGAP-CFD": [20230103, 20250804]}


def plan():
    out = []
    for cid, per in CAMPANAS.items():
        st = json.loads(Path(glob.glob(str(ROOT / f"docs/research/**/embudo/{cid}/estado.json"), recursive=True)[0]).read_text(encoding="utf-8"))
        cs = celdas_de(st); spec = dict(st["spec"], cid=cid + "-ATRAS")
        assert per[1] < int(st["spec"]["desc"][0]), "ATRAS tiene que terminar antes del DESC"
        spec["ejecucion"] = spec["sensor"]               # proxy: se opera el CFD; `friccion` de un spot ya usa el costo de su futuro
        out.append(dict(cid=cid, spec=spec, cortes=st["cortes"], celdas=cs, periodo=per))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("plan", "lanzar", "traer")); a = ap.parse_args()
    hf = SALIDA / "handles.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}
    if a.cmd == "plan":
        for p in plan(): print(p["cid"], len(p["celdas"]), p["periodo"], p["spec"]["ejecucion"])
        return
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None)
    if a.cmd == "lanzar":
        from edgelab.funnel.multiplicity import TrialRegistry
        reg = TrialRegistry(ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl")
        for p in plan():
            if p["cid"] in hs: continue
            reg.ensure(f"atras/{p['cid']}/{p['periodo'][0]}-{p['periodo'][1]}", p["spec"]["familia"], len(p["celdas"]),
                       f"ATRAS informativa de {p['cid']} (historia no mirada, proxy CFD)")
            try: h = run.lanzar(p["spec"], "ANALIZAR_REGLA", dict(cortes=p["cortes"], celdas=p["celdas"]), p["periodo"])
            except RuntimeError as e: print("no se lanzó", p["cid"], str(e)[-150:]); continue
            hs[p["cid"]] = dict(handle=h, periodo=p["periodo"], ts=time.time()); hf.write_text(json.dumps(hs, indent=1)); print("lanzada", p["cid"])
        return
    for cid, h in hs.items():
        e = run.estado(h["handle"])
        if e != "complete": print(cid, e); continue
        r = run.traer(h["handle"]); (SALIDA / f"{cid}.json").write_text(json.dumps(r, indent=1, default=float))
        for x in r.get("reportes", []):
            ic = x.get("ic90_sesiones"); v = "A_FAVOR" if ic and ic[0] > 0 else "EN_CONTRA_PASADO" if ic and ic[1] < 0 else "SIN_RECHAZO"
            print(cid, x["celda"], x.get("n"), x.get("media"), ic, v)


if __name__ == "__main__":
    main()
