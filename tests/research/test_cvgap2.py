"""CVGAP-2: duraciones causales, niveles (confirmación, stop estructural, TP) y truncado del futuro."""
import numpy as np

from edgelab.research import cvgap2 as X, grilla_generica as GG, indicadores as I, preflight as PF, sintetico


def _ctx(dias=25, seed=7):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=seed), tick=0.25)


def test_estatico_y_celdas():
    assert PF.estatico(X) == []
    assert GG.n_celdas(X) == 2 * 2 * 2 * 3 * 3 * 3 * 3 * 3 * 3 * 5 * 16


def test_duraciones():
    h = np.array([100.5, 101.5, 103.0, 102.5, 101.8]); l = h - 0.5; ses = np.zeros(5, np.int64)
    # impulso alcista (d=+1), ancla 100.2, extremo 103.0 en la vela 2, decisión en la 4
    di, dr = X._duraciones(np.array([4]), np.array([1]), np.array([103.0]), np.array([100.2]), h, l, ses)
    assert dr[0] == 2 and di[0] == 2                        # la vela 0 (l = 100.0) es la última del lado de la caja


def test_causal():
    ctx = _ctx()
    D = X.disparos(ctx)
    assert len(D) > 20 and (D.dur_reg >= 0).all() and (D.dur_ida >= 0).all()
    assert I.causal(X.disparos, ctx) == []


def test_niveles():
    ctx = dict(c=np.array([100.0, 99.5, 99.0]), h=np.array([100.2, 100.8, 99.3]), l=np.array([99.8, 99.4, 98.8]),
               ses=np.zeros(3, np.int64), tick=0.25)
    r = dict(k=0, dir_imp=1, ext=101.0, h_am=2.0, mid50=95.0, mid25=93.0, orig100=90.0)   # ruptura alcista: operamos venta
    k, lim, s, e, st, tp, be, kl, dl = X.niveles(r, ("MERC", "S_E1", "MID50"), ctx)
    assert (k, lim, s, e, st, tp, kl) == (0, 2, -1, 100.0, 101.25, 95.0, 1)
    assert X.niveles(r, ("MERC", "S_EXT", "2R"), ctx)[4] == 101.5 and X.niveles(r, ("MERC", "S_EXT", "2R"), ctx)[5] == 97.0
    assert X.niveles(r, ("CONF", "S_E1", "MID50"), ctx)[:4] == (1, 2, -1, 99.5)               # la vela 1 cerró a favor
    assert X.niveles(r, ("CONF", "S_E1", "MID50"), dict(ctx, c=np.array([100.0, 100.5, 99.0]))) is None
    # la vela de confirmación hizo un máximo nuevo (101.6 > ext): el stop va detrás de ese extremo
    assert X.niveles(r, ("CONF", "S_E1", "MID50"), dict(ctx, h=np.array([100.2, 101.6, 99.3])))[4] == 102.0
