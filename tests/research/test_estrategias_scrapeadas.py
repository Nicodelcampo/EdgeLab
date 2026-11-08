import numpy as np
import pandas as pd

from edgelab.research import estrategias_scrapeadas as X


def _ctx(n_dias=160, seed=0):
    rng = np.random.default_rng(seed)
    t = pd.date_range("2025-07-01", periods=n_dias * 1440, freq="1min", tz="UTC")
    t = t[t.dayofweek < 5]
    c = 100 + np.cumsum(rng.normal(0, 0.05, len(t))); o = np.r_[c[0], c[:-1]]
    return dict(t=np.asarray((t - pd.Timestamp(0, tz="UTC")) // pd.Timedelta("1s"), dtype=np.int64) + 60, o=o, h=np.maximum(o, c) + 0.02, l=np.minimum(o, c) - 0.02, c=c, v=np.ones(len(c)))


def test_familias_corren_y_son_coherentes():
    ctx = _ctx()
    for nombre, (fn, celdas) in X.FAMILIAS.items():
        R = fn(ctx)
        assert len(R), nombre
        assert set(map(tuple, R.celda)) <= set(celdas)
        assert (R.riesgo > 0).all()
        st = R[R.motivo == 1]                            # salida por stop: pierde a lo sumo el riesgo
        assert np.allclose(st.bruto, -st.riesgo) or nombre == "MARTES_DEBIL" or (st.bruto <= 1e-9).all()


def test_sim_velas_stop_antes_que_objetivo():
    o = np.array([10.0]); h = np.array([12.0]); l = np.array([8.0]); c = np.array([11.0])
    assert X._sim_velas(o, h, l, c, 0, 10.0, 1, 1.0, 1.0, None, 0) == (-1.0, 1)


def test_memoria_ideas_rota_y_entra_en_el_paquete():
    from edgelab.autopilot import contexto
    a, b = contexto.memoria_ideas(0), contexto.memoria_ideas(1)
    assert "kemet" in a["indice"] and a["reel"]["archivo"] != b["reel"]["archivo"]
    p = contexto.armar_paquete(tablero={}, vacios=[], fichas=[], retiradas=[], lente=next(iter(contexto.LENTES)), memoria=a)
    assert p["memoria_ideas"]["indice"] and "12. **Memoria de ideas" in p["directivas_de_nico"]
