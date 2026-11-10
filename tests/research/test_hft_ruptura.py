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
    base = dict(rasgo="r", tercil=0, n_real=500, rompe_media=0, rompe_doble=0, avance15=0, ic90_vs_control=None, meses=8, cortes_por_activo={"NQ": [0, 0]})
    M = [dict(base, rasgo="a", rompe_real=0.12, dif_vs_control=0.1, meses_positivos=6, por_activo={"NQ": 0.1, "ES": 0.15}),
         dict(base, rasgo="a", tercil=2, rompe_real=0.10, dif_vs_control=0.1, meses_positivos=6, por_activo={"NQ": 0.1}),
         dict(base, rasgo="b", rompe_real=0.09, dif_vs_control=0.1, meses_positivos=4, por_activo={"NQ": 0.1}),       # inestable
         dict(base, rasgo="c", rompe_real=0.09, dif_vs_control=0.1, meses_positivos=6, por_activo={"NQ": 0.1, "ES": -0.1}),  # inconsistente
         dict(base, rasgo="e", rompe_real=0.085, dif_vs_control=0.1, meses_positivos=6, por_activo={"NQ": 0.1, "ES": -0.2},
              n_por_activo={"NQ": 400, "ES": 40}),                                                                   # ES chico: no cuenta
         dict(base, rasgo="d", rompe_real=0.05, dif_vs_control=0.1, meses_positivos=7, por_activo={"NQ": 0.05})]      # no paga
    assert [(m["rasgo"], m["tercil"]) for m in H.seleccionar(M)] == [("a", 0), ("e", 0)]


def test_rasgos_extra_picos_y_ema():
    # 30 velas de 1 min bajando 1 punto por minuto con un repunte de +6 cada 8 velas (deja máximos vivos arriba) hasta un cluster [100, 104]
    t, p = [], []; base = 140.0
    for m in range(30):
        for k in range(6):
            t.append(1_700_000_000 * S + (m * 60 + k * 10) * S); p.append(base - m + (6.0 if (m % 8 == 4 and k == 3) else 0.0))
    t.append(t[-1] + 5 * S); p.append(104.0); ts = np.array(t); px = np.array(p); v = np.ones(len(px))
    M = H.minutos(ts, px); j = len(px) - 1
    c = dict(lo=100.0, hi=104.0, t_ns=int(ts[0]))
    r = H.rasgos_extra(ts, px, v, j, 0, +1, 20.0, c, M)                           # llega bajando a un soporte (lado +1)
    assert r["ema9_pend"] > 0 and r["ema21_pend"] > 0                              # las EMAs bajan hacia el cluster
    assert r["picos_sin_tomar"] >= 1 and r["picos_dentro"] == 0
    assert np.isfinite(r["salida_s"]) or np.isnan(r["salida_s"])


def test_estratos_discretos_no_colapsan_y_cortes_por_activo():
    T = pd.DataFrame(dict(inst=["NQ"] * 9 + ["ES"] * 3, placebo=0, picos_sin_tomar=[0, 0, 0, 0, 0, 0, 1, 2, 5, 0, 1, 3],
                          aprox_s=[1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 200, 300.0]))
    e = H.estrato(T, "picos_sin_tomar", H.cortes_de(T, "picos_sin_tomar"))
    assert list(e) == [0] * 6 + [1, 2, 2, 0, 1, 2]                                 # 0 | 1 | ≥ 2, no todo en un tercil
    c = H.cortes_de(T, "aprox_s"); e = H.estrato(T, "aprox_s", c)
    assert sorted(e[:9]) == [0, 0, 0, 1, 1, 1, 2, 2, 2] and list(e[9:]) == [0, 1, 2]   # cada activo con sus propios terciles
    assert c["ES"][0] > c["NQ"][1]


def test_salida_desde_el_ultimo_tick_dentro_y_eficiencia():
    ts = 1_700_000_000 * S + np.arange(12) * S
    px = np.array([102, 103, 104, 106, 105, 108, 110, 112, 111, 108, 105, 104.0])   # sale del rango [100, 104] en el tick 2→3 y vuelve
    M = H.minutos(ts, px)
    r = H.rasgos_extra(ts, px, np.ones(12), 11, 5, +1, 10.0, dict(lo=100.0, hi=104.0, t_ns=int(ts[0])), M, i0=0, pasada_s=3.0)
    assert r["salida_s"] == 4.0                                                     # del tick 2 (último dentro, 104) al 6 (110 ≥ hi + X/2)
    assert abs(r["salida_eficiencia"] - 6 / 8) < 1e-12 and r["pasada_s"] == 3.0    # desplazamiento 6 sobre un camino de 8


def test_minuto_desde_la_apertura_de_la_sesion():
    assert list(H._minutos_et([1_700_000_000 * S])) == [1393]                      # 17:13 ET = 1.393 min desde las 18:00 ET del día anterior
