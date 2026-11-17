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


def test_orb_ema20_vela_de_entrada_solo_stop():
    ctx = _ctx(30, 3); R = X.orb_ema20(ctx)
    assert len(R) and (R[R.motivo == 2].bruto > 0).all() and (R[R.motivo == 1].bruto < 0).all()


def test_reels_20261116_causal_por_prefijo():
    """Las operaciones de un día no cambian si se corta el feed al terminar ese día (nada mira el futuro)."""
    ctx = _ctx(140, 5); corte = ctx["t"][len(ctx["t"]) // 2]
    pre = {k: (v[ctx["t"] <= corte] if isinstance(v, np.ndarray) else v) for k, v in ctx.items()}
    dia_corte = int(pd.to_datetime(corte - 60, unit="s", utc=True).tz_convert("America/New_York").strftime("%Y%m%d"))
    for fn in (X.viernes_lunes, X.dos_velas, X.franklin):
        a, b = fn(ctx), fn(pre)
        assert len(a), fn.__name__
        a = a[a.fecha < dia_corte].reset_index(drop=True)
        if not len(b): assert not len(a), fn.__name__; continue
        b = b[b.fecha < dia_corte].reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b)


def test_viernes_lunes_solo_ventas_y_e0():
    R = X.viernes_lunes(_ctx(200, 7))
    assert len(R) and (R.lado == -1).all() and (R.bruto >= -R.riesgo - 1e-9).all()
    V = X.visitas_hougaard(_ctx(60, 7))
    assert {"menor", "dentro", "visita"} <= set(V.columns) and V.visita.dtype == bool


def test_franklin_variantes_causal_y_base_coincide():
    ctx = _ctx(140, 9)
    R = X.franklin_variantes(ctx)
    assert len(R) and set(map(tuple, R.celda)) <= set(X.FRV_CELDAS) and (R.riesgo > 0).all()
    corte = ctx["t"][len(ctx["t"]) // 2]
    pre = {k: (v[ctx["t"] <= corte] if isinstance(v, np.ndarray) else v) for k, v in ctx.items()}
    dia = int(pd.to_datetime(corte - 60, unit="s", utc=True).tz_convert("America/New_York").strftime("%Y%m%d"))
    a = R[R.fecha < dia].reset_index(drop=True); b = X.franklin_variantes(pre); b = b[b.fecha < dia].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
    # la celda (1000, rango, ninguno) es la regla base FRANKLIN «cierre» (salvo los primeros 20 días sin ATR)
    base = X.franklin(ctx); base = base[base.celda.map(tuple) == ("cierre",)].set_index("fecha")
    v = R[R.celda.map(tuple) == ("1000", "rango", "ninguno")].set_index("fecha")
    comun = v.index.intersection(base.index)
    assert len(comun) and np.allclose(v.loc[comun, "bruto"], base.loc[comun, "bruto"])


def test_leer_m1_russell_en_utc_y_resto_en_hora_servidor(tmp_path):
    """2026-11-16: el CSV de Russell viene en UTC; los *_M1_dukas en NY + 7. Las 14:30 UTC de enero son las 09:30 NY; las 13:30 UTC de julio también."""
    from edgelab.research import m1_intradia as M
    txt = "Date,Time,Open,High,Low,Close,Volume\n20240110,14:30:00,1,2,0.5,1.5,10\n20240710,13:30:00,1,2,0.5,1.5,10\n"
    (tmp_path / "USSC2000IDXUSD.csv").write_text(txt); (tmp_path / "SP_M1_dukas.csv").write_text(txt.replace("14:30", "16:30").replace("13:30", "16:30"))
    r = M.leer_m1(tmp_path / "USSC2000IDXUSD.csv"); s = M.leer_m1(tmp_path / "SP_M1_dukas.csv")
    assert [(t.hour, t.minute) for t in r.index] == [(9, 30), (9, 30)]
    assert [(t.hour, t.minute) for t in s.index] == [(9, 30), (9, 30)]


def test_zona_m1_declarada_y_listas_iguales():
    """Auditoría 2026-11-16: toda fuente M1 declara su zona; las dos listas de archivos en UTC son la misma."""
    import pytest
    from edgelab.research import m1_intradia as M, fuentes_ticks as FT
    assert tuple(M.EN_UTC) == tuple(FT.M1_EN_UTC)
    assert M.zona_m1("DEUIDXEUR-M1-.csv") == "UTC" and M.zona_m1("NQ_M1_dukas-M1-.csv") == "SERVIDOR"
    with pytest.raises(ValueError): M.zona_m1("CUALQUIERA.csv")
