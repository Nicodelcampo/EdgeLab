"""INTENTO-FALLIDO (idea de Nico, 2026-11-03): geometría del intento, vías A y B, y causalidad (truncar el futuro no cambia el pasado)."""
import numpy as np
import pandas as pd

from edgelab.research import intento_fallido as IF


def _camino(precios):
    c = np.array(precios, float); h = c + 0.1; l = c - 0.1
    return h, l, c, np.zeros(len(c), np.int64)


def _corre(precios, T=100.0, A=10.0, d=1):
    h, l, c, ses = _camino(precios)
    return IF._intentos(np.array([0]), np.array([d]), np.array([T]), np.array([A]), h, l, c, ses,
                        np.array([0.10]), np.array([0.20]), np.array([0.5]), 50)


def test_toca_el_objetivo_no_hay_intento():
    # baja desde 110 hasta tocar 100 (el borde): U1 cumplió, no hay intento fallido
    assert _corre([110, 106, 103, 100.05, 99.5, 104]) == []


def test_via_a_y_via_b():
    # se acerca a 100.9 (best = 0.8 <= y=1.0), rebota +2 (z=2.0) al cierre -> A; luego recupera la mitad -> B hacia y B en contra
    F = _corre([110, 106, 103, 101.0, 102.0, 103.0, 101.8, 104])
    reglas = [(f[3], f[4]) for f in F]
    assert (0, 5) in reglas                                       # A al cierre de la vela 5 (103 - 100 - 0.9 >= 2.0)
    assert (1, 6) in reglas and (3, 6) in reglas                  # B50: vuelve a <= 3.0 - 0.5*(3.0 - 0.9) = 1.95 -> 101.8
    a = [f for f in F if f[3] == 0][0]
    assert abs(a[5] - 100.9) < 1e-9                               # stop_ref = precio más cercano del intento


def test_sin_acercarse_a_y_no_hay_evento():
    assert _corre([110, 106, 104, 106, 108, 110]) == []           # nunca llegó a 1.0 del objetivo


def test_lado_contrario_simetrico():
    F = _corre([90, 94, 97, 99.0, 98.0, 97.0], T=100.0, d=-1)    # precio abajo, objetivo = borde inferior 100
    assert any(f[3] == 0 and f[4] == 5 for f in F)


def test_causal_truncar_el_futuro_no_cambia_lo_ya_decidido():
    rng = np.random.default_rng(5); px = 110 + np.cumsum(rng.normal(0, 0.6, 400))
    h, l, c, ses = _camino(px)
    args = (np.array([0]), np.array([1]), np.array([px.min() - 1.0]), np.array([15.0]))
    full = IF._intentos(*args, h, l, c, ses, np.array(IF.YS), np.array(IF.ZS), np.array(IF.RS), 240)
    for corte in (60, 150, 300):
        part = IF._intentos(*args, h[:corte], l[:corte], c[:corte], ses[:corte], np.array(IF.YS), np.array(IF.ZS), np.array(IF.RS), 240)
        assert sorted(f for f in full if f[4] < corte) == sorted(part)


def test_niveles_stop_estructural_y_objetivos():
    ctx = dict(c=np.array([103.0]), tick=0.25)
    r = dict(lado=1, k=0, stop_ref=100.9, lejos=110.0)
    k, lim, s, e, st, tp, be, kl, dl = IF.niveles(r, ("2R",), ctx)
    assert (s, st, kl) == (1, 100.5, 0) and abs(tp - (103 + 2 * 2.5)) < 1e-9
    assert IF.niveles(r, ("LEJOS",), ctx)[5] == 110.0
    assert IF.niveles(dict(r, stop_ref=104.0), ("2R",), ctx) is None          # stop del lado equivocado: no se opera
