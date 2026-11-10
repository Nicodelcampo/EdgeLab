"""REBOTE_NIVEL_SESION: el generador produce eventos D0 de niveles de la sesión con rasgos causales y el parámetro «sin zonas»."""
import numpy as np
import pandas as pd

from edgelab.research import niveles_sesion as NV

S = 1_000_000_000


def _sesion(n=30000, seed=2):
    rng = np.random.default_rng(seed); ts = 1_700_000_000 * S + np.arange(n) * S
    return ts, 20000 + np.cumsum(rng.normal(0, 1.5, n)), np.ones(n)


def test_rasgos_zona_espacio_y_tiempo():
    t_ev = 1_700_010_000 * S
    Z = pd.DataFrame(dict(t_ns=[t_ev - 300 * S, t_ev - 1500 * S, t_ev + 10 * S], lo=[110.0, 101.0, 100.0], hi=[112.0, 103.0, 102.0]))
    r = NV.rasgos_zona(t_ev, 100.0, 102.0, 10.0, Z, None)
    assert r["dist_zona_600"] == 0.8                                               # sólo la de hace 300 s, a 8 pts = 0,8 X
    assert r["dist_zona_1800"] == 0.0 and r["n_zonas_1x_1800"] == 2.0              # la de hace 1.500 s se solapa
    assert r["dist_cluster"] == NV.SIN_ZONA                                        # la zona posterior al evento no cuenta
    C = pd.DataFrame(dict(t_ns=[t_ev - 100 * S, t_ev - 4000 * S], lo=[95.0, 100.0], hi=[96.0, 102.0]))
    assert NV.rasgos_zona(t_ev, 100.0, 102.0, 10.0, Z, C)["dist_cluster"] == 0.4   # el viejo ya no está vivo


def test_niveles_del_dia_causal_por_prefijo_y_completo():
    ts, px, v = _sesion()
    Z = pd.DataFrame(dict(t_ns=[int(ts[k]) for k in (3000, 9000, 15000)], lo=[px[k] - 2 for k in (3000, 9000, 15000)], hi=[px[k] + 2 for k in (3000, 9000, 15000)]))
    F = pd.DataFrame(NV.niveles_del_dia("NQ", 20250805, ts, px, v, Z, None, 0.25, 1.5455))
    assert len(F) > 5 and set(NV.RASGOS) <= set(F.columns) and set(F.rompe) <= {-1, 0, 1} and (F.placebo == 0).all()
    px2 = px.copy(); px2[25000:] += 500                                            # cambiar el final no cambia los rasgos de eventos anteriores
    F2 = pd.DataFrame(NV.niveles_del_dia("NQ", 20250805, ts, px2, v, Z, None, 0.25, 1.5455))
    a = F.head(3); b = F2.head(3)
    pd.testing.assert_frame_equal(a[NV.RASGOS].reset_index(drop=True), b[NV.RASGOS].reset_index(drop=True))
