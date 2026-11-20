import numpy as np

from edgelab.research import contraccion as C


def _sintetico(seed=1, k=120, m=40, tau=0.05, se=0.08):
    """k campañas de m celdas: efecto verdadero ~ N(0, τ), desc y réplica con ruido se; se eligen las 10 mejores en desc.
    Contracción teórica = τ² / (τ² + se²) sobre lo elegido (≈ 0,28 con estos valores)."""
    rng = np.random.default_rng(seed); P = []
    for c in range(k):
        mu = rng.normal(0, tau, m); d = mu + rng.normal(0, se, m); r = mu + rng.normal(0, se, m)
        for i in np.argsort(-d)[:10]: P.append((f"c{c}", "F", 1000.0, d[i], r[i], None))
    return P


def test_recupera_contraccion_conocida():
    e = C.estimar(_sintetico(), B=300)
    teo = 0.05 ** 2 / (0.05 ** 2 + 0.08 ** 2)
    assert e["ic90"][0] <= teo + 0.05 and e["ic90"][1] >= teo - 0.05 and 0.1 < e["b"] < 0.45


def test_sin_efecto_contraccion_cero():
    e = C.estimar(_sintetico(tau=0.0), B=300)
    assert abs(e["b"]) < 0.1 and e["ic90"][0] < 0 < e["ic90"][1]
