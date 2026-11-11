"""Ningún import nuevo fuera del entorno (AUTOMATIZACION_PROCESOS_20261111 I8): el análisis congelado del holdout de HFT_RUPTURA
falló el 2026-11-11 por `import scipy`, que no está en el entorno. Permitidos: biblioteca estándar, paquetes de los locks de
requirements/core-bridge-dev.lock (el .venv de CLAUDE.md), el propio repo, y la línea base de imports que ya existían (config/imports_baseline.json; sólo se achica)."""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "config/imports_baseline.json"
ALIAS = {"pyyaml": "yaml", "scikit-learn": "sklearn", "python-dateutil": "dateutil", "beautifulsoup4": "bs4", "pillow": "PIL",
         "llvmlite": "llvmlite", "typing-extensions": "typing_extensions"}
LOCALES = {"edgelab", "tests", "tools", "scripts", "docs"}


def permitidos() -> set:
    p = set(sys.stdlib_module_names) | LOCALES
    for f in [ROOT / "requirements/core-bridge-dev.lock"]:              # el entorno de trabajo declarado en CLAUDE.md (.venv); scipy no está

        for m in re.findall(r"^([A-Za-z0-9_.\-]+)==", f.read_text(encoding="utf-8"), flags=re.M):
            p.add(ALIAS.get(m.lower(), m.lower().replace("-", "_")))
    return p


def imports() -> set:
    """(archivo, módulo de primer nivel) de edgelab/ y tools/ (sin kernels generados ni dependencias opcionales en try/except)."""
    out = set()
    for f in list((ROOT / "edgelab").rglob("*.py")) + list((ROOT / "tools").rglob("*.py")):
        rel = f.relative_to(ROOT).as_posix()
        if "/kernel_" in rel or "/tablas/" in rel or "_pkg_kernel" in rel: continue
        try: tree = ast.parse(f.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError): continue
        opcionales = {id(n) for t in ast.walk(tree) if isinstance(t, ast.Try) for b in t.body for n in ast.walk(b)}
        for n in ast.walk(tree):
            if id(n) in opcionales: continue
            if isinstance(n, ast.Import): mods = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and not n.level and n.module: mods = [n.module]
            else: continue
            for m in mods: out.add((rel, m.split(".")[0]))
    return out


def faltantes() -> list:
    ok = permitidos()
    hermanos = {p.stem for d in ("edgelab", "tools", "docs", "scripts") if (ROOT / d).exists() for p in (ROOT / d).rglob("*.py")}   # módulos del repo
    hermanos |= {p.name for d in ("edgelab", "tools") for p in (ROOT / d).rglob("*") if p.is_dir()}
    return sorted(f"{a}:{m}" for a, m in imports() if m.lower() not in ok and m not in ok and m not in hermanos)


def test_sin_imports_nuevos_fuera_del_entorno():
    base = set(json.loads(BASE.read_text(encoding="utf-8"))) if BASE.exists() else set()
    nuevos = [x for x in faltantes() if x not in base]
    assert not nuevos, f"imports fuera de los locks (agregarlos al lock o no usarlos): {nuevos}"
