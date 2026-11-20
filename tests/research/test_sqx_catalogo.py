import numpy as np
import pandas as pd

from edgelab.research import sqx_catalogo as S


def _B(n=900, seed=1, freq="D"):
    rng = np.random.default_rng(seed); t = pd.date_range("2018-01-01", periods=n, freq=freq); t = t[t.dayofweek < 5]
    c = 100 + np.cumsum(rng.normal(0, 1, len(t))); o = np.r_[c[0], c[:-1]] + rng.normal(0, 0.3, len(t))
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.6, len(t))); l = np.minimum(o, c) - np.abs(rng.normal(0, 0.6, len(t)))
    B = pd.DataFrame(dict(o=o, h=h, l=l, c=c, v=np.ones(len(t))), index=t); B["fecha"] = np.asarray(t.strftime("%Y%m%d"), dtype=np.int64); B["dow"] = t.dayofweek
    return B


def _cot(B):
    rng = np.random.default_rng(3); n = len(B); C = pd.DataFrame({k: rng.uniform(0, 1, n) for k in ("spec52", "spec156", "hedg52", "hedg156")})
    for k in list(C.columns): C[k + "_r1"] = np.r_[np.nan, C[k].values[:-1]]; C[k + "_r4"] = np.r_[[np.nan] * 4, C[k].values[:-4]]
    return C


def test_estrategias_causales_por_prefijo():
    B = _B(); ctx = dict(pip=0.01, fric=0.05, cot=_cot(B), poc_dia_previo=np.cumsum(np.random.default_rng(5).normal(0, 1, len(B))))
    corte = len(B) // 2; fecha_corte = B.fecha.iloc[corte]
    for nom, (fn, tf, _) in S.ESTRATEGIAS.items():
        if nom in ("RANGE_1300",): continue
        for var in (False, True):
            a = S.simular(B, fn(B, ctx), var)
            Bp = B.iloc[:corte + 1]; cp = dict(ctx, cot=ctx["cot"].iloc[:corte + 1].reset_index(drop=True), poc_dia_previo=ctx["poc_dia_previo"][:corte + 1])
            b = S.simular(Bp, fn(Bp, cp), var)
            # operaciones cerradas antes del corte deben coincidir (entrada y salida)
            fin = lambda T: T[(T.motivo != "FIN")]
            a2 = fin(a); b2 = fin(b); a2 = a2[a2.fecha < fecha_corte - 100]; b2 = b2[b2.fecha < fecha_corte - 100]
            pd.testing.assert_frame_equal(a2.reset_index(drop=True), b2.reset_index(drop=True), check_dtype=False), nom


def test_motor_stop_antes_que_objetivo_y_gap():
    t = pd.date_range("2024-01-01", periods=7, freq="D")
    B = pd.DataFrame(dict(o=[100, 100, 100, 101, 100, 90, 100.0], h=[101, 101, 101, 112, 101, 91, 101.0], l=[99, 99, 99, 89, 99, 89, 99.0],
                          c=[100, 100, 100, 100, 100, 90, 100.0], v=1.0), index=t)
    B["fecha"] = np.asarray(t.strftime("%Y%m%d"), dtype=np.int64); B["dow"] = 1
    sig = dict(lado=np.array([0, 1, 0, 0, 0, 0, 0]), tipo="mkt", sl=np.full(7, 5.0), tp=np.full(7, 10.0))
    T = S.simular(B, sig, False)                       # entra 100 (vela 2); la vela 3 toca stop 95 y objetivo 110 → stop
    assert T.motivo.iloc[0] == "STOP" and T.salida_px.iloc[0] == 95.0
    sig2 = dict(lado=np.array([0, 0, 0, 1, 0, 0, 0]), tipo="mkt", sl=np.full(7, 3.0), tp=np.full(7, 50.0))
    T2 = S.simular(B, sig2, False)                     # entra 100 (vela 4), stop 97; la vela 5 abre 90 → sale a 90 (hueco)
    assert T2.motivo.iloc[0] == "STOP_GAP" and T2.salida_px.iloc[0] == 90.0


def _escenario(minutos):
    """Barras de 4 minutos M1: barra 0 y 1 planas (la señal va al cierre de la 1), después los minutos dados."""
    filas = [[100, 101, 99, 100]] * 8 + minutos; t = pd.date_range("2024-01-02 02:00", periods=len(filas), freq="1min")
    D = pd.DataFrame(filas, columns=list("ohlc"), index=t, dtype=float); D["v"] = 1.0
    g = np.arange(len(D)) // 4; B = D.groupby(g).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), v=("v", "sum"))
    B.index = t[::4]; B["fecha"] = 20240102; B["dow"] = 1
    m = dict(o=D.o.to_numpy(), h=D.h.to_numpy(), l=D.l.to_numpy(), a=np.arange(len(B)) * 4, b=np.arange(len(B)) * 4 + 4)
    return B, m


