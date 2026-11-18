"""Motor único de ejecuciones: convención de salidas, entrada en la vuelta, límite «atraviesa» y calibración sin optimismo."""
import numpy as np
import pandas as pd
import pytest

from edgelab.research import ejecucion as X


def _p(*xs):
    return np.array(xs, float)


_NA = np.zeros(0, np.bool_)                                     # ticks reales: sin marcas de apertura (K40)


def test_mercado_objetivo_stop_al_tick_parcial_y_be():
    # venta (lado −1), ref = 90, entrada 100: D = 10; stop 0,2·D = 2; objetivo 1,0·D
    assert X._mercado_nb(_p(100, 99, 95, 90), _NA, 0, 4, -1, 90.0, 0.2, 1.0, 0.0, 0.0) == (5.0, 2.0)
    assert X._mercado_nb(_p(100, 101, 103), _NA, 0, 3, -1, 90.0, 0.2, 1.0, 0.0, 0.0)[0] == -1.5      # el salto se paga entero
    r, _ = X._mercado_nb(_p(100, 97.5, 101, 103), _NA, 0, 4, -1, 90.0, 0.2, 1.0, 0.25, 0.0)
    assert np.isclose(r, (0.5 * 2.5 + 0.5 * -3) / 2)
    assert X._mercado_nb(_p(100, 97.5, 100, 103), _NA, 0, 4, -1, 90.0, 0.2, 1.0, 0.0, 0.25)[0] == 0.0
    assert np.isnan(X._mercado_nb(_p(89, 88), _NA, 0, 2, -1, 90.0, 0.2, 1.0, 0.0, 0.0)[0])           # ya pasó la referencia


def test_vuelta_y_cancelaciones():
    ts = np.array([0, 10], np.int64); fin = np.array([1], np.int64)
    # venta tras impulso alcista: ref 0, ext 100, rg 100; se extiende a 110 (e 0,1), vuelve 5 (r 0,05) → vende en 105, stop 115
    assert X._vuelta_nb(_p(101, 106, 110, 108, 105, 80, 50), _NA, ts, fin, 0, 7, -1, 0.0, 100.0, 100.0, 0.1, 0.05, 0.05, 1, 0.5) == (5.5, 10.0)
    assert np.isnan(X._vuelta_nb(_p(101, 111, 160), _NA, ts, fin, 0, 3, -1, 0.0, 100.0, 100.0, 0.1, 0.05, 0.05, 1, 0.5)[0])   # pasó c
    assert np.isnan(X._vuelta_nb(_p(101, 104, 99), _NA, ts, fin, 0, 3, -1, 0.0, 100.0, 100.0, 0.1, 0.05, 0.05, 1, 0.5)[0])    # no extendió


def test_limite_atraviesa():
    ts = np.array([0, 10], np.int64); fin = np.array([1], np.int64)
    # compra límite 10 por debajo de ext = 100 (x 0,1 · rg 100) → 90; sólo se llena si imprime 89,75 (un tick más allá)
    assert np.isnan(X._limite_nb(_p(95, 90, 92), _NA, ts, fin, 0, 3, 1, 100.0, 100.0, 0.25, 0.1, 0.5, 1.0)[0])
    assert X._limite_nb(_p(95, 89.75, 120, 200), _NA, ts, fin, 0, 4, 1, 100.0, 100.0, 0.25, 0.1, 0.5, 1.0) == (1.0 * 100 / 50, 50.0)


def test_validar_y_nombres():
    assert not X.validar(X.CALIBRACION_BASE)
    assert X.validar([("MERCADO", 0.2, 0.5, 0.5, 0)])                      # parcial en el objetivo: inválido
    assert X.validar([("FOO", 1)]) and X.validar([("LIMITE", 0.1, 0.5, 1.0)] * 2)


def test_calibracion_sin_optimismo():
    """Con entradas al azar en caminatas sin deriva ninguna ejecución da R positivo significativo (el sesgo del stop acreditado
    en su nivel daba ≈ +0,3 R con saltos y lo detecta esta prueba)."""
    c = X.calibrar(n=1500, dias=30, seeds=(21,))
    assert c["optimistas"] == [], c["optimistas"]
    assert all(x.startswith("M_sl0.2") for x in c["m1_optimistas_con_saltos"])     # K40: M1 no ve saltos dentro de la vela (se reporta)


def test_calibracion_detecta_el_stop_acreditado_en_su_nivel(monkeypatch):
    """El error real del 2026-11-11: acreditar −1 R aunque el precio salte más allá del stop. La calibración lo marca."""
    def sesgado(tpx, j0, jw, lado, ref, sl, tp, pt, be):
        e = tpx[j0]; D = lado * (ref - e); risk = sl * D; fav = 0.0
        for j in range(j0 + 1, jw):
            fav = lado * (tpx[j] - e)
            if fav <= -risk: return -1.0, risk
            if fav >= tp * D: return tp * D / risk, risk
        return fav / risk, risk
    def lote(tpx, aper, j0, jw, ok, lado, ref, sl, tp, pt, be):
        out = np.full((len(j0), 2), np.nan)
        for q in np.flatnonzero(ok): out[q] = sesgado(tpx, j0[q], jw[q], lado[q], ref[q], sl, tp, pt, be)
        return out
    monkeypatch.setattr(X, "_lote_mercado", lote)
    assert X.calibrar(specs=[("MERCADO", 0.2, 1.0, 0, 0)], n=800, dias=30, seeds=(21,))["optimistas"][:1] == ["M_sl0.2_tp1.0_N@ticks"]


