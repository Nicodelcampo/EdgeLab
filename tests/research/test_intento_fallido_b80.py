"""INTENTO-FALLIDO-HACIA: piernas, entradas y causalidad."""
import numpy as np

from edgelab.research import intento_fallido_b80 as IB


def _camino(px):
    c = np.array(px, float); return c + 0.1, c - 0.1, c, np.zeros(len(c), np.int64)


def test_piernas_y_reacercamiento():
    # A = 10, T = 100: llega a 100.9 (best 0.8 <= 2), rechaza a 103.1 (>= 2), recupera la mitad -> r=0.5 en la vela 6
    h, l, c, ses = _camino([110, 106, 103, 101.0, 102.0, 103.0, 101.8, 104])
    F = IB._piernas(np.array([0]), np.array([1]), np.array([100.0]), np.array([10.0]), h, l, c, ses, 0.20, 0.20, np.array([0.5]), 50)
    i, ri, jB, jb, jf, best, far = F[0]
    assert (jB, jb, jf) == (6, 3, 5) and abs(best - 0.9) < 1e-9 and abs(far - 103.1) < 1e-9


def test_toca_antes_de_reacercar_no_entra():
    h, l, c, ses = _camino([110, 106, 103, 101.0, 102.0, 103.0, 99.5])
    assert IB._piernas(np.array([0]), np.array([1]), np.array([100.0]), np.array([10.0]), h, l, c, ses, 0.20, 0.20, np.array([0.5]), 50) == []


def test_causal_truncar_el_futuro():
    rng = np.random.default_rng(7); px = 110 + np.cumsum(rng.normal(0, 0.6, 400)); h, l, c, ses = _camino(px)
    args = (np.array([0]), np.array([1]), np.array([px.min() - 1.0]), np.array([15.0]))
    full = IB._piernas(*args, h, l, c, ses, 0.2, 0.2, np.array(IB.RS), 240)
    for corte in (80, 200):
        part = IB._piernas(*args, h[:corte], l[:corte], c[:corte], ses[:corte], 0.2, 0.2, np.array(IB.RS), 240)
        assert sorted(f for f in full if f[2] < corte) == sorted(part)


def test_entradas():
    ctx = dict(c=np.array([102.0, 101.5, 101.0]), ses=np.zeros(3, np.int64), tick=0.25)
    r = dict(lado=-1, k=0, stop_ref=103.1, e_lim=102.3, T=100.0, mid=97.5, lejos_zona=95.0)
    assert IB.niveles(r, ("MERC", "Z1"), ctx)[:6] == (0, 2, -1, 102.0, 103.5, 100.0)
    assert IB.niveles(r, ("CONF", "Z1"), ctx)[0] == 1                       # la vela siguiente cerró hacia la zona
    lim = IB.niveles(r, ("LIM", "Z2"), ctx); assert lim[1] == 1 and lim[3] == 102.25 and lim[5] == 97.5
