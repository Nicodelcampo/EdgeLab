import numpy as np

from edgelab.research import vida_ventaja as V


def _estructura(k=30, T=150, seed=1):
    rng = np.random.default_rng(seed); return [rng.poisson(rng.uniform(1, 12), T) for _ in range(k)]


def test_recupera_rho_y_tau_conocidos():
    S = V.generar_series(_estructura(), rho=0.9, tau=0.15, seed=3)
    a = V.ajustar(S)
    assert 0.85 <= a["rho"] <= 0.95 and 0.1 <= a["tau"] <= 0.2 and a["lr_tau0"] > 10
    assert 4 <= a["vida_media_meses"] <= 14


def test_sin_regimen_no_inventa_vida():
    S = V.generar_series(_estructura(seed=2), rho=0.9, tau=0.0, seed=4)
    a = V.ajustar(S)
    assert a["tau"] <= 0.03 and a["lr_tau0"] < 3.84 and a["ic_tau"][0] == 0.0


def test_mensual_recorta_y_estandariza():
    s, n = V.mensual([1.0, -1.0, 20.0], np.array([0, 0, 2]), 4)
    assert n.tolist() == [2, 0, 1, 0] and abs(s[2] - 5.0 / np.std([1.0, -1.0, 5.0], ddof=1)) < 1e-9