def test_m1_resuelve_vela_de_entrada_y_ambiguedad():
    # barra 2: baja a 96 ANTES de tocar el stop de compra 105 y no vuelve; barra 3 llega al objetivo 115
    B, m = _escenario([[100, 100, 96, 97], [97, 101, 97, 101], [101, 104, 101, 104], [104, 106, 104, 105],
                       [105, 107, 104, 106], [106, 109, 105, 108], [108, 112, 107, 112], [112, 116, 111, 115]])
    n = len(B); sig = dict(lado=np.r_[0, 1, np.zeros(n - 2)], tipo="stop", px=np.full(n, 105.0), sl=np.full(n, 8.0), tp=np.full(n, 10.0), valida=3)
    sin = S.simular(B, sig, False); con = S.simular(B, sig, False, m1=m)
    assert sin.motivo.iloc[0] == "STOP" and sin.barras.iloc[0] == 1          # OHLC: el mínimo 96 cuenta como posterior (lo peor)
    assert con.motivo.iloc[0] == "OBJ" and con.salida_px.iloc[0] == 115.0   # M1: entra 105 en el último minuto de la barra 2, objetivo en la 3
    # barra que toca stop y objetivo: el M1 decide el orden (primero el objetivo)
    B2, m2 = _escenario([[100, 100, 99.5, 100], [100, 104.5, 100, 104], [104, 104, 96, 97], [97, 101, 97, 100]])
    sig2 = dict(lado=np.r_[0, 1, np.zeros(len(B2) - 2)], tipo="mkt", sl=np.full(len(B2), 4.0), tp=np.full(len(B2), 4.0))
    assert S.simular(B2, sig2, False).motivo.iloc[0] == "STOP"               # sin M1: stop (lo peor)
    T = S.simular(B2, sig2, False, m1=m2)                                    # entra 100 a la apertura de la barra 2: objetivo 104 en su 2.º minuto
    assert T.motivo.iloc[0] == "OBJ" and T.salida_px.iloc[0] == 104.0 and T.barras.iloc[0] == 1


def test_turtle_v_de_fabrica_igual_a_turtle_y_causal():
    B = _B(n=1400); ctx = {}
    for var in (False, True):
        a = S.simular(B, S.turtle(55, 20, True)(B, ctx), var).drop(columns="i0")
        b = S.simular(B, S.turtle_v()(B, ctx), var).drop(columns="i0")
        pd.testing.assert_frame_equal(a, b, check_dtype=False)
    corte = 900; fc = B.fecha.iloc[corte]
    for kw in (dict(entrada="stop"), dict(tend=False), dict(vol=False, n_in=20), dict(cortos=False)):
        for reent in (False, True):
            def corre(Bx):
                s = S.turtle_v(**kw)(Bx, ctx); s = S.con_reentrada(Bx, s) if reent else s
                T = S.simular(Bx, s, True); return T[(T.motivo != "FIN") & (T.fecha < fc - 100)].drop(columns="i0").reset_index(drop=True)
            pd.testing.assert_frame_equal(corre(B), corre(B.iloc[:corte + 1]), check_dtype=False)


def _caminata_m1(seed, dias=120):
    rng = np.random.default_rng(seed); t = pd.date_range("2024-01-01 18:00", periods=60 * 24 * dias, freq="1min"); t = t[t.dayofweek < 5]
    c = 100 + np.cumsum(rng.normal(0, 0.3, len(t))); o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.1, len(t))); l = np.minimum(o, c) - np.abs(rng.normal(0, 0.1, len(t)))
    return pd.DataFrame(dict(o=o, h=h, l=l, c=c, v=1.0), index=t), rng


def _r_al_azar(D, rng, k, con_m1):
    B = S.barras_desde_m1(D, "M15"); m = S.indices_m1(B, D, "M15") if con_m1 else None; n = len(B)
    on = rng.random(n) < 0.3; a = (B.h - B.l).rolling(20).mean().to_numpy()
    sig = dict(lado_l=np.where(on, 1, 0), lado_s=np.where(on, -1, 0), tipo_l="stop", tipo_s="stop", px_l=B.h.to_numpy(), px_s=B.l.to_numpy(),
               valida=1, sl=k * a, tp=k * a)
    T = S.simular(B, sig, True, m1=m); return (T.lado * (T.salida_px - T.entrada) / (T.entrada - T.stop0).abs()).to_numpy()


def test_calibracion_motor_barras():
    """K28: OCO de rupturas al azar sobre una caminata sin deriva. Con el M1 y stops de 1 rango medio de barra, R medio ≈ 0; sin M1 y con
    stops chicos el motor es PESIMISTA (el extremo previo al llenado cuenta como posterior: −0,5 R), el sesgo de la corrida v1 del catálogo."""
    medias = []
    for seed in (3, 4, 5):
        D, rng = _caminata_m1(seed); medias.append(_r_al_azar(D, rng, 1.0, True).mean())
    assert abs(np.mean(medias)) < 0.05, medias
    D, rng = _caminata_m1(3); assert _r_al_azar(D, rng, 0.3, False).mean() < -0.3
