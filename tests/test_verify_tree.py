"""Ejecuta el self-test embebido de tools/verify_tree.py.

No necesita pyarrow: los casos adversarios usan archivos sinteticos y la logica
de la prueba fisica de holdout se testea como funcion pura.
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "verify_tree.py"


def test_selftest_verify_tree():
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--selftest"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "0 fallas" in proc.stdout


if __name__ == "__main__":
    test_selftest_verify_tree()
    print("ok")