def test_precios_por_fila():
    # venta: entrada 100, objetivo 90, stop 104 → riesgo 4; toca el objetivo: +10/4
    assert X._precios_nb(_p(100, 98, 90), _NA, 0, 3, -1, 90.0, 104.0) == (2.5, 4.0)
    assert X._precios_nb(_p(100, 103, 105), _NA, 0, 3, -1, 90.0, 104.0)[0] == -1.25         # stop al tick: 105
    assert np.isnan(X._precios_nb(_p(105, 90), _NA, 0, 2, -1, 90.0, 104.0)[0])             # la entrada ya pasó el stop
    assert not X.validar([("PRECIOS", "obj", "stop")]) and X.nombre(("PRECIOS", "obj", "stop")) == "P_obj_stop"


def test_m1_stop_en_su_nivel_salvo_hueco_K40():
    """Con pseudo-ticks de M1 un stop cruzado dentro de la vela sale en su nivel; cruzado en la apertura (hueco), al precio real."""
    ap = np.array([True, True, False, False, False])
    tpx = _p(100, 100, 106, 99, 104)                                                          # venta en 100, stop 2 (102)
    assert X._mercado_nb(tpx, _NA, 0, 5, -1, 90.0, 0.2, 1.0, 0.0, 0.0)[0] == -3.0           # ticks: 106 (−6/2)
    assert X._mercado_nb(tpx, ap, 0, 5, -1, 90.0, 0.2, 1.0, 0.0, 0.0)[0] == -1.0            # M1: en el stop
    assert X._mercado_nb(_p(100, 105, 106, 104, 105), ap, 0, 5, -1, 90.0, 0.2, 1.0, 0.0, 0.0)[0] == -2.5   # hueco en la apertura
    assert X._precios_nb(tpx, ap, 0, 5, -1, 90.0, 102.0)[0] == -1.0
    ctx = dict(m1_sintetico=True, tpx=np.zeros(8), tstart=np.array([0, 4, 8], np.int64))
    assert X.aperturas(ctx).tolist() == [True, False, False, False, True, False, False, False]
    assert len(X.aperturas(dict(tpx=np.zeros(8), tstart=np.array([0, 4, 8])))) == 0


def test_precios_con_vela_de_salida_por_fila():
    """ORB-A5: («PRECIOS», obj, stop, fin) sale en la vela `fin` aunque pase de TOPE; sin `fin`, a las TOPE velas."""
    n = 400; px = 100.0 + np.arange(n) * 0.25                                     # una vela = un tick, precio que sube
    ctx = dict(t=np.arange(n) * 60.0, ses=np.full(n, 20250102), tstart=np.arange(n + 1, dtype=np.int64), tpx=px, tick=0.25)
    E = pd.DataFrame(dict(k=[0], lado=[1], ref=[1e6], ext=[0.0], rg=[1.0], obj=[1e6], stop=[50.0], fin=[350]))
    T = X.desenlaces(E, ctx, [("PRECIOS", "obj", "stop", "fin"), ("PRECIOS", "obj", "stop")])
    e = px[1]; risk = e - 50.0
    assert np.isclose(T["r_P_obj_stop_fin"][0], (px[350] - e) / risk)               # sostiene hasta la vela 350 (> TOPE = 240)
    assert np.isclose(T["r_P_obj_stop"][0], (px[X.TOPE] - e) / risk)                # sin columna: tope de TOPE velas
    assert X.validar([("PRECIOS", "a", "b", "c")]) == [] and X.validar([("PRECIOS", "a")]) != []


def test_motor_grilla_stop_m1_en_su_nivel_K40():
    """areas_expansion._primero_en_ticks: con pseudo-ticks de M1 el stop sale en su nivel salvo un hueco en la apertura."""
    from edgelab.research import areas_expansion as AX
    tpx = _p(100, 99, 103, 101)                                                          # compra, stop 100,5: la vela llega a 99
    ap = np.array([True, False, False, False])
    assert AX._primero_en_ticks(tpx, 1, 4, 1, 100.5, 110.0, 0.25, np.zeros(0, np.bool_)) == (1, 99.0)   # ticks: al tick que cruza
    assert AX._primero_en_ticks(tpx, 1, 4, 1, 100.5, 110.0, 0.25, ap) == (1, 100.5)                      # M1: en el stop
    assert AX._primero_en_ticks(_p(99, 98, 103, 101), 0, 4, 1, 100.5, 110.0, 0.25, ap) == (1, 99.0)      # hueco: abre bajo el stop
