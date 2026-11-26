"""Estado de producción: cuentas prop/demo, bot de cada una, reglas y auditorías de ejecución.

Fuente única: `config/cuentas_activas.json` (se edita a mano). Este script genera `docs/ESTADO_PRODUCCION.md`
(<= 80 líneas) para leer al arrancar una sesión de bots/cuentas.

  python tools/estado_produccion.py --write     # regenera el resumen
  python tools/estado_produccion.py --check     # falla si el resumen no coincide con el JSON; avisa datos vencidos
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUENTE = ROOT / "config" / "cuentas_activas.json"
SALIDA = ROOT / "docs" / "ESTADO_PRODUCCION.md"
MAX_LINEAS = 80


def _usd(x) -> str:
    return "—" if x is None else f"${x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _dias(d: str | None, hoy: date) -> int | None:
    return None if not d else (hoy - date.fromisoformat(d)).days


def avisos(c: dict, hoy: date) -> list[str]:
    u, out = c.get("umbrales", {}), []
    for k in c["cuentas"]:
        d = _dias(k.get("balance_observado"), hoy)
        if k.get("dinero_real") and (d is None or d > u.get("dias_balance_vencido", 3)):
            out.append(f"{k['nombre']}: balance observado hace {d} días (vence a los {u.get('dias_balance_vencido', 3)})")
        if k.get("dinero_real") and k.get("reglas", {}).get("piso_verificado") is False:
            out.append(f"{k['nombre']}: piso del drawdown sin verificar en el dashboard")
    audit = [a for a in c.get("auditorias_ejecucion", []) if a.get("fecha")]
    ult = max((a["fecha"] for a in audit), default=None)
    if ult is None:
        out.append("sin auditoría de ejecución real (EdgeLabExecutionProbe + tools/audit_live_execution.py)")
    elif _dias(ult, hoy) > u.get("dias_auditoria_vencida", 14):
        out.append(f"última auditoría de ejecución {ult}: vencida")
    return out


def render(c: dict) -> str:
    L = ["# Estado de producción", "", "Estado: VIGENTE (GENERADO con `python tools/estado_produccion.py --write` desde "
         "`config/cuentas_activas.json`; no editar a mano)  ", f"Actualizado: {c['actualizado']}  ", "",
         "Operar con dinero real es decisión humana: el agente prepara, verifica y documenta; Nico activa.", "",
         "## Cuentas", "", "| cuenta | tipo | estado | dinero real | balance | observado | colchón al piso |", "|---|---|---|---|---|---|---|"]
    for k in c["cuentas"]:
        r = k.get("reglas", {})
        colchon = (k["balance"] - r["piso_usd"]) if k.get("balance") is not None and r.get("piso_usd") else None
        L.append(f"| {k['nombre']} (`{k['id']}`) | {k['tipo']} | {k['estado']} | {'sí' if k.get('dinero_real') else 'no'} | "
                 f"{_usd(k.get('balance'))} | {k.get('balance_observado') or '—'} | {_usd(colchon)}"
                 f"{'' if r.get('piso_verificado', True) else ' (piso sin verificar)'} |")
    L += ["", "## Bot por cuenta", ""]
    for k in c["cuentas"]:
        b = k.get("bot") or {}
        extra = ", ".join(f"{n} `{b[n]}`" for n in ("preset", "perfil", "max_micros", "daily_loss_bot_usd", "hard_flatten_hhmm_et") if n in b)
        L.append(f"- **{k['nombre']}**: {b.get('plataforma', '—')} `{b.get('estrategia', '—')}` en {b.get('grafico', '—')}"
                 f"{'; ' + extra if extra else ''}; {'ACTIVO' if b.get('activo') else 'NO ACTIVO'} ({b.get('activo_nota', '')}).")
        if b.get("parametros"):
            L.append(f"  Parámetros: {b['parametros']}.")
        for n in k.get("notas", []):
            L.append(f"  - {n}")
    L += ["", "## Planificadas", ""] + [f"- {p['nombre']}: {p['para']} ({p['estado']})." for p in c.get("planificadas", [])]
    L += ["", "## Auditorías de ejecución real", ""]
    au = c.get("auditorias_ejecucion", [])
    L += [f"- {a['fecha']} {a.get('cuenta', '')}: slippage {a.get('slippage_ticks', '—')} ticks, fill {a.get('fill_lat_ms', '—')} ms, "
          f"barra {a.get('bar_delay_ms', '—')} ms, n {a.get('n', '—')} ({a.get('archivo', '')})" for a in au] or ["- ninguna todavía."]
    L += ["", "Avisos al generar: ver `python tools/estado_produccion.py --check`."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    c = json.loads(FUENTE.read_text(encoding="utf-8"))
    txt = render(c)
    if len(txt.splitlines()) > MAX_LINEAS:
        print(f"FALLA: {SALIDA.name} tendría {len(txt.splitlines())} líneas (máx {MAX_LINEAS})"); return 1
    if a.write:
        SALIDA.write_text(txt, encoding="utf-8", newline="\n"); print(f"escrito {SALIDA.relative_to(ROOT)} ({len(txt.splitlines())} líneas)")
    rc = 0
    if a.check:
        if not SALIDA.exists() or SALIDA.read_text(encoding="utf-8") != txt:
            print(f"FALLA: {SALIDA.relative_to(ROOT)} no coincide con {FUENTE.relative_to(ROOT)} (correr --write)"); rc = 1
        else:
            print(f"OK: {SALIDA.relative_to(ROOT)} vigente")
    for w in avisos(c, date.today()):
        print("AVISO", w)
    return rc


if __name__ == "__main__":
    sys.exit(main())
