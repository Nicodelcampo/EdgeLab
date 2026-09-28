"""TBZX: métricas de afuera/reingreso sobre un camino sintético con respuesta conocida (manifiesto §3)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import tbzx_espejo as TX  # noqa: E402


def _bars(closes, wick=0):
    c = np.asarray(closes, dtype=np.int64)
    return (np.arange(len(c), dtype=float) * 10.0, c + wick, c - wick, c, np.ones(len(c)))


def test_sale_por_B_se_aleja_vuelve_y_cruza_hasta_A():
    # impulso alcista A=0 -> B=20 (W=20). e = vela 0 (cierre 14, adentro).
    closes = [14, 18, 22, 25, 23, 19, 10, 2, -1, -3] + [0] * 60
    t, H, L, C, V = _bars(closes)
    m = dict(zip(TX.MET, TX.path_metrics(t, H, L, C, V, 0, 1, 0, 20, 20, 60, 50)))
    assert m["exited"] == 1 and m["side_B"] == 1
    assert m["bars_to_exit"] == 2                 # primera vela con cierre > 20: la 2
    assert m["exc_ticks"] == 5 and m["exc_W"] == 0.25
    assert m["out_bars"] == 3 and m["out_vol"] == 3   # velas 2, 3, 4 afuera; vuelve en la 5
    assert m["reentered"] == 1
    assert m["pen_W"] == (20 - (-3)) / 20          # desde el borde B hasta el mínimo -3
    assert m["reach_opp"] == 1 and m["reach_mirror"] == 0
    assert m["re_tpb"] == (25 - (-3)) / (9 - 3)    # de la vela del extremo afuera (3) a la de máxima penetración (9)


def test_no_sale_nunca():
    t, H, L, C, V = _bars([10] * 80)
    m = dict(zip(TX.MET, TX.path_metrics(t, H, L, C, V, 0, 1, 0, 20, 20, 60, 50)))
    assert m["exited"] == 0 and np.isnan(m["side_B"])
    assert m["tot_out_B_bars"] == 0 and m["tot_out_A_bars"] == 0


def test_bajista_sale_por_A():
    # impulso bajista A=20 -> B=0 (d=-1). Sale por arriba (lado A) y no vuelve.
    closes = [8, 15, 21, 24, 26] + [27] * 70
    t, H, L, C, V = _bars(closes)
    m = dict(zip(TX.MET, TX.path_metrics(t, H, L, C, V, 0, -1, 20, 0, 20, 60, 50)))
    assert m["side_B"] == 0 and m["reentered"] == 0 and m["exc_ticks"] == 7
