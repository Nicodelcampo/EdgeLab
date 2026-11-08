"""ORB-VARIANTES: objetivo en múltiplos de R, stop por last, cierre, comisión por instrumento y BH con m heredado."""
import numpy as np
import medir_variantes as V

T = np.arange(10) * 10; BID = np.array([100., 100, 101, 102, 104, 103, 99, 98, 100, 100]); ASK = BID + 1


def _ll(last, obj, cierre=85):
    return V.llenar(T, np.asarray(last, float), BID, ASK, 5, cierre, 100, 1, 98.0, 0, 1.0, 0.0, obj)


def test_objetivo_stop_y_cierre():
    last = [100, 100, 101, 102, 105, 103, 99, 97, 100, 100]
    # entrada ask[1]=101, riesgo 3; objetivo 1R = 104: el last 105 lo atraviesa en t=40 -> +1R exacto
    assert abs(_ll(last, 1.0) - 1.0) < 1e-12
    # 2R = 107 nunca: el stop (98) se toca por last 97 en t=70 -> sale al bid 98: (98-101)/3
    assert abs(_ll(last, 2.0) - (-1.0)) < 1e-12
    # sin objetivo y cierre en t=35: sale al bid del primer tick >= cierre (t=40, bid 104): +1R
    assert abs(_ll(last, None, cierre=35) - 1.0) < 1e-12
    # objetivo tocado sin atravesar (last == objetivo) no llena
    assert abs(_ll([100, 100, 101, 102, 104, 103, 99, 97, 100, 100], 1.0) - (-1.0)) < 1e-12


def test_bh_usa_m_heredado():
    res = {("a",): dict(p=0.0001, evaluable=True), ("b",): dict(p=0.03, evaluable=True), ("c",): dict(p=0.5, evaluable=False)}
    assert V.bh(res, 2) == {("a",), ("b",)} and V.bh(res, 100) == {("a",)} and V.bh(res, 5000) == set()


def test_modelo_last_usa_medio_spread():
    last = np.array([100., 100, 101, 102, 105, 103, 99, 97, 100, 100]); V.MODELO = "last"; V.SPREAD_ACTUAL = 2.0
    try:   # entrada last[1]+1 = 101 (igual que ask), riesgo 3; objetivo 1R = 104 atravesado -> +1R
        assert abs(V.llenar(T, last, BID, ASK, 5, 85, 100, 1, 98.0, 0, 1.0, 0.0, 1.0) - 1.0) < 1e-12
    finally: V.MODELO = "bidask"; V.SPREAD_ACTUAL = 0.0
