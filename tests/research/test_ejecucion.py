"""Motor único de ejecuciones: convención de salidas, entrada en la vuelta, límite «atraviesa» y calibración sin optimismo."""
import numpy as np
import pandas as pd
import pytest

from edgelab.research import ejecucion as X


def _p(*xs):
    return np.array(xs, float)


def test_mercado_objetivo_stop_al_tick_parcial_y_be():
    # venta (lado −1), ref = 90, entrada 100: D = 10; stop 0,2·D = 2; objetivo 1,0·D
    assert X._mercado_nb(_p(100, 99, 95, 90), 0, 4, -1, 90.0, 0.2, 1.0, 0.0, 0.0) == (5.0, 2.0)
    assert X._mercado_nb(_p(100, 101, 103), 0, 3, -1, 90.0, 0.2, 1.0, 0.0, 0.0)[0] == -1.5      # el salto se paga entero
    r, _ = X._mercado_nb(_p(100, 97.5, 101, 103), 0, 4, -1, 90.0, 0.2, 1.0, 0.25, 0.0)
    assert np.isclose(r, (0.5 * 2.5 + 0.5 * -3) / 2)
    assert X._mercado_nb(_p(100, 97.5, 100, 103), 0, 4, -1, 90.0, 0.2, 1.0, 0.0, 0.25)[0] == 0.0
    assert np.isnan(X._mercado_nb(_p(89, 88), 0, 2, -1, 90.0, 0.2, 1.0, 0.0, 0.0)[0])           # ya pasó la referencia


def test_vuelta_y_cancelaciones():
    ts = np.array([0, 10], np.int64); fin = np.array([1], np.int64)
    # venta tras impulso alcista: ref 0, ext 100, rg 100; se extiende a 110 (e 0,1), vuelve 5 (r 0,05) → vende en 105, stop 115
    assert X._vuelta_nb(_p(101, 106, 110, 108, 105, 80, 50), ts, fin, 0, 7, -1, 0.0, 100.0, 100.0, 0.1, 0.05, 0.05, 1, 0.5) == (5.5, 10.0)
    assert np.isnan(X._vuelta_nb(_p(101, 111, 160), ts, fin, 0, 3, -1, 0.0, 100.0, 100.0, 0.1, 0.05, 0.05, 1, 0.5)[0])   # pasó c
    assert np.isnan(X._vuelta_nb(_p(101, 104, 99), ts, fin, 0, 3, -1, 0.0, 100.0, 100.0, 0.1, 0.05, 0.05, 1, 0.5)[0])    # no extendió


def test_limite_atraviesa():
    ts = np.array([0, 10], np.int64); fin = np.array([1], np.int64)
    # compra límite 10 por debajo de ext = 100 (x 0,1 · rg 100) → 90; sólo se llena si imprime 89,75 (un tick más allá)
    assert np.isnan(X._limite_nb(_p(95, 90, 92), ts, fin, 0, 3, 1, 100.0, 100.0, 0.25, 0.1, 0.5, 1.0)[0])
    assert X._limite_nb(_p(95, 89.75, 120, 200), ts, fin, 0, 4, 1, 100.0, 100.0, 0.25, 0.1, 0.5, 1.0) == (1.0 * 100 / 50, 50.0)


def test_validar_y_nombres():
    assert not X.validar(X.CALIBRACION_BASE)
    assert X.validar([("MERCADO", 0.2, 0.5, 0.5, 0)])                      # parcial en el objetivo: inválido
    assert X.validar([("FOO", 1)]) and X.validar([("LIMITE", 0.1, 0.5, 1.0)] * 2)


def test_calibracion_sin_optimismo():
    """Con entradas al azar en caminatas sin deriva ninguna ejecución da R positivo significativo (el sesgo del stop acreditado
    en su nivel daba ≈ +0,3 R con saltos y lo detecta esta prueba)."""
    c = X.calibrar(n=1500, dias=30, seeds=(21,))
    assert c["optimistas"] == [], c["optimistas"]


def test_calibracion_detecta_el_stop_acreditado_en_su_nivel(monkeypatch):
    """El error real del 2026-11-11: acreditar −1 R aunque el precio salte más allá del stop. La calibración lo marca."""
    def sesgado(tpx, j0, jw, lado, ref, sl, tp, pt, be):
        e = tpx[j0]; D = lado * (ref - e); risk = sl * D; fav = 0.0
        for j in range(j0 + 1, jw):
            fav = lado * (tpx[j] - e)
            if fav <= -risk: return -1.0, risk
            if fav >= tp * D: return tp * D / risk, risk
        return fav / risk, risk
    def lote(tpx, j0, jw, ok, lado, ref, sl, tp, pt, be):
        out = np.full((len(j0), 2), np.nan)
        for q in np.flatnonzero(ok): out[q] = sesgado(tpx, j0[q], jw[q], lado[q], ref[q], sl, tp, pt, be)
        return out
    monkeypatch.setattr(X, "_lote_mercado", lote)
    assert X.calibrar(specs=[("MERCADO", 0.2, 1.0, 0, 0)], n=800, dias=30, seeds=(21,))["optimistas"] == ["M_sl0.2_tp1.0_N"]
