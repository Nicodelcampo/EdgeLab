"""K28: calibración de los simuladores de cuentas del Monte Carlo 20k de la auditoría de Antigravity (2026-11-26).

El código vive dos veces: como plantilla de texto en tools/optimizar_cartera_v2.py y como kernel de Kaggle en
docs/research/auditoria_cartera_20261126/kaggle_mc20k/kaggle_mc20k.py. Se calibra el kernel (lo que corrió) con series constantes,
cuyo resultado se calcula a mano, y se verifica que la plantilla sea el mismo código.

Alcance: esto prueba que el simulador hace lo que dicen sus propias reglas. NO prueba que esas reglas sean las de LucidFlex/Tradeify/FTMO:
el retiro («saldo − piso − 500», hasta 4) difiere del de tools/cartera_lucid.py (50 % del saldo), que es el calibrado contra las reglas de
la cuenta (tests/research/test_cartera_lucid_calibracion.py). Los EV de props de la auditoría son, por eso, exploratorios.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
KERNEL = ROOT / "docs/research/auditoria_cartera_20261126/kaggle_mc20k/kaggle_mc20k.py"
pytest.importorskip("numba")


def _kernel():
    sp = importlib.util.spec_from_file_location("kaggle_mc20k_auditoria", KERNEL)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def _c(v, n=200):
    return np.full(n, float(v))


def test_K28_sims_props_mc20k_calibrados():
    K = _kernel()
    # Lucid/Tradeify: +100 por día, objetivo 1.250, consistencia 50 % → pasa al día 13 (1.300; mayor día 100 ≤ 650).
    # Fondeada: el retiro es saldo − max(piso, 0) − 500 si ≥ 250, tras 5 días buenos y ≥ 500 de saldo nuevo:
    # día 8 → 300; luego cada 5 días saldo 1.000 con piso 0 → 500 (×3, tope 4 retiros) = 1.800; EV = 1.800 − 100.
    r = K.sim_lucid_or_tradeify(_c(100), _c(100), 1.0, 100.0, 1250.0, 1000.0, 1100.0, 1e9, 1500.0, 100.0, 50.0, 0.5, 1.0, 0, 10, 7)
    assert r == pytest.approx((1.0, 1.0, 1700.0, 1.0, 0.0, 1800.0, 13.0))
    # −100 por día: al día 10 el mínimo toca el piso −1.000 → quiebra; EV = −precio.
    r = K.sim_lucid_or_tradeify(_c(-100), _c(-100), 1.0, 100.0, 1250.0, 1000.0, 1100.0, 1e9, 1500.0, 100.0, 50.0, 0.5, 1.0, 0, 10, 7)
    assert r == pytest.approx((0.0, 0.0, -100.0, 0.0, 1.0, 0.0, 0.0))
    # FTMO 100K: +1.000 por día → fase 1 al día 10, fase 2 al día 5; fondeada cada 14 días cobra 80 % de 14.000 (+580 de reintegro en el
    # primero): 11.780 + 3 × 11.200 = 45.380; EV = 45.380 − 580.
    assert K.sim_ftmo_100k(_c(1000), _c(1000), 1.0, 1.0, 10, 7) == pytest.approx((1.0, 1.0, 44800.0, 1.0, 45380.0))
    assert K.sim_ftmo_100k(_c(-1000), _c(-1000), 1.0, 1.0, 10, 7) == pytest.approx((0.0, 0.0, -580.0, 0.0, 0.0))
    # Broker: 252 sesiones de ±10 → retorno ±2.520; caída 0 o −2.520.
    r, d = K.sim_broker_tails(_c(10), _c(10), 1.0, 5, 7); assert np.allclose(r, 2520.0) and np.allclose(d, 0.0)
    r, d = K.sim_broker_tails(_c(-10), _c(-10), 1.0, 5, 7); assert np.allclose(r, -2520.0) and np.allclose(d, -2520.0)


def test_plantilla_y_kernel_son_el_mismo_codigo():
    plantilla = (ROOT / "tools/optimizar_cartera_v2.py").read_text(encoding="utf-8")
    kernel = KERNEL.read_text(encoding="utf-8")
    for f in ("sim_lucid_or_tradeify", "sim_ftmo_100k", "sim_broker_tails"):
        cuerpo = kernel.split(f"def {f}(", 1)[1].split("\n@njit", 1)[0].split("\ndef main", 1)[0]
        assert cuerpo in plantilla, f
