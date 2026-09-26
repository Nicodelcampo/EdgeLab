"""Tests de tools/verify_indices.py.

El self-test de la herramienta es la cobertura real (15 grupos, incluye los
casos adulterados). Aca solo se verifica que exista, que su self-test cierre
en 0 fallas y que sin argumentos falle en vez de asumir rutas.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "verify_indices.py"


def test_tool_existe() -> None:
    assert TOOL.exists(), "falta tools/verify_indices.py"


def test_selftest_sin_fallas() -> None:
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--selftest"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "0 fallas" in proc.stdout, proc.stdout


def test_requiere_recut_o_selftest() -> None:
    proc = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode != 0
    assert "--recut" in (proc.stderr + proc.stdout)
