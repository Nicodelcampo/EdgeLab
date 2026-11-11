#!/usr/bin/env python3
"""Uso del agente del Debian por día (arranque 2026-11-11, §4 y §5): LLM por rol y modelo, Kaggle por cuenta, tiempo muerto y producción.

Reutiliza lo que ya existe (búsqueda `tools/existente.py buscar "uso tokens costo por rol"` del 2026-11-10: no había una herramienta de
uso; sí el libro `llm_calls` de `edgelab/autopilot/roles.py`, `account_launches.jsonl` de `edgelab/autopilot/account.py`, los estados del
embudo y los libros `propuestas.jsonl` / `promociones.jsonl` del estado). No escribe nada salvo con `--write`.

    python tools/uso_agente.py --state /var/lib/edgelab-autopilot/state/autopilot_runs [--dia AAAA-MM-DD] [--write docs/autopilot/USO_<dia>.md]

Tiempo muerto: hueco entre el fin de una llamada y el comienzo de la siguiente (con `dur_s`, la columna que agrega roles.py desde el
2026-11-10; sin ella el comienzo se aproxima con el fin). «Hueco con cola» = la parte del hueco en la que había trabajo pendiente; la cola
se reconstruye de los estados del embudo (campañas en PENDIENTE o CORRIENDO). Es una cota superior: el ciclo no registra todavía su cola.
"""
from __future__ import annotations

import argparse, collections, datetime as dt, json, sqlite3, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHES = ROOT / "docs/research/autopilot_runs/account_launches.jsonl"
ERRORES = ("INVALID_ATTEMPT_1", "INVALID_ATTEMPT_2", "LLM_INVALID_OUTPUT", "MODELO_NO_DISPONIBLE", "RATE_LIMITED")


def _dia(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d")


def _jsonl(p: Path) -> list:
    if not Path(p).exists(): return []
    out = []
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            try: out.append(json.loads(l))
            except json.JSONDecodeError: pass
    return out


def _filas(db_path: Path, dia: str) -> list:
    if not Path(db_path).exists(): return []
    db = sqlite3.connect(Path(db_path)); db.row_factory = sqlite3.Row
    cols = {r[1] for r in db.execute("PRAGMA table_info(llm_calls)")}
    dur = "dur_s" if "dur_s" in cols else "NULL AS dur_s"
    rows = [dict(r) for r in db.execute(f"SELECT ts, role, model, status, tokens_in, tokens_out, cost_usd, {dur} FROM llm_calls WHERE day=? ORDER BY ts", (dia,))]
    db.close(); return rows


def llm(db_path: Path, dia: str) -> list:
    """Por rol y modelo: llamadas reales (sin caché ni topes), OK, errores, reintentos, tokens, costo informado y duración."""
    g = collections.defaultdict(lambda: dict(llamadas=0, ok=0, errores=0, reintentos=0, cacheadas=0, saltadas_tope=0, tokens_in=0, tokens_out=0, costo_usd=0.0, dur_s=0.0, con_dur=0))
    for r in _filas(db_path, dia):
        x = g[(r["role"], r["model"])]; s = r["status"]
        if s == "CACHED": x["cacheadas"] += 1; continue
        if s == "SKIPPED_CAP": x["saltadas_tope"] += 1; continue
        x["llamadas"] += 1; x["ok"] += s == "OK"; x["errores"] += s in ERRORES; x["reintentos"] += s == "INVALID_ATTEMPT_1"
        x["tokens_in"] += int(r["tokens_in"] or 0); x["tokens_out"] += int(r["tokens_out"] or 0); x["costo_usd"] += float(r["cost_usd"] or 0)
        if r["dur_s"] is not None: x["dur_s"] += float(r["dur_s"]); x["con_dur"] += 1
    return [dict(rol=k[0], modelo=k[1], **{c: (round(v, 4) if isinstance(v, float) else v) for c, v in d.items()}) for k, d in sorted(g.items())]


def _unir(intervalos) -> list:
    """Unión de intervalos: varias campañas con cola a la vez cuentan una sola vez."""
    out = []
    for a, b in sorted((float(x), float(y)) for x, y in intervalos if y > x):
        if out and a <= out[-1][1]: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return [tuple(x) for x in out]


def _intersec(a0, a1, intervalos) -> float:
    return sum(max(0.0, min(a1, b1) - max(a0, b0)) for b0, b1 in _unir(intervalos))


def huecos(db_path: Path, dia: str, cola: list | None = None) -> dict:
    """Huecos entre llamadas consecutivas (todas las reales del día, en orden). `cola`: intervalos (t0, t1) con trabajo pendiente."""
    rs = [r for r in _filas(db_path, dia) if r["status"] not in ("CACHED", "SKIPPED_CAP")]
    h, hc = [], []
    for a, b in zip(rs, rs[1:]):
        fin_a = float(a["ts"]); ini_b = float(b["ts"]) - float(b["dur_s"] or 0)
        g = max(0.0, ini_b - fin_a); h.append(g)
        if cola is not None: hc.append(_intersec(fin_a, ini_b, cola))
    med = lambda v: round(statistics.median(v), 1) if v else None
    return dict(n_llamadas=len(rs), n_huecos=len(h), hueco_mediana_s=med(h), hueco_total_s=round(sum(h), 1),
                hueco_con_cola_mediana_s=med(hc) if cola is not None else None, hueco_con_cola_total_s=round(sum(hc), 1) if cola is not None else None,
                aproximado=any(r["dur_s"] is None for r in rs))


def cola_embudo(embudo: Path) -> list:
    """Intervalos con trabajo pendiente del embudo: de cada evento del historial al siguiente, mientras la campaña no terminó."""
    out = []
    for f in sorted(Path(embudo).glob("*/estado.json")):
        try: st = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): continue
        ts = [float(e["ts"]) for e in st.get("historial", []) if isinstance(e, dict) and e.get("ts")]
        out += [(a, b) for a, b in zip(ts, ts[1:])]
    return out


