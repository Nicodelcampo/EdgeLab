"""REGIMEN-FORWARD: el vigilante declara EDGE con una serie buena, futilidad con una mala y LIMITE_VIOLADO fuera de cotas."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import regimen_forward as RF  # noqa: E402


def test_vigilante_edge_futilidad_y_cotas():
    rng = np.random.default_rng(0)
    buena = rng.normal(0.6, 1.0, 400).clip(-1.9, 11.9)
    assert RF.vigilar(buena, **RF.REGLAS["R"])["estado"] == "EDGE"
    mala = rng.normal(-0.3, 1.0, 600).clip(-1.9, 11.9)
    assert RF.vigilar(mala, **RF.REGLAS["R"])["estado"].startswith("SUSPENDER")
    assert RF.vigilar([0.1, 50.0], **RF.REGLAS["R"])["estado"] == "LIMITE_VIOLADO"
