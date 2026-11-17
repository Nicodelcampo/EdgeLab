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
