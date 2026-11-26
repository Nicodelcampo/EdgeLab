"""K28: calibración del simulador de cuentas LucidFlex de tools/cartera_lucid.py con series deterministas (resultado conocido a mano)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
pytest.importorskip("numba")


def test_sim_cuenta_lucid_calibrado():
    import cartera_lucid as CL
    x = np.zeros(300)
    gana = CL._sim_cuenta(x, 100.0, 50, 1, "25K")        # +100 por día: pasa en 13 días (1.300 ≥ 1.250, mayor día 100 ≤ 40 %)
    assert gana["pasa"] == 1.0 and gana["p_ganar"] == 1.0 and gana["retiros"] == 5.0
    # 5 retiros: el primero cuando el saldo llega a 1.000 (50 % = 500), luego cada vez que el 50 % del saldo vuelve a ser >= 500
    assert gana["cobrado"] == pytest.approx(0.9 * 500 * 5)
    pierde = CL._sim_cuenta(x, -100.0, 50, 1, "25K")     # -100 por día: nunca pasa, rompe el piso en 10 días
    assert pierde["pasa"] == 0.0 and pierde["p_ganar"] == 0.0 and pierde["ev"] == pytest.approx(-45.5)
