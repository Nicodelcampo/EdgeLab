"""HFT-REBOTES: cada definición dispara en su caso y no en los vecinos; un evento por cluster; sólo ticks posteriores."""
import numpy as np
import pandas as pd

from edgelab.research import hft_rebotes as R

S = 1_000_000_000; X = 20.0; LO, HI = 100.0, 104.0


def _serie(tramos):
    """tramos = [(precio_final, segundos, ticks)]: interpolación lineal. Devuelve t (s desde 0), p, v."""
    t, p, t0, p0 = [0.0], [102.0], 0.0, 102.0
    for pf, seg, n in tramos:
        for k in range(1, n + 1): t.append(t0 + seg * k / n); p.append(p0 + (pf - p0) * k / n)
        t0, p0 = t0 + seg, pf
    return np.array(t), np.array(p), np.ones(len(t))


def _ev(tramos): t, p, v = _serie(tramos); return R.eventos(t, p, v, LO, HI, X, 0.25)


def test_base_y_fresco_lejano():
    e = _ev([(102.0, 60, 30), (130.0, 120, 60), (104.0, 120, 60), (135.0, 60, 30)])       # sale 26 por arriba y vuelve
    assert e["D0_BASE"][2] == 1 and e["D1_FRESCO_LEJANO"][2] == 1 and e["D1_FRESCO_LEJANO"][1] == HI
    e = _ev([(102.0, 60, 30), (114.0, 60, 30), (104.0, 60, 30), (135.0, 60, 30)])         # excursión 10 < X: base sí, lejano no
    assert "D0_BASE" in e and "D1_FRESCO_LEJANO" not in e


def test_fresco_deja_de_contar_tras_mucho_tiempo_adentro():
    e = _ev([(102.0, 700, 200), (130.0, 60, 30), (104.0, 60, 30), (135.0, 60, 30)])       # 700 s negociando adentro antes
    assert "D1_FRESCO_LEJANO" not in e and "D0_BASE" in e


def test_aceptado_y_rechazado_al_nacer_son_excluyentes():
    acep = _ev([(102.5, 200, 200), (101.5, 90, 90), (130.0, 60, 30), (104.0, 300, 60), (140.0, 60, 30)])
    rech = _ev([(130.0, 20, 20), (125.0, 400, 80), (104.0, 120, 60), (140.0, 60, 30)])
    assert "D2_ACEPTADO_Y_ABANDONADO" in acep and "D3_RECHAZADO_AL_NACER" not in acep
    assert "D3_RECHAZADO_AL_NACER" in rech and "D2_ACEPTADO_Y_ABANDONADO" not in rech


def test_memoria_y_deriva():
    e = _ev([(102.0, 30, 15), (130.0, 60, 30), (126.0, 900, 90), (104.0, 400, 200), (135.0, 60, 30)])
    assert "D4_MEMORIA" in e and "D5_DERIVA" in e                                         # 1.360 s afuera; últimos 10 pts en ~180 s
    e = _ev([(102.0, 30, 15), (130.0, 60, 30), (104.0, 5, 5), (135.0, 60, 30)])           # vuelve en 5 s: ni memoria ni deriva
    assert "D4_MEMORIA" not in e and "D5_DERIVA" not in e and "D0_BASE" in e


def test_penetracion_fallida_entra_en_la_salida():
    e = _ev([(102.0, 30, 15), (130.0, 60, 30), (103.5, 30, 30), (106.0, 20, 20), (140.0, 60, 30)])
    j, ref, lado = e["D6_PENETRACION_FALLIDA"]; assert lado == 1 and ref >= HI + 0.5
    e = _ev([(102.0, 30, 15), (130.0, 60, 30), (99.0, 30, 30), (106.0, 20, 20), (140.0, 60, 30)])   # toca el borde lejano
    assert "D6_PENETRACION_FALLIDA" not in e
    e = _ev([(102.0, 30, 15), (130.0, 60, 30), (104.0, 30, 30), (140.0, 60, 30)])        # toca y se va sin entrar: no es penetración
    assert "D6_PENETRACION_FALLIDA" not in e and "D0_BASE" in e


def test_rebotes_del_dia_solo_ticks_posteriores_y_control_lejos():
    rng = np.random.default_rng(5); n = 30000; ts = 1_700_000_000 * S + np.arange(n) * S; px = 20000 + np.cumsum(rng.normal(0, 1.2, n))
    C = pd.DataFrame(dict(t_ns=[int(ts[12000])], lo=[px[12000] - 4], hi=[px[12000] + 4]))
    F = pd.DataFrame(R.rebotes_del_dia("NQ", 20250805, ts, px, np.ones(n), C, 0.25, 1.5455))
    assert set(F.definicion) <= set(R.DEFINICIONES) and set(F.resultado) <= {-1, 0, 1}
    assert F.groupby(["placebo", "definicion"]).size().max() <= 4                       # un evento por cluster y definición
    px2 = px.copy(); px2[:12000] = 0.0                                                    # cambiar el pasado no cambia nada
    F2 = pd.DataFrame(R.rebotes_del_dia("NQ", 20250805, ts, px2, np.ones(n), C, 0.25, 1.5455))
    pd.testing.assert_frame_equal(F[F.placebo == 0].reset_index(drop=True), F2[F2.placebo == 0].reset_index(drop=True))
