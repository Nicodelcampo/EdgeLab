#!/usr/bin/env python3
"""Corridas de StrategyQuant X gobernadas por EdgeLab (2026-11-14). Docs: docs/infra/SQX_MT5_EDGELAB_INFRA.md.

  python tools/sqx_corrida.py preparar IDEA SIMBOLO TF [--base Builder] [--plantilla TrendFollowing]
                              [--desde 2011.01.01] [--hasta 2019.12.31] [--oos 2017.01.01] [--nulo-de ID_REAL] [--intradia]
      clona el proyecto base, (opcional) aplica la plantilla del Builder, fija los datos del Build (costos del instrumento,
      rango que NUNCA pasa del 2026-09-29) y escribe sqx/corridas/<id>/manifest.json. No lanza nada.
  python tools/sqx_corrida.py lanzar ID          # run_project (exige el manifiesto committeado: pre-registro antes de correr)
  python tools/sqx_corrida.py estado ID          # get_project_status → manifiesto + contador global (total generado = pruebas)
  python tools/sqx_corrida.py avance ID          # parcial mientras corre: real vs su nulo (piso económico), sin decidir nada
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


# Guardas de diseño (contrato de calidad, edgelab/research/sqx_calidad.py): pocas condiciones, stop y objetivo en ATR grandes frente
# al spread, generación ALEATORIA (no genética: menos sobreajuste y el total generado es el K honesto de la corrección).
DISENO = dict(max_condiciones=3, max_salidas=2, max_periodo=200, sl_atr=(2.0, 5.0), pt_atr=(2.0, 8.0), atr_periodo=(14, 50))


RIESGO_USD = 1000.0                                   # riesgo fijo por operación: R = P/L / RIESGO_USD (medición en R, CLAUDE.md)
MM_R = (f'<RiskMoneyManagement><MoneyManagement><Method type="FixedAmount" use="true"><Params>'
        f'<Param key="RiskedMoney" className="FixedAmount">{RIESGO_USD:g}</Param><Param key="Decimals" className="FixedAmount">3</Param>'
        f'<Param key="LotsIfNoMM" className="FixedAmount">0.01</Param><Param key="MaxLots" className="FixedAmount">100000</Param></Params></Method>'
        f'<InitialCapital>1000000</InitialCapital></MoneyManagement><RiskManagement maxDrawdown="100"><Method type="AllowAllTrades" use="true">'
        f'<Params /></Method></RiskManagement></RiskMoneyManagement>')


def diseno_macro(wtb: str) -> str:
    d = DISENO
    def tag(x, k, v): return re.sub(rf"<{k}>[^<]*</{k}>", f"<{k}>{v}</{k}>", x)
    wtb = re.sub(r'maxConditions="\d+"', f'maxConditions="{d["max_condiciones"]}"', wtb)
    wtb = re.sub(r'maxExitConditions="\d+"', f'maxExitConditions="{d["max_salidas"]}"', wtb)
    wtb = re.sub(r'maxPeriod="\d+"', f'maxPeriod="{d["max_periodo"]}"', wtb)
    for k, v in (("SLRequired", "true"), ("PTRequired", "true"), ("SLFixedPips", "false"), ("PTFixedPips", "false"), ("SLPercent", "false"),
                 ("PTPercent", "false"), ("SLATR", "true"), ("PTATR", "true"), ("MinSLATRMultiple", d["sl_atr"][0]), ("MaxSLATRMultiple", d["sl_atr"][1]),
                 ("MinPTATRMultiple", d["pt_atr"][0]), ("MaxPTATRMultiple", d["pt_atr"][1]), ("MinSLATRPeriod", d["atr_periodo"][0]),
                 ("MaxSLATRPeriod", d["atr_periodo"][1]), ("MinPTATRPeriod", d["atr_periodo"][0]), ("MaxPTATRPeriod", d["atr_periodo"][1])):
        wtb = tag(wtb, k, v)
    return re.sub(r'generationType="[^"]+"', 'generationType="random-generation"', wtb)


def opciones_macro(op: str, intradia: bool = False) -> str:
    """Macro de días, pero NADA abierto el fin de semana (decisión de Nico, 2026-11-14): cierre obligatorio el viernes a las 23:00 hora
    del servidor de datos (EST+07 = 16:00 de Nueva York); sí puede quedar abierta de noche (sin cierre de fin de día).
    `intradia` (2026-11-16, props de futuros: plano al cierre): cierre de fin de día a las 22:55 del servidor = 15:55 NY."""
    op = re.sub(r'(<Param key="ExitAtEndOfDay" className="ExitAtEndOfDay">)(true|false)(</Param>)', r"\1" + ("true" if intradia else "false") + r"\3", op)
    if intradia: op = re.sub(r'(<Param key="EODExitTime" className="ExitAtEndOfDay">)\d+(</Param>)', r"\g<1>2255\2", op)
    op = re.sub(r'(<Param key="ExitOnFriday" className="ExitOnFriday">)(true|false)(</Param>)', r"\1true\3", op)
    op = re.sub(r'(<Param key="FridayExitTime" className="ExitOnFriday">)\d+(</Param>)', r"\g<1>2300\2", op)
    # Gap del domingo (y de noticias): el stop/límite atravesado por un gap se llena al precio DESPUÉS del gap, como en real
    # (RealisticGapsHandling, motores MT4/MT5). Sin esto SQX lo llena en el precio pedido y regala el gap.
    if 'key="RealisticGapsHandling"' in op:
        op = re.sub(r'(<Param key="RealisticGapsHandling" className="RealisticGapsHandling">)(true|false)(</Param>)', r"\1true\3", op)
    else:
        op = op.replace("</Params>", '<Param key="RealisticGapsHandling" className="RealisticGapsHandling">true</Param></Params>', 1)
    return op


def parada(rk: str, horas: int) -> str:
    """El Build se detiene solo a las `horas` (real y nulo con el mismo presupuesto; el K real de cada uno se lee de get_project_status)."""
    return re.sub(r"<StopCondition [^>]*/>", f'<StopCondition type="time-limit" passedStrategies="1000" restartCount="5" days="0" hours="{horas}" minutes="0" />', rk)


def preparar(idea, simbolo, tf):
    from edgelab.research import ideas as I
    if not any(x["id"] == idea for x in I.leer()): raise SystemExit(f"{idea}: no está en el banco de ideas (tools/ideas.py)")
    c = MC.Cliente("sqx"); base = _arg("--base", "Builder")
    existente = _arg("--proyecto")                        # completar un clon ya creado (p. ej. tras un error a mitad de camino)
    cid = existente[3:] if existente else _id(idea, simbolo, tf); nombre = existente or f"EL {cid}"
    desde, hasta, oos = _fecha_ok(_arg("--desde", "2011.01.01")), _fecha_ok(_arg("--hasta", "2019.12.31")), _arg("--oos", "2017.01.01")
    datos = {x["symbol"]: x for x in c.llamar("list_data", {"filter": simbolo, "detail": True}).get("data", [])}
    if simbolo not in datos: raise SystemExit(f"{simbolo}: no está en list_data")
    inst = c.llamar("list_instruments", {"filter": datos[simbolo]["instrument"]})["instruments"][0]
    if not existente:
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
           f'{(inst.get("commissions") or "<Method type=\"SizeBased\" use=\"true\"><Params><Param key=\"Commission\" className=\"SizeBased\">0</Param></Params></Method>").replace("<Method", "<Commissions><Method", 1) + "</Commissions>" if "<Commissions" not in (inst.get("commissions") or "") else inst["commissions"]}'
           f'{inst.get("swap") or '<Swap use="false" type="points" long="0" short="0" tripleSwapOn="NEVER" />'}</Setup></Setups><OutOfSample showGraph="false"><Range dateFrom="{oos}" dateTo="{hasta}" /></OutOfSample></Data>')
    c.llamar("set_task_config", {"name": nombre, "taskFile": build.group(2), "section": "Data", "xml": xml})
    c.llamar("set_task_config", {"name": nombre, "taskFile": build.group(2), "section": "RiskMoneyManagement", "xml": MM_R})
    op = c.llamar("get_project_config", {"name": nombre, "taskFile": build.group(2), "section": "Options"})["xml"]
    c.llamar("set_task_config", {"name": nombre, "taskFile": build.group(2), "section": "Options", "xml": opciones_macro(op, "--intradia" in sys.argv)})
    rk = c.llamar("get_project_config", {"name": nombre, "taskFile": build.group(2), "section": "Rankings"})["xml"]
    c.llamar("set_task_config", {"name": nombre, "taskFile": build.group(2), "section": "Rankings", "xml": parada(rk, int(_arg("--horas", "2")))})
    wtb = c.llamar("get_project_config", {"name": nombre, "taskFile": build.group(2), "section": "WhatToBuild"})["xml"]
    c.llamar("set_task_config", {"name": nombre, "taskFile": build.group(2), "section": "WhatToBuild", "xml": diseno_macro(wtb)})
    m = dict(id=cid, proyecto=nombre, idea=idea, base=base, plantilla=_arg("--plantilla"), simbolo=simbolo, instrumento=datos[simbolo]["instrument"],
             timeframe=tf, build=dict(desde=desde, hasta=hasta, oos_desde=oos), tope_datos=TOPE, servidor=c.servidor,
             datos=dict(rango=[datos[simbolo].get("dateFrom"), datos[simbolo].get("dateTo")], filas=datos[simbolo].get("rows")),
             costos=dict(spread=inst["defaultSpread"], swap=inst.get("swap"), comision=inst.get("commissions")),
             diseno=DISENO, riesgo_usd=RIESGO_USD, config_build=c.llamar("get_project_config", {"name": nombre, "taskFile": build.group(2), "section": "WhatToBuild"}).get("xml", "")[:4000],
             nulo_de=_arg("--nulo-de"), es_nulo=simbolo.startswith("NULO_"),
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
    if not s.get("running") and gen:                       # el contador es inmutable por id: se registra UNA vez, al terminar cada lanzamiento
        TrialRegistry(ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl").ensure(f"sqx/{cid}/lanzamiento{len(m.get('historial', [])) + 1}",
                                                                                 f"SQX_{m['idea']}", gen, f"SQX {m['proyecto']}: estrategias generadas")
        m["estado"] = "TERMINADA"
    _guardar(cid, m); print(json.dumps({k: s.get(k) for k in ("status", "strategiesGenerated", "strategiesAccepted", "running")}))


def _filas(c, proyecto, db="Results"):
    cols = "Net profit (IS),# of trades (IS),Net profit (OOS),# of trades (OOS)"; out, off = [], 0
    while True:
        r = c.llamar("query_databank", {"name": proyecto, "databank": db, "columns": cols, "limit": 500, "offset": off})
        rows = r.get("rows", []); out += rows; off += len(rows)
        if not rows or off >= r.get("totalRows", 0): return out


def _num(x):
    try: return float(str(x).replace(",", "").replace("$", "").strip())
    except ValueError: return float("nan")


def avance(cid):
    """Lectura PARCIAL mientras corre (no decide nada: no se para ni se elige por esto). Real contra su nulo: cuántas estrategias aceptadas
    por SQX cumplen el piso económico del contrato (R medio ≥ 0,10 con ≥ 200 operaciones, IS+OOS) y la mejor R media."""
    c = MC.Cliente("sqx"); m = _cargar(cid); res = {}
    for nom, proy in (("real", m["proyecto"]), ("nulo", m.get("nulo_proyecto"))):
        if not proy: continue
        F = _filas(c, proy); vals = []
        for f in F:
            v = f.get("values", [0, 0, 0, 0])                 # orden de `cols`: neto IS, # IS, neto OOS, # OOS
            pl = _num(v[0]) + _num(v[2]); n = _num(v[1]) + _num(v[3])
            if n > 0: vals.append((pl / RIESGO_USD / n, n))
        ok = [r for r, n in vals if r >= 0.10 and n >= 200]
        res[nom] = dict(aceptadas=len(vals), piso_economico=len(ok), mejor_r=round(max([r for r, n in vals if n >= 200], default=float("nan")), 3),
                        generadas=c.llamar("get_project_status", {"name": proy}).get("strategiesGenerated"))
    m.setdefault("avances", []).append(dict(cuando=dt.datetime.now(dt.UTC).isoformat(), **res)); _guardar(cid, m); print(json.dumps(res, ensure_ascii=False))


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
    elif op in ("lanzar", "estado", "exportar", "avance"): globals()[op](a[1])
    else: raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
