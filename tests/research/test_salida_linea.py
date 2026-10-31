"""Salida por tiempo de parada (`areas_expansion.simular_cierre_linea`, 2026-10-31): sale en la apertura siguiente al primer cierre
que cruza la línea menos δ, respeta stop y objetivo, y sin línea es idéntica a `simular_cierre`."""
import numpy as np

from edgelab.research import areas_expansion as AX


def _serie():
    c = np.array([100, 101, 102, 103, 104, 105, 104.5, 102, 101, 100.5], float)
    o = np.r_[c[0], c[:-1]]; h = np.maximum(o, c) + 0.25; l = np.minimum(o, c) - 0.25
    ses = np.zeros(len(c), np.int64); tstart = np.zeros(len(c) + 1, np.int64)
    return o, h, l, c, ses, tstart


def _uno(kl, dl, lin, stop=90.0, tp=200.0):
    o, h, l, c, ses, ts = _serie()
    a = (np.array([0]), np.array([1]), np.array([0]), np.array([np.nan]), np.array([stop]), np.array([tp]), np.array([0]))
    return AX.simular_cierre_linea(*a, o, h, l, c, ses, 0.25, np.zeros(0), ts, lin, np.array([kl], np.int64), np.array([dl]))


def test_sale_en_la_apertura_siguiente_al_cierre_que_cruza():
    lin = np.array([[99, 100, 101, 102, 103, 103.5, 104, 104.5, 105, 105.5]], float)   # soporte ascendente
    pnl, amb, fb, xb = _uno(0, 0.0, lin)
    # vela 7 cierra en 102 < 104.5: sale en la apertura de la vela 8 (= cierre de la 7, 102)
    assert xb[0] == 8 and pnl[0] == 102 - 100


def test_delta_retrasa_la_salida():
    lin = np.array([[99, 100, 101, 102, 103, 103.5, 104, 104.5, 105, 105.5]], float)
    _, _, _, xb0 = _uno(0, 0.0, lin)
    _, _, _, xb1 = _uno(0, 3.0, lin)                     # 102 < 104.5 − 3 no; 101 < 105 − 3 sí (vela 8): sale en la 9
    assert xb1[0] == 9 > xb0[0]


def test_stop_y_objetivo_siguen_activos():
    lin = np.full((1, 10), 50.0)                          # línea lejos: nunca cruza
    pnl, _, _, _ = _uno(0, 0.0, lin, tp=104.0)
    assert pnl[0] == 4.0


def test_sin_linea_igual_a_simular_cierre():
    o, h, l, c, ses, ts = _serie()
    a = (np.array([0, 2]), np.array([1, -1]), np.array([0, 0]), np.array([np.nan, np.nan]), np.array([95.0, 110.0]),
         np.array([104.0, 99.0]), np.array([0, 1]))
    r1 = AX.simular_cierre(*a, o, h, l, c, ses, 0.25, np.zeros(0), ts)
    r2 = AX.simular_cierre_linea(*a, o, h, l, c, ses, 0.25, np.zeros(0), ts, np.full((1, 1), np.nan), np.array([-1, -1], np.int64), np.zeros(2))
    for x, y in zip(r1, r2):
        assert np.array_equal(x, y, equal_nan=True)


def test_venta_sale_si_cierra_sobre_la_resistencia():
    o, h, l, c, ses, ts = _serie()
    lin = np.array([[110, 109, 108, 107, 106, 104.8, 104, 103, 102, 101]], float)
    a = (np.array([0]), np.array([-1]), np.array([0]), np.array([np.nan]), np.array([120.0]), np.array([80.0]), np.array([0]))
    pnl, _, _, xb = AX.simular_cierre_linea(*a, o, h, l, c, ses, 0.25, np.zeros(0), ts, lin, np.array([0], np.int64), np.array([0.0]))
    assert xb[0] == 6 and pnl[0] == -(c[5] - 100)          # vela 5 cierra 105 > 104.8: sale en la apertura de la 6 (105)
