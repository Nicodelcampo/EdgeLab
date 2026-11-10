"""Motor de fills pasivos: llena sólo según el modelo, el stop gana en empate, vence sin fill y sale por tiempo."""
import numpy as np
import pytest

from edgelab.research import fill_pasivo as FP

S = 1_000_000_000


def _serie(p):
    p = np.asarray(p, float); return 1_700_000_000 * S + np.arange(len(p)) * S, p


def test_toca_llena_atraviesa_no():
    ts, px = _serie([105, 104, 103, 100.0, 101, 106, 112])                       # baja al límite 100 justo, rebota
    a = FP.operar(ts, px, 0, 7, 100.0, +1, 5.0, 5.0, 60, 0.25, "toca")
    assert a["llena"] and a["salida"] == "objetivo" and a["r_bruto"] == 1.0
    b = FP.operar(ts, px, 0, 7, 100.0, +1, 5.0, 5.0, 60, 0.25, "atraviesa")
    assert not b["llena"] and b["salida"] == "vencida"                           # nunca imprimió 99,75: la cola no se consumió


def test_atraviesa_y_stop_gana_en_empate_y_tiempo():
    ts, px = _serie([105, 99.5, 98, 94.0, 110])                                    # atraviesa, sigue y toca el stop
    r = FP.operar(ts, px, 0, 5, 100.0, +1, 5.0, 5.0, 60, 0.25, "atraviesa")
    assert r["llena"] and r["salida"] == "stop" and r["r_bruto"] == -1.0
    ts, px = _serie([95, 100.5, 101, 102.0, 101.5])                                # venta límite en 100, sale por tiempo
    r = FP.operar(ts, px, 0, 5, 100.0, -1, 5.0, 5.0, 2, 0.25, "atraviesa")
    assert r["llena"] and r["salida"] == "tiempo" and r["r_bruto"] == pytest.approx(-(102.0 - 100.0) / 5.0)


def test_orden_fuera_de_su_vida_no_llena():
    ts, px = _serie([105, 104, 103, 99.0, 98])
    assert not FP.operar(ts, px, 0, 3, 100.0, +1, 5.0, 5.0, 60, 0.25, "toca")["llena"]   # vence antes del tick 3
