"""ESPEJO-MACRO-10T-TIEMPO: el tope de la ida en tiempo (no en velas) deja pasar idas largas en velas pero cortas en minutos, y sigue
siendo causal."""
import numpy as np

from edgelab.research import espejo_macro_tiempo as X, grilla_generica as GG, indicadores as I, preflight as PF, sintetico


def _linea(*tramos, start=20000.0):
    c = [start]
    for dest, n in tramos: c += list(np.linspace(c[-1], dest, n + 1)[1:])
    return np.asarray(c, float)


def test_tope_en_tiempo_y_no_en_velas():
    c = _linea((20120, 600), (20060, 30), (20040, 10))              # ida de 600 velas
    ses = np.zeros(len(c), np.int64)
    rapido = np.arange(len(c), dtype=float) * 2.0                   # 2 s por vela: la ida dura 20 min -> entra
    lento = np.arange(len(c), dtype=float) * 10.0                   # 10 s por vela: la ida dura 100 min -> no entra
    assert len(X._detectar_t(c, rapido, ses, 0.2, 0.5, 80.0, 8, 4, 3600.0, 7200.0)) == 1
    assert len(X._detectar_t(c, lento, ses, 0.2, 0.5, 80.0, 8, 4, 3600.0, 7200.0)) == 0


def test_causal_y_estatico():
    assert PF.estatico(X) == []
    ctx = GG.contexto_m1(sintetico.bloques(dias=8, planta=False, seed=5), tick=0.25, ticks_por_barra=10)
    assert I.causal(X.disparos, ctx) == []
