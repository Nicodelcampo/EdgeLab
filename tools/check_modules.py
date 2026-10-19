#!/usr/bin/env python3
"""Valida config/modules.json contra el arbol real del repo y genera docs/MODULES.md.

Reglas (todas deben cumplirse, el chequeo sale 1 si alguna falla):
  1. cada path declarado existe;
  2. cada archivo .py de edgelab/ (salvo __init__.py) pertenece a algun modulo;
  3. depends_on referencia modulos definidos, sin ciclos, y nunca apunta a una capa superior;
  4. el doc de cada modulo existe y cada ruta de tests existe;
  5. id unico y status valido.

Uso: python tools/check_modules.py [--write]    (--write regenera docs/MODULES.md)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "modules.json"
OUT_DOC = ROOT / "docs" / "MODULES.md"


def load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _owned(file_rel: str, modules: list[dict]) -> bool:
    for m in modules:
        for p in m["paths"]:
            p = p.rstrip("/")
            if file_rel == p or file_rel.startswith(p + "/"):
                return True
    return False


def validate(reg: dict, root: Path = ROOT) -> list[str]:
    errs: list[str] = []
    mods = reg["modules"]
    ids = [m["id"] for m in mods]
    if len(set(ids)) != len(ids):
        errs.append("ids duplicados")
    by_id = {m["id"]: m for m in mods}
    for m in mods:
        if m["status"] not in reg["status_values"]:
            errs.append(f"{m['id']}: status invalido {m['status']}")
        if str(m["layer"]) not in reg["layers"]:
            errs.append(f"{m['id']}: capa invalida {m['layer']}")
        if m.get("branch"):          # vive en otra rama: se registra, no se verifica en este arbol
            if m["status"] != "other-branch":
                errs.append(f"{m['id']}: branch requiere status other-branch")
            for d in m["depends_on"]:
                if d not in by_id:
                    errs.append(f"{m['id']}: depende de modulo no definido {d}")
            continue
        for p in m["paths"]:
            if not (root / p).exists():
                errs.append(f"{m['id']}: path inexistente {p}")
        if not (root / m["doc"]).exists():
            errs.append(f"{m['id']}: doc inexistente {m['doc']}")
        for t in m["tests"]:
            if not (root / t).exists():
                errs.append(f"{m['id']}: ruta de tests inexistente {t}")
        for d in m["depends_on"]:
            if d not in by_id:
                errs.append(f"{m['id']}: depende de modulo no definido {d}")
            elif by_id[d]["layer"] > m["layer"]:
                errs.append(f"{m['id']}: depende de una capa superior ({d})")
    # ciclos
    state: dict[str, int] = {}

    def visit(n: str, stack: list[str]) -> None:
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            errs.append("ciclo: " + " -> ".join(stack + [n]))
            return
        state[n] = 1
        for d in by_id.get(n, {}).get("depends_on", []):
            visit(d, stack + [n])
        state[n] = 2

    for i in ids:
        visit(i, [])
    # propiedad de archivos
    ok_unowned = set(reg.get("unowned_ok", []))
    for f in sorted((root / "edgelab").rglob("*.py")):
        rel = f.relative_to(root).as_posix()
        if "__pycache__" in rel or f.name == "__init__.py" or rel in ok_unowned:
            continue
        if not _owned(rel, mods):
            errs.append(f"archivo sin modulo: {rel}")
    return errs


def render(reg: dict) -> str:
    L = ["# Mapa de modulos de EdgeLab", "",
         "> Generado por `tools/check_modules.py --write` desde `config/modules.json`. **No editar a mano**: cambia el registro y regenera.", "",
         "Capas (una dependencia nunca apunta a una capa superior):", ""]
    for k, v in sorted(reg["layers"].items()):
        L.append(f"- **{k}** — {v}")
    L += ["", "## Modulos", "", "| Capa | Id | Modulo | Estado | Funcion | Depende de | Doc | Tests |", "|---|---|---|---|---|---|---|---|"]
    for m in sorted(reg["modules"], key=lambda x: (x["layer"], x["id"])):
        dep = ", ".join(m["depends_on"]) or "-"
        tests = ", ".join(f"`{t}`" for t in m["tests"]) or "**sin tests**"
        L.append(f"| {m['layer']} | `{m['id']}` | {m['name']} | {m['status']} | {m['function']} | {dep} | `{m['doc']}` | {tests} |")
    L += ["", "## Conexiones (flujo de datos)", "", "```mermaid", "graph LR"]
    for m in sorted(reg["modules"], key=lambda x: (x["layer"], x["id"])):
        for d in m["depends_on"]:
            L.append(f"  {m['id'].replace('-', '_')} --> {d.replace('-', '_')}")
    L += ["```", "", "(La flecha va del consumidor al proveedor.)", "",
          "## Entradas y salidas por modulo", ""]
    for m in sorted(reg["modules"], key=lambda x: (x["layer"], x["id"])):
        L.append(f"- **{m['id']}** — entra: {', '.join(m['inputs']) or '-'}; sale: {', '.join(m['outputs']) or '-'}.")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    reg = load()
    errs = validate(reg)
    if a.write:
        OUT_DOC.write_text(render(reg), encoding="utf-8", newline="\n")
    for e in errs:
        print("FALLA:", e)
    print(f"{len(reg['modules'])} modulos, {len(errs)} problemas")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
