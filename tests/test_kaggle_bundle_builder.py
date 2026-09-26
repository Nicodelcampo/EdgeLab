"""El self-test del builder del bundle de Kaggle corre como test de CI.

No toca datos reales ni requiere pyarrow: usa un árbol temporal de archivos
sintéticos y un censo de footer simulado. Cubre la frontera del sello del
holdout al nanosegundo, el gate de licencia, la detección de archivos con
holdout, el comportamiento fail-closed ante carpetas/archivos rotos, los
presupuestos del contrato y el round-trip del staging.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "build_kaggle_bundle.py"


def test_build_kaggle_bundle_selftest():
    pytest.importorskip("numpy")
    assert SCRIPT.is_file(), f"falta {SCRIPT}"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--selftest"],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "self-test: 0 fallas" in proc.stdout, proc.stdout
