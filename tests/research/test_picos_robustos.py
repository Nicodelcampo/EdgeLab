"""Picos robustos: causalidad (cortar la serie no cambia lo ya confirmado) y monotonía de los factores del diseño."""
import math

import numpy as np
import pytest

from edgelab.research import picos_robustos as PR


def _serie(path, paso=1.0, ruido=0.0, seed=0):
    """Velas M1 a partir de un camino lineal por tramos (un punto por vela)."""
    rng = np.random.default_rng(seed); pts = [path[0]]
    for a, b in zip(path[:-1], path[1:]):
        k = max(1, int(abs(b - a) / paso)); pts += list(np.linspace(a, b, k + 1)[1:])
    x = np.array(pts) + rng.normal(0, ruido, len(pts)); n = len(x)
    o = np.r_[x[0], x[:-1]]; c = x
    h = np.maximum(o, c) + 0.25; l = np.minimum(o, c) - 0.25
    t = 1767225600 + 60 * np.arange(n)
    return t, h, l, c


def _cfg(**kw):
    c = PR.config("B_NIVEL"); c.update(n_atr=5); c.update(kw); return c


def _par_techo(pares):
    H = [p for p in pares if p["k"] == "H"]; assert H; return max(H, key=lambda p: p["Sf"])


def test_causalidad_corte():
    t, h, l, c = _serie([100, 80, 120, 90, 125, 85, 130, 100, 128, 95, 140, 110, 139, 100], paso=1.0, ruido=0.3, seed=3)
    cfg = _cfg(); full, _ = PR.calcular(t, h, l, c, cfg, 0.25)
    for j in (60, 120, 200, len(t) - 20):
        cut, _ = PR.calcular(t[:j], h[:j], l[:j], c[:j], cfg, 0.25)
        a = {(p["k"], p["ia"], p["ib"]): p["Sc"] for p in full if p["cf"] < j}
        b = {(p["k"], p["ia"], p["ib"]): p["Sc"] for p in cut if p["cf"] < j}
        assert a == b


def test_zigzag_confirma_despues_del_extremo():
    t, h, l, c = _serie([100, 130, 105, 140, 110], paso=1.0)
    I, K, P, Cf = PR.zigzag_alterno(h, l, PR.sesiones(t), np.full(len(h), 5.0))
    assert len(I) >= 3 and np.all(Cf > I) and np.all(np.diff(K) != 0)


@pytest.mark.parametrize("d2,mejor", [(0.0, True), (8.0, False)])
def test_cercania_sube_el_puntaje(d2, mejor):
    base = [60, 100, 70, 100, 60]                           # doble techo exacto, central 30, piernas 40
    t0, h0, l0, c0 = _serie(base); t1, h1, l1, c1 = _serie([60, 100, 70, 100 - d2, 60])
    s0 = _par_techo(PR.calcular(t0, h0, l0, c0, _cfg(), 0.25)[0])["Sf"]
    s1 = _par_techo(PR.calcular(t1, h1, l1, c1, _cfg(), 0.25)[0])["Sf"]
    assert (s1 >= s0 - 1e-9) if mejor else (s1 < s0)


def test_piernas_cortas_y_central_corta_bajan_el_puntaje():
    s = lambda path: _par_techo(PR.calcular(*_serie(path), _cfg(), 0.25)[0])["Sf"]  # noqa: E731
    largo = s([40, 100, 70, 100, 40])
    assert s([97, 100, 70, 100, 97]) < largo               # piernas de confirmación cortas EN UNIDADES DE A (~2 A)
    assert s([40, 100, 92, 100, 40]) < largo               # central corta respecto de las piernas


def test_misma_distancia_pesa_menos_con_mas_excursion():
    p_chica = PR._puntaje(40, 40, 10, 2, 1.0, _cfg())[1]["fK"]
    p_grande = PR._puntaje(40, 40, 30, 2, 1.0, _cfg())[1]["fK"]
    assert p_grande > p_chica and math.isclose(PR._puntaje(40, 40, 30, 0, 1.0, _cfg())[1]["fK"], 1.0)
