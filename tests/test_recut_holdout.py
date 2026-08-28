"""CI del re-corte de holdout: corre el self-test embebido de la herramienta.

El self-test usa un backend de parquet falso (JSON) para que toda la logica de
corte, sellado, verificacion y rechazo sea ejecutable sin pyarrow y sin datos
reales. La ruta pyarrow queda cubierta en la maquina local con --precheck.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "recut_holdout.py"


def test_tool_existe():
    assert TOOL.is_file(), f"falta {TOOL}"


def test_selftest_sin_fallas():
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--selftest"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    salida = proc.stdout + proc.stderr
    assert proc.returncode == 0, salida
    assert "self-test: 0 fallas" in proc.stdout, salida


def test_requiere_index_o_selftest():
    """Sin --index y sin --selftest la herramienta no debe hacer nada."""
    proc = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode != 0
    assert "--index" in (proc.stdout + proc.stderr)
