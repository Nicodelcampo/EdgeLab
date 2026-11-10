"""HFT-RUPTURA: rasgos causales, desenlaces en la dirección de ruptura, marginales y regla de selección mecánica."""
import numpy as np
import pandas as pd

from edgelab.research import hft_ruptura as H

S = 1_000_000_000


def _sesion(n=40000, seed=4):
    rng = np.random.default_rng(seed); ts = 1_700_000_000 * S + np.arange(n) * S
    px = 20000 + np.cumsum(rng.normal(0, 1.5, n)); return ts, px, np.ones(n)


def test_desenlaces_en_la_direccion_de_ruptura():
    ts = 1_700_000_000 * S + np.arange(10) * S
    px = np.array([110, 106, 104, 100, 95, 88, 84, 80, 75, 70.0])               # llega desde arriba (lado +1) y sigue bajando
    d = H.desenlaces(ts, px, 2, 104.0, +1, 20.0)
    assert d["rompe"] == 1 and d["rompe_media"] == 1 and d["avance15_x"] > 1.0
    d = H.desenlaces(ts, px[::-1].copy() * 0 + np.array([96, 100, 104, 108, 112, 118, 124, 128, 130, 132.0]), 2, 104.0, +1, 20.0)
    assert d["rompe"] == -1                                                       # rebota hacia arriba


def test_ruptura_del_dia_rasgos_completos_y_causales():
    ts, px, v = _sesion()
    C = pd.DataFrame(dict(t_ns=[int(ts[k]) for k in (8000, 20000)], lo=[px[8000] - 4, px[20000] - 4], hi=[px[8000] + 4, px[20000] + 4],
                          n_zonas=[8, 9], packing=[1.1, 0.9], net_dir=[1, -1]))
    F = pd.DataFrame(H.ruptura_del_dia("NQ", 20250805, ts, px, v, C, 0.25, 1.5455))
    assert len(F) and set(H.RASGOS) <= set(F.columns) and set(F.rompe) <= {-1, 0, 1}
    px2 = px.copy(); px2[30000:] += 1000                                          # cambiar lo posterior al horizonte no cambia rasgos
    F2 = pd.DataFrame(H.ruptura_del_dia("NQ", 20250805, ts, px2, v, C, 0.25, 1.5455))
    r1 = F[(F.placebo == 0)][H.RASGOS].iloc[0]; r2 = F2[(F2.placebo == 0)][H.RASGOS].iloc[0]
    pd.testing.assert_series_equal(r1, r2)


def test_seleccion_mecanica():
    base = dict(rasgo="r", tercil=0, n_real=500, rompe_media=0, rompe_doble=0, avance15=0, ic90_vs_control=None, meses=8, corte=[0, 0])
    M = [dict(base, rasgo="a", rompe_real=0.12, dif_vs_control=0.1, meses_positivos=6, por_activo={"NQ": 0.1, "ES": 0.15}),
         dict(base, rasgo="a", tercil=2, rompe_real=0.10, dif_vs_control=0.1, meses_positivos=6, por_activo={"NQ": 0.1}),
         dict(base, rasgo="b", rompe_real=0.09, dif_vs_control=0.1, meses_positivos=4, por_activo={"NQ": 0.1}),       # inestable
         dict(base, rasgo="c", rompe_real=0.09, dif_vs_control=0.1, meses_positivos=6, por_activo={"NQ": 0.1, "ES": -0.1}),  # inconsistente
         dict(base, rasgo="d", rompe_real=0.05, dif_vs_control=0.1, meses_positivos=7, por_activo={"NQ": 0.05})]      # no paga
    assert [(m["rasgo"], m["tercil"]) for m in H.seleccionar(M)] == [("a", 0)]
