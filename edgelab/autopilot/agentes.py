"""Fuente única de agentes, roles y modelos del agente del Debian: `config/autopilot/AGENTES.json` (2026-11-09).

Antes los modelos estaban escritos a mano en roles.py, programador.py, orquestador_multiagente.py, TOPOLOGIA_AGENTES_DEBIAN.json y la
plantilla de despliegue, y no coincidían (roles 5.5 vs topología 4.6). Ahora todos leen de acá; `tests/autopilot/test_agentes.py`
falla si algo vuelve a escribir un modelo a mano o si la documentación generada queda vieja.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / "config/autopilot/AGENTES.json"


@lru_cache(maxsize=1)
def tabla() -> dict:
    t = json.loads(RUTA.read_text(encoding="utf-8"))
    de_rol = {}
    for nombre, a in t["agentes"].items():
        for r in a["roles"]:
            if r in de_rol: raise ValueError(f"rol {r} asignado a dos agentes")
            de_rol[r] = nombre
    if set(de_rol) != set(t["roles"]): raise ValueError(f"roles sin agente o agentes con roles inexistentes: {set(de_rol) ^ set(t['roles'])}")
    return t


def agente_de(rol: str) -> str:
    return next(n for n, a in tabla()["agentes"].items() if rol in a["roles"])


def modelo(rol: str) -> str:
    """Identificador exacto del modelo del rol (el del agente al que pertenece)."""
    t = tabla(); return t["modelos"][t["agentes"][agente_de(rol)]["modelo"]]["id"]


def rol(nombre: str) -> dict:
    t = tabla(); a = t["agentes"][agente_de(nombre)]
    return dict(t["roles"][nombre], modelo=modelo(nombre), agente=agente_de(nombre), contexto_max_chars=a.get("contexto_max_chars", 30000))


def markdown() -> str:
    t = tabla(); L = ["# Agentes del Debian — roles, modelos y tareas", "",
                      f"Estado: VIGENTE (GENERADO de `config/autopilot/AGENTES.json` con `python tools/agentes.py --write`; no editar a mano). Actualizado: {t['actualizado']}.", "",
                      "## Agentes", "", "| Agente | Modelo | Función | Contexto máx. (caracteres) | Roles |", "|---|---|---|---|---|"]
    for n, a in t["agentes"].items():
        m = t["modelos"][a["modelo"]]["id"] if "modelo" in a else a.get("motor", "")
        L.append(f"| {n} | `{m}` | {a['rol']} | {a.get('contexto_max_chars', '—')} | {', '.join(a['roles']) or '—'} |")
    L += ["", "## Roles", "", "| Rol | Agente | Modelo | Tope diario | Núcleo de contexto | Tarea |", "|---|---|---|---|---|---|"]
    for n in t["roles"]:
        r = rol(n); L.append(f"| {n} | {r['agente']} | `{r['modelo']}` | {r['tope_diario']} | {'sí' if r['nucleo'] else 'no'} | {r['tarea']} |")
    L += ["", "## Modelos", "", "| Alias | Identificador | USD por millón (entrada / salida) | Para qué |", "|---|---|---|---|"]
    for k, m in t["modelos"].items(): L.append(f"| {k} | `{m['id']}` | {m['usd_mtok_entrada']} / {m['usd_mtok_salida']} | {m['para']} |")
    L += ["", "El que propone (arquitecto) y el que juzga (juez, auditor) son modelos distintos a propósito: separación de poderes.", ""]
    return "\n".join(L)
