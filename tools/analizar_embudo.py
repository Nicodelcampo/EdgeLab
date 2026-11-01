#!/usr/bin/env python3
"""Reporte del analizador (estilo Strategy Analyzer) de las celdas que dieron positivo en el backtest y no confirmaron en el embudo.

Pedido de Nico (2026-10-26): «hay estrategias que no dan señal y son rentables en el backtesting; corré todas en la herramienta nueva».
Toma, de cada campaña del embudo, las candidatas y las pistas congeladas (todas positivas en su descubrimiento por construcción) que no
terminaron CONFIRMADAS (y sólo de campañas cuya réplica/OOS ya se evaluó: correr antes miraría la réplica), y las corre con la etapa ANALIZAR_REGLA (mismo motor que las eligió: límites, tope, ticks) sobre TODO el
desarrollo de la campaña (inicio del DESC → 2026-09-30, antes del holdout). EXPLORATORIO: las celdas ya se miraron; nada se promueve.

  python tools/analizar_embudo.py lanzar  [--raiz-glob 'docs/research/**/embudo']   # un kernel por campaña, guarda los handles
  python tools/analizar_embudo.py traer                                                # baja los reportes y escribe el resumen
"""
import argparse
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
SALIDA = ROOT / "docs/research/analizador_embudo_20261026"
HASTA = 20260930


def celdas_de(st: dict) -> list:
    """Candidatas y pistas congeladas de una campaña, sin las CONFIRMADAS, sin repetir."""
    if st.get("fase") == "CONFIRMADA": return []
    if not (st.get("oos") or (st.get("pistas_replica") or {}).get("veredicto")): return []     # réplica sin evaluar: no se mira antes
    out = [list(c) for c in st.get("candidatas") or []] + [list(c) for c in (st.get("pistas_replica") or {}).get("celdas") or []]
    conf = {tuple(c) for c in (st.get("pistas_replica") or {}).get("confirmadas") or [] if isinstance(c, list)}
    vistos, res = set(), []
    for c in out:
        if tuple(c) not in vistos and tuple(c) not in conf: vistos.add(tuple(c)); res.append(c)
    return res


def plan(patron: str) -> list:
    filas = []
    for f in sorted(glob.glob(str(ROOT / patron / "*/estado.json"), recursive=True)):
        st = json.loads(Path(f).read_text(encoding="utf-8")); cs = celdas_de(st)
        if cs and st.get("cortes") is not None:
            filas.append(dict(cid=st["spec"]["cid"], estado=f, spec=st["spec"], cortes=st["cortes"], celdas=cs,
                              periodo=[int(st["spec"]["desc"][0]), HASTA]))
    return filas


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("plan", "lanzar", "traer")); ap.add_argument("--raiz-glob", default="docs/research/**/embudo")
    a = ap.parse_args(); SALIDA.mkdir(parents=True, exist_ok=True); hf = SALIDA / "handles.json"
    if a.cmd == "plan":
        for p in plan(a.raiz_glob): print(p["cid"], len(p["celdas"]), p["periodo"])
        return
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None)
    if a.cmd == "lanzar":
        from edgelab.funnel.multiplicity import TrialRegistry
        reg = TrialRegistry(ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"); hs = json.loads(hf.read_text()) if hf.exists() else {}
        for p in plan(a.raiz_glob):
            if p["cid"] in hs and run.estado(hs[p["cid"]]["handle"]) != "error": continue
            reg.ensure(f"analizador_embudo/{p['cid']}/{p['periodo'][0]}-{p['periodo'][1]}", p["spec"]["familia"], len(p["celdas"]),
                       f"analizador de celdas ya miradas de {p['cid']} (exploratorio, desarrollo completo)")
            cuentas = run.cuentas(); spec = dict(p["spec"], cid=p["cid"] + "-AN")
            for i in range(len(cuentas)):                                   # tope de kernels simultáneos por cuenta: probar la otra
                spec["cuenta_kaggle"] = cuentas[(len(hs) + i) % len(cuentas)]
                try: h = run.lanzar(spec, "ANALIZAR_REGLA", dict(cortes=p["cortes"], celdas=p["celdas"]), p["periodo"]); break
                except RuntimeError as e: h = None; print("no se lanzó", p["cid"], spec["cuenta_kaggle"], str(e)[-120:])
            if h is None: continue                                          # se reintenta en el próximo `lanzar`
            hs[p["cid"]] = dict(handle=h, periodo=p["periodo"], n=len(p["celdas"]), ts=time.time())
            hf.write_text(json.dumps(hs, indent=1)); print("lanzada", p["cid"], len(p["celdas"]))
        return
    hs = json.loads(hf.read_text()); filas = []
    for cid, h in hs.items():
        e = run.estado(h["handle"])
        if e != "complete": print(cid, e); continue
        r = run.traer(h["handle"]); (SALIDA / f"{cid}.json").write_text(json.dumps(r, indent=1, default=float))
        for x in r.get("reportes", []):
            filas.append(dict(cid=cid, celda=x["celda"], n=x.get("n"), neto=x.get("neto_total"), media=x.get("media"), pf=x.get("profit_factor"),
                              dd=x.get("drawdown_max"), ic90=x.get("ic90_sesiones"), p=x.get("p_sesiones")))
    filas.sort(key=lambda f: -(f["media"] or -1e9))
    (SALIDA / "RESUMEN.json").write_text(json.dumps(filas, indent=1, default=float)); print(len(filas), "celdas")


if __name__ == "__main__":
    main()
