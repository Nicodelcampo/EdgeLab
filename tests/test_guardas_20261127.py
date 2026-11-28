"""Guardas de los errores del 27-nov (K58–K64; docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"


def test_k63_registro_global_sin_argumentos_no_consolida():
    antes = GLOBAL.read_bytes()
    r = subprocess.run([sys.executable, str(ROOT / "tools/registro_global.py")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 2 and "consolidar" in r.stdout
    assert GLOBAL.read_bytes() == antes


def test_k58_modulo_de_alineacion_existe_y_se_cita_en_la_guia():
    guia = (ROOT / "docs/research/LEER_ANTES_DE_CADA_CORRIDA.md").read_text(encoding="utf-8")
    assert "alineacion_horaria" in guia and "K58" in guia
