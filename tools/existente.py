#!/usr/bin/env python3
"""Antes de construir, buscar lo que ya existe (pedido de Nico, 2026-10-24: «la mayoría de las herramientas ya se encuentran
disponibles en el repo; que nunca un agente intente armar algo que ya existe»).

Tres comandos, sin LLM y deterministas:
  buscar "qué querés hacer" [-k 12]   funciones, clases y scripts de edgelab/ y tools/ que ya lo hacen (BM25 de
                                      edgelab/autopilot/conocimiento.py sobre nombre + firma + docstring, por función)
  catalogo [--write|--check]          docs/HERRAMIENTAS.md: cada script de tools/ con la primera línea de su docstring
                                      (--check sale 1 si un script nuevo no está: agregarlo obliga a mirar el catálogo)
  clones [--write|--check]            funciones copiadas (mismo cuerpo con otros nombres de variables) que no estaban en la
                                      línea base config/clones_baseline.json (--check sale 1 si aparece una copia nueva)

El 2026-10-24 el agente de la sesión en la nube reescribió `one` de tools/barrido_horario_etapa_c_spot.py para la celda GC 04:15
en vez de reutilizarla, como ya hacía tools/barrido_horario_etapa_c_parquet.py. `clones --check` corre en la suite
(tests/test_existente.py), así que también frena al programador del Debian, que sólo aplica código con tests verdes.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RAICES = ("edgelab", "tools")
CATALOGO = ROOT / "docs" / "HERRAMIENTAS.md"
BASELINE = ROOT / "config" / "clones_baseline.json"
MIN_SENTENCIAS = 6                 # cuerpos más cortos se parecen por casualidad
GENERADO = "# Kernel generado por"


def archivos(root: Path = ROOT):
    for r in RAICES:
        for f in sorted((root / r).rglob("*.py")):
            rel = f.relative_to(root).as_posix()
            if "__pycache__" in rel or "/archive/" in rel: continue
            try: src = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError): continue
            if src.startswith(GENERADO): continue                      # kernels empaquetados: copian módulos a propósito
            yield rel, src


def _arbol(src: str):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                              # escapes inválidos de scripts viejos: no son de este chequeo
        try: return ast.parse(src)
        except SyntaxError: return None


def _partes(nombre: str) -> str:
    return " ".join([nombre] + [p for p in re.split(r"[_\W]+|(?<=[a-z])(?=[A-Z])", nombre) if p])


def entradas(root: Path = ROOT) -> list:
    """Una entrada por script (docstring del módulo) y por función o clase: lo que el buscador indexa."""
    out = []
    for rel, src in archivos(root):
        t = _arbol(src)
        if t is None: continue
        mod = (ast.get_docstring(t) or "").strip()
        out.append(dict(ref=f"{rel}:1", nombre=Path(rel).stem, doc=mod[:600], texto=f"{_partes(rel)} {mod[:1500]}"))
        for n in ast.walk(t):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("__"):
                doc = (ast.get_docstring(n) or "").strip()
                firma = ", ".join(a.arg for a in n.args.args) if not isinstance(n, ast.ClassDef) else ""
                out.append(dict(ref=f"{rel}:{n.lineno}", nombre=n.name, doc=doc[:600],
                                texto=f"{_partes(n.name)} {_partes(firma)} {_partes(Path(rel).stem)} {doc[:1500]}"))
    return out


def buscar(consulta: str, k: int = 12, root: Path = ROOT) -> list:
    from edgelab.autopilot import conocimiento as CO
    E = entradas(root)
    idx = dict(docs=[dict(id=e["ref"], sha256=None) for e in E], pasajes=[dict(doc=e["ref"], tipo="codigo", linea=0, texto=e["texto"]) for e in E])
    por_ref = {e["ref"]: e for e in E}
    return [dict(ref=r["doc"], nombre=por_ref[r["doc"]]["nombre"], score=r["score"], doc=por_ref[r["doc"]]["doc"].split("\n")[0][:200])
            for r in CO.buscar(idx, " ".join(_partes(w) for w in consulta.split()), k=k)]


def catalogo(root: Path = ROOT) -> str:
    filas = []
    for rel, src in archivos(root):
        if not rel.startswith("tools/"): continue
        t = _arbol(src); doc = (ast.get_docstring(t) or "") if t else ""
        primera = next((l.strip() for l in doc.splitlines() if l.strip()), "(sin docstring)")
        filas.append(f"| `{rel}` | {primera.replace('|', '/')[:220]} |")
    return ("# Herramientas del repo (`tools/`)\n\nEstado: VIGENTE. Generado por `python tools/existente.py catalogo --write`; no editar a mano.\n\n"
            "**Antes de escribir un script, módulo o función:** `python tools/existente.py buscar \"qué querés hacer\"`. "
            "Si algo de acá o de `docs/MODULES.md` ya lo hace, se reutiliza (importándolo o reemplazando su lector, como "
            "`tools/barrido_horario_etapa_c_parquet.py` hace con `one`). Si se construye igual, el commit dice qué se encontró y por qué no "
            "sirve. `tests/test_existente.py` falla si un script nuevo no está acá o si aparece una función copiada.\n\n"
            f"{len(filas)} scripts.\n\n| script | qué hace (primera línea del docstring) |\n|---|---|\n" + "\n".join(filas) + "\n")


class _Anonimo(ast.NodeTransformer):
    """Cuerpo sin nombres propios: variables, argumentos y docstrings fuera; la estructura y las constantes numéricas quedan."""
    def visit_Name(self, n): return ast.copy_location(ast.Name(id="_", ctx=n.ctx), n)
    def visit_arg(self, n): n.arg = "_"; n.annotation = None; return n


def _huella(fn) -> str | None:
    cuerpo = list(fn.body)
    if cuerpo and isinstance(cuerpo[0], ast.Expr) and isinstance(getattr(cuerpo[0], "value", None), ast.Constant) and isinstance(cuerpo[0].value.value, str):
        cuerpo = cuerpo[1:]
    if sum(1 for c in cuerpo for s in ast.walk(c) if isinstance(s, ast.stmt)) < MIN_SENTENCIAS: return None
    m = ast.Module(body=[_Anonimo().visit(copy.deepcopy(c)) for c in cuerpo], type_ignores=[])
    return hashlib.sha256(ast.dump(m, annotate_fields=False).encode()).hexdigest()[:16]


def clones(root: Path = ROOT) -> dict:
    """huella -> funciones (ruta::nombre) con el mismo cuerpo anonimizado, sólo grupos de 2 o más."""
    g = {}
    for rel, src in archivos(root):
        t = _arbol(src)
        if t is None: continue
        for n in ast.walk(t):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                try: h = _huella(n)
                except (SyntaxError, ValueError, IndexError): h = None
                if h: g.setdefault(h, set()).add(f"{rel}::{n.name}")
    return {h: sorted(v) for h, v in sorted(g.items()) if len(v) > 1}


def clones_nuevos(actual: dict, base: dict) -> dict:
    """Grupos con algún miembro que la línea base no tenía como copia (sumar una copia más a un grupo viejo también cuenta)."""
    conocidos = {m for v in base.values() for m in v}
    return {h: v for h, v in actual.items() if any(m not in conocidos for m in v)}


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("buscar"); b.add_argument("consulta", nargs="+"); b.add_argument("-k", type=int, default=12)
    for c in ("catalogo", "clones"):
        p = sp.add_parser(c); p.add_argument("--write", action="store_true"); p.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.cmd == "buscar":
        for r in buscar(" ".join(a.consulta), a.k): print(f"{r['score']:7.2f}  {r['ref']:<70} {r['nombre']}: {r['doc']}")
        print("\nSi alguno ya lo hace: reutilizarlo. Si se construye igual, el commit dice qué se encontró y por qué no sirve.")
    elif a.cmd == "catalogo":
        txt = catalogo()
        if a.write: CATALOGO.write_text(txt, encoding="utf-8", newline="\n"); print(CATALOGO.relative_to(ROOT))
        elif a.check:
            ok = CATALOGO.exists() and CATALOGO.read_text(encoding="utf-8") == txt
            print("OK" if ok else "docs/HERRAMIENTAS.md desactualizado: python tools/existente.py catalogo --write (y mirá qué ya existía)"); sys.exit(0 if ok else 1)
        else: print(txt)
    else:
        act = clones()
        if a.write: BASELINE.write_text(json.dumps(act, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"); print(len(act), "grupos en la línea base")
        else:
            nuevos = clones_nuevos(act, json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {})
            for h, v in nuevos.items(): print(f"COPIA {h}: " + " = ".join(v))
            print("OK" if not nuevos else "función copiada: importá la original (o extraé una común) en vez de duplicarla")
            if a.check: sys.exit(1 if nuevos else 0)


if __name__ == "__main__":
    main()
