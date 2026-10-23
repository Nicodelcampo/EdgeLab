"""Errores 21/23 de la revisión del 2026-10-23: todo .py trackeado parsea (un salto de línea literal dentro de un string rompió un
script que ningún test importaba), y un resultado sabe si su código sigue vigente."""
import ast
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_todo_python_trackeado_parsea():
    malos = []
    for p in subprocess.run(["git", "ls-files", "edgelab", "tools", "tests"], cwd=ROOT, capture_output=True, text=True).stdout.split():
        if not p.endswith(".py"): continue
        try: ast.parse((ROOT / p).read_text(encoding="utf-8-sig"))          # como el intérprete: tolera BOM
        except SyntaxError as e: malos.append(f"{p}:{e.lineno} {e.msg}")
        except (UnicodeDecodeError, FileNotFoundError): pass
    assert not malos, malos


def test_codigo_vigente_detecta_cambios():
    from edgelab.research.preflight import codigo_vigente
    r = json.loads((ROOT / "docs/research/areas_expansion_20261022/u1/U1_CRUZADO_20250805_20260331.json").read_text(encoding="utf-8"))
    assert isinstance(codigo_vigente(r), list)
    assert codigo_vigente(dict(modulos={"edgelab/holdout.py": "0" * 64})) == ["edgelab/holdout.py"]
