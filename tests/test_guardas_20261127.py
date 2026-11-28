"""Guardas de los errores del 27-nov (K58–K64; docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md)."""
import subprocess
import sys
from pathlib import Path

import pytest

from edgelab.holdout import exigir_sin_holdout_no_abierto, mascara_a5_limpia

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


def test_k60_exigir_sin_holdout_no_abierto_bloquea_y_permite():
    # Para 2024: verificar una fecha DESC y una fecha HOLDOUT conocidas vía a5_meses
    from edgelab.holdout import a5_meses
    meses = a5_meses(2024)
    m_desc = next(m for m, b in meses.items() if b == "DESC")
    m_ho = next(m for m, b in meses.items() if b == "HOLDOUT")
    f_desc = int(f"2024{m_desc:02d}15")
    f_ho = int(f"2024{m_ho:02d}15")

    assert list(mascara_a5_limpia([f_desc, f_ho], [f_desc, f_ho])) == [True, False]
    exigir_sin_holdout_no_abierto([f_desc], "FAMILIA_SIN_APERTURA")
    with pytest.raises(ValueError, match="K60/A5"):
        exigir_sin_holdout_no_abierto([f_desc, f_ho], "FAMILIA_SIN_APERTURA")
    # Una familia con apertura vigente registrada sí pasa
    exigir_sin_holdout_no_abierto([f_ho], "CARRIL2_A5")
    with pytest.raises(ValueError, match="TERMINAL"):
        exigir_sin_holdout_no_abierto([20261005], "CARRIL2_A5")
