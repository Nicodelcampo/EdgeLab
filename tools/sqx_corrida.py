#!/usr/bin/env python3
"""Corridas de StrategyQuant X gobernadas por EdgeLab (2026-11-14). Docs: docs/infra/SQX_MT5_EDGELAB_INFRA.md.

  python tools/sqx_corrida.py preparar IDEA SIMBOLO TF [--base "NQ CFD H1 - Dukascopy"] [--plantilla TrendFollowing]
                              [--desde 2011.01.01] [--hasta 2019.12.31] [--oos 2017.01.01]
      clona el proyecto base, (opcional) aplica la plantilla del Builder, fija los datos del Build (costos del instrumento,
      rango que NUNCA pasa del 2026-09-29) y escribe sqx/corridas/<id>/manifest.json. No lanza nada.
  python tools/sqx_corrida.py lanzar ID          # run_project (exige el manifiesto committeado: pre-registro antes de correr)
  python tools/sqx_corrida.py estado ID          # get_project_status → manifiesto + contador global (total generado = pruebas)
  python tools/sqx_corrida.py exportar ID [--databank Results] [--max 50]
      trades de cada estrategia del databank (JSON del MCP → sqx/corridas/<id>/trades/<estrategia>.csv) y su pseudocódigo.

Requiere EDGELAB_MCP_SQX (URL del túnel o local). Nada de execute_shell/run_python (el cliente los bloquea).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import mcp_cliente as MC  # noqa: E402

CORRIDAS = ROOT / "sqx/corridas"
TOPE = "2026.09.29"                                   # el holdout empieza con la sesión CME del 2026-10-01 (apertura 30-sep 22:00 UTC)


def _arg(nombre, defecto=None):
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv else defecto


def _id(idea, simbolo, tf):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", f"{idea}_{simbolo}_{tf}_{dt.datetime.now(dt.UTC).replace(tzinfo=None):%Y%m%d%H%M}")


def _man(cid) -> Path:
    return CORRIDAS / cid / "manifest.json"


def _guardar(cid, m):
    p = _man(cid); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")


def _cargar(cid) -> dict:
    return json.loads(_man(cid).read_text(encoding="utf-8"))


def _fecha_ok(f: str) -> str:
    if f.replace(".", "") > TOPE.replace(".", ""): raise SystemExit(f"{f}: pasa el tope {TOPE} (holdout)")
    return f


def preparar(idea, simbolo, tf):
    from edgelab.research import ideas as I
    if not any(x["id"] == idea for x in I.leer()): raise SystemExit(f"{idea}: no está en el banco de ideas (tools/ideas.py)")
    c = MC.Cliente("sqx"); base = _arg("--base", "NQ CFD H1 - Dukascopy"); cid = _id(idea, simbolo, tf); nombre = f"EL {cid}"
    desde, hasta, oos = _fecha_ok(_arg("--desde", "2011.01.01")), _fecha_ok(_arg("--hasta", "2019.12.31")), _arg("--oos", "2017.01.01")
    datos = {x["symbol"]: x for x in c.llamar("list_data", {"filter": simbolo, "detail": True}).get("data", [])}
    if simbolo not in datos: raise SystemExit(f"{simbolo}: no está en list_data")
    inst = c.llamar("list_instruments", {"filter": datos[simbolo]["instrument"]})["instruments"][0]
    antes = {p["name"] for p in c.llamar("list_projects")["projects"]}
    c.llamar("manage_project", {"name": base, "action": "clone"})
    nuevo = ({p["name"] for p in c.llamar("list_projects")["projects"]} - antes).pop()
    c.llamar("manage_project", {"name": nuevo, "action": "rename", "newName": nombre})
    px = c.llamar("get_project_config", {"name": nombre})["projectXml"]
    build = re.search(r'<Task type="Build" name="([^"]+)"[^>]*taskXMLFile="([^"]+)"', px)
    if not build: raise SystemExit("el proyecto base no tiene tarea Build")
    if _arg("--plantilla"): c.llamar("apply_build_template", {"name": nombre, "template": _arg("--plantilla"), "task": build.group(1)})
    xml = (f'<Data><Setups><Setup dateFrom="{desde}" dateTo="{hasta}" testPrecision="1" session="No Session" slippage="0" minDist="0" '
           f'engine="MetaTrader5 (hedged)"><Chart symbol="{simbolo}" timeframe="{tf}" spread="{inst["defaultSpread"]}" />'
           f'{inst["commissions"].replace("<Method", "<Commissions><Method", 1) + "</Commissions>" if "<Commissions" not in inst["commissions"] else inst["commissions"]}'
           f'{inst["swap"]}</Setup></Setups><OutOfSample showGraph="false"><Range dateFrom="{oos}" dateTo="{hasta}" /></OutOfSample></Data>')
    c.llamar("set_task_config", {"name": nombre, "taskFile": build.group(2), "section": "Data", "xml": xml})
    m = dict(id=cid, proyecto=nombre, idea=idea, base=base, plantilla=_arg("--plantilla"), simbolo=simbolo, instrumento=datos[simbolo]["instrument"],
             timeframe=tf, build=dict(desde=desde, hasta=hasta, oos_desde=oos), tope_datos=TOPE, servidor=c.servidor,
             datos=dict(rango=[datos[simbolo].get("dateFrom"), datos[simbolo].get("dateTo")], filas=datos[simbolo].get("rows")),
             costos=dict(spread=inst["defaultSpread"], swap=inst["swap"], comision=inst["commissions"]),
             config_build=c.llamar("get_project_config", {"name": nombre, "taskFile": build.group(2), "section": "WhatToBuild"}).get("xml", "")[:4000],
             creado=dt.datetime.now(dt.UTC).replace(tzinfo=None).isoformat() + "Z", estado="PREPARADA")
    _guardar(cid, m); print("preparada", cid, "→", nombre, "| commiteá el manifiesto antes de lanzar")


def lanzar(cid):
    m = _cargar(cid)
    if subprocess.run(["git", "log", "-1", "--format=%H", "--", str(_man(cid).relative_to(ROOT))], cwd=ROOT, capture_output=True, text=True).stdout.strip() == "":
        raise SystemExit("el manifiesto no está committeado: pre-registro antes de correr")
    print(MC.Cliente("sqx").llamar("run_project", {"name": m["proyecto"]})); m["estado"] = "LANZADA"; m["lanzada"] = dt.datetime.now(dt.UTC).replace(tzinfo=None).isoformat() + "Z"; _guardar(cid, m)


def estado(cid):
    from edgelab.funnel.multiplicity import TrialRegistry
    m = _cargar(cid); s = MC.Cliente("sqx").llamar("get_project_status", {"name": m["proyecto"]}); m["ultimo_estado"] = s
    gen = int(s.get("strategiesGenerated") or 0)
    if gen: TrialRegistry(ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl").ensure(f"sqx/{cid}", f"SQX_{m['idea']}", gen, f"SQX {m['proyecto']}: estrategias generadas")
    if not s.get("running") and gen: m["estado"] = "TERMINADA"
    _guardar(cid, m); print(json.dumps({k: s.get(k) for k in ("status", "strategiesGenerated", "strategiesAccepted", "running")}))


def exportar(cid):
    c = MC.Cliente("sqx"); m = _cargar(cid); db = _arg("--databank", "Results"); tope = int(_arg("--max", "50"))
    est = c.llamar("list_strategies", {"name": m["proyecto"], "databank": db})
    nombres = [x.get("name", x) if isinstance(x, dict) else x for x in (est.get("strategies", est) if isinstance(est, dict) else est)][:tope]
    d = CORRIDAS / cid; (d / "trades").mkdir(parents=True, exist_ok=True); (d / "reglas").mkdir(exist_ok=True)
    for n in nombres:
        t = c.llamar("get_strategy_trades", {"name": m["proyecto"], "databank": db, "strategy": n, "limit": 100000})
        filas = t.get("trades", []) if isinstance(t, dict) else []
        if filas:
            with open(d / "trades" / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', n)}.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
        src = c.llamar("get_strategy_source", {"name": m["proyecto"], "databank": db, "strategy": n, "format": "pseudocode"})
        (d / "reglas" / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', n)}.txt").write_text(src if isinstance(src, str) else json.dumps(src, ensure_ascii=False), encoding="utf-8")
    m["exportadas"] = dict(databank=db, n=len(nombres), cuando=dt.datetime.now(dt.UTC).replace(tzinfo=None).isoformat() + "Z"); _guardar(cid, m); print("exportadas", len(nombres))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--") and (sys.argv[sys.argv.index(x) - 1] if sys.argv.index(x) else "")[:2] != "--"]
    op = a[0] if a else None
    if op == "preparar": preparar(*a[1:4])
    elif op in ("lanzar", "estado", "exportar"): globals()[op](a[1])
    else: raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
