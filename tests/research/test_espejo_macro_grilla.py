"""ESPEJO-MACRO-10T: el port numba reproduce la geometría del detector de foundation (montaña lisa sí, serrucho no, corte en la
fracción), es causal, y la orden va hacia A con stop más allá de B."""
import numpy as np

from edgelab.research import espejo_macro_grilla as X, grilla_generica as GG, indicadores as I, preflight as PF, sintetico


def _linea(*tramos, start=20000.0):
    c = [start]
    for dest, n in tramos: c += list(np.linspace(c[-1], dest, n + 1)[1:])
    return np.asarray(c, float)


def _det(c, f=0.5, retro=0.2):
    return X._detectar(c, np.zeros(len(c), np.int64), retro, f, 80.0, 8, 4, 400)


def test_montana_lisa_corta_en_la_fraccion():
    c = _linea((20120, 12), (20060, 6), (20040, 4))
    d = _det(c)
    assert len(d) == 1
    i0, ie, k, lado, W, ri, rv = d[0]
    assert lado == 1 and W == 120 and c[ie] - c[k] >= 60 and c[ie] - c[k - 1] < 60
    lenta = _linea((20120, 12), (20030, 12), (20000, 4))                   # vuelta más lenta: al 25 % ya pasaron >= 4 velas
    k25, k50 = _det(lenta, f=0.25)[0][2], _det(lenta, f=0.5)[0][2]
    assert k25 < k50                                                        # al 25 % se conoce antes que al 50 %


def test_baja_lisa_y_serrucho():
    assert _det(_linea((19880, 12), (19940, 6), (19980, 4)))[0][3] == -1
    serrucho = _linea((20060, 6), (20020, 4), (20120, 6), (20060, 6), (20040, 4))   # la ida devuelve 40 de 60 (> 20 %)
    assert all(x[5] <= 0.2 for x in _det(serrucho))


def test_causal_y_estatico():
    assert PF.estatico(X) == []
    ctx = GG.contexto_m1(sintetico.bloques(dias=8, planta=False, seed=5), tick=0.25, ticks_por_barra=10)
    assert I.causal(X.disparos, ctx) == []


def test_niveles_hacia_a_con_stop_mas_alla_de_b():
    ctx = dict(c=np.array([20060.0, 20059.0]), ses=np.zeros(2, np.int64), tick=0.25)
    r = dict(k=0, lado=-1, A=20000.0, B=20120.0, W=120.0)               # impulso alcista: la orden es venta hacia A
    k, lim, s, e, st, tp, be, kl, dl = X.niveles(r, ("B1", "A"), ctx)
    assert (s, st, tp, lim) == (-1, 20120.25, 20000.0, 2)
    assert X.niveles(r, ("B10", "M75"), ctx)[4:6] == (20132.0, 20030.0)


def test_friccion_fija_coincide_con_costos():
    from edgelab import costos
    for inst, v in X.FRICCION_SEVERA_TICKS.items():
        assert abs(costos.friccion_rt_ticks(inst, "severo") - v) < 1e-3, inst