def kaggle(dia: str, launches: Path = LAUNCHES, embudo: Path | None = None) -> dict:
    """Por cuenta: kernels lanzados ese día (account_launches) y, del embudo, fallas y etapas terminadas ese día."""
    lan = collections.Counter(r["slug"].split("/")[0] for r in _jsonl(launches) if r.get("slug") and _dia(float(r["ts"])) == dia)
    fallas, fines = 0, 0
    if embudo:
        for f in Path(embudo).glob("*/estado.json"):
            try: st = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): continue
            for e in st.get("historial", []):
                if isinstance(e, dict) and e.get("ts") and _dia(float(e["ts"])) == dia:
                    fallas += "falla" in e; fines += bool(e.get("fin"))
    return dict(lanzados_por_cuenta=dict(sorted(lan.items())), lanzados=sum(lan.values()), fallas_embudo=fallas, etapas_terminadas=fines)


def produccion(state: Path, dia: str) -> dict:
    p = [r for r in _jsonl(Path(state) / "propuestas.jsonl") if r.get("ts") and _dia(float(r["ts"])) == dia]
    pr = [r for r in _jsonl(Path(state) / "promociones.jsonl") if r.get("ts") and _dia(float(r["ts"])) == dia]
    fx = [r for r in _jsonl(Path(state) / "factores_propuestos.jsonl") if str(r.get("fecha", "")) == dia]
    rev = collections.Counter((r.get("revisor") or {}).get("decision") for r in pr if isinstance(r.get("revisor"), dict))
    return dict(propuestas=len(p), propuestas_por_estado=dict(collections.Counter(r.get("status") for r in p)),
                promociones=dict(collections.Counter(r.get("decision") for r in pr)), revisor=dict(rev), factores_propuestos=len(fx))


def informe(state: Path, dia: str, launches: Path = LAUNCHES) -> dict:
    state = Path(state); db = state / "llm_calls.sqlite"; emb = state / "embudo"
    return dict(dia=dia, llm=llm(db, dia), tiempo_muerto=huecos(db, dia, cola_embudo(emb)), kaggle=kaggle(dia, launches, emb), produccion=produccion(state, dia))


def markdown(r: dict) -> str:
    l = [f"# Uso del agente del Debian — {r['dia']}", "", f"Estado: VIGENTE (GENERADO con `python tools/uso_agente.py --write`; no editar a mano).", "",
         "## LLM por rol y modelo", "", "| Rol | Modelo | Llamadas | OK | Errores | Reintentos | Caché | Tope | Tokens entrada | Tokens salida | Costo informado (USD) | Duración (s) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in r["llm"]:
        l.append(f"| {x['rol']} | `{x['modelo']}` | {x['llamadas']} | {x['ok']} | {x['errores']} | {x['reintentos']} | {x['cacheadas']} | {x['saltadas_tope']} | "
                 f"{x['tokens_in']} | {x['tokens_out']} | {x['costo_usd']:.4f} | {x['dur_s']:.0f}{'' if x['con_dur'] == x['llamadas'] else ' (parcial)'} |")
    if not r["llm"]: l.append("| — | — | 0 | | | | | | | | | |")
    t = r["tiempo_muerto"]; k = r["kaggle"]; p = r["produccion"]
    l += ["", "## Tiempo muerto", "", f"- Llamadas: {t['n_llamadas']}; huecos: {t['n_huecos']}; mediana {t['hueco_mediana_s']} s; total {t['hueco_total_s']} s.",
          f"- Hueco con cola (cota superior, cola del embudo): mediana {t['hueco_con_cola_mediana_s']} s; total {t['hueco_con_cola_total_s']} s."
          + (" Aproximado: hay llamadas sin `dur_s`." if t["aproximado"] else ""),
          "", "## Kaggle", "", f"- Kernels lanzados: {k['lanzados']} ({', '.join(f'{c}: {n}' for c, n in k['lanzados_por_cuenta'].items()) or 'ninguno'}).",
          f"- Embudo: {k['etapas_terminadas']} etapas terminadas, {k['fallas_embudo']} fallas.",
          "", "## Producción", "", f"- Propuestas: {p['propuestas']} {p['propuestas_por_estado'] or ''}", f"- Promociones: {p['promociones'] or '—'}; revisor: {p['revisor'] or '—'}",
          f"- Factores propuestos por el meta-analista: {p['factores_propuestos']}", ""]
    return "\n".join(l)


def resumen_sala(r: dict) -> str:
    n = sum(x["llamadas"] for x in r["llm"]); ok = sum(x["ok"] for x in r["llm"]); c = sum(x["costo_usd"] for x in r["llm"])
    return (f"Uso {r['dia']}: {n} llamadas LLM ({ok} OK, USD {c:.2f} informado); Kaggle {r['kaggle']['lanzados']} kernels; "
            f"hueco con cola mediana {r['tiempo_muerto']['hueco_con_cola_mediana_s']} s; {r['produccion']['propuestas']} propuestas.")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--state", required=True); ap.add_argument("--dia", default=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"))
    ap.add_argument("--launches", default=str(LAUNCHES)); ap.add_argument("--write"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args(); r = informe(Path(a.state), a.dia, Path(a.launches))
    if a.write: Path(a.write).write_text(markdown(r), encoding="utf-8"); print("escrito", a.write)
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else resumen_sala(r))


if __name__ == "__main__":
    main()
