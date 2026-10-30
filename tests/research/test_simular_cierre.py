"""Barras de llenado y salida de cada operación (para un freno diario por hora real de cierre), sin mover pnl ni amb."""
import numpy as np
import pytest

from edgelab.research import areas_expansion as AX, grilla_generica as GG, u1_indaga as U
from tests.research.test_u1_indaga import _bloques

VARIANTES = [pytest.param(AX.simular_cierre, id="numba"), pytest.param(getattr(AX.simular_cierre, "py_func", AX.simular_cierre), id="python")]


def _velas(n=30):
    c = np.full(n, 100.0)
    return c.copy(), c + .5, c - .5, c, np.zeros(n, np.int64)


def _op(impl, velas, start=5, s=1, lim=0, nivel=100.0, st=90.0, tp=110.0, be=0, tpx=None, tstart=None):
    o, h, l, c, ses = velas
    if tpx is None: tpx, tstart = np.zeros(0), np.zeros(len(c) + 1, np.int64)
    i = lambda v: np.array([v], np.int64); a = lambda v: np.array([v], float)
    p, am, f, x = impl(i(start), i(s), i(lim), a(nivel), a(st), a(tp), i(be), o, h, l, c, ses, 1.0, tpx, tstart)
    return p[0], am[0], f[0], x[0]


@pytest.mark.parametrize("impl", VARIANTES)
def test_llenado_inmediato_y_salida_por_stop(impl):
    v = _velas(); v[2][8] = 89.0
    p, _, f, x = _op(impl, v)
    assert (f, x, p) == (5, 8, -10.0)


@pytest.mark.parametrize("impl", VARIANTES)
def test_salida_por_objetivo(impl):
    v = _velas(); v[1][9] = 112.0
    p, _, f, x = _op(impl, v)
    assert (f, x, p) == (5, 9, 10.0)


@pytest.mark.parametrize("impl", VARIANTES)
def test_salida_por_tiempo_cuenta_240_barras(impl):
    p, _, f, x = _op(impl, _velas(300))
    assert (f, x, p) == (5, 245, 0.0)


@pytest.mark.parametrize("impl", VARIANTES)
def test_salida_por_fin_de_sesion_es_la_ultima_vela_de_la_sesion(impl):
    v = _velas(); v[4][20:] = 1
    assert _op(impl, v)[2:] == (5, 19)


@pytest.mark.parametrize("impl", VARIANTES)
def test_limite_que_llena_tarde(impl):
    v = _velas(); v[2][12] = 95.0; v[1][15] = 112.0
    p, _, f, x = _op(impl, v, lim=1, nivel=97.0)
    assert (f, x, p) == (12, 15, 13.0)


@pytest.mark.parametrize("impl", VARIANTES)
def test_limite_sin_llenado(impl):
    p, _, f, x = _op(impl, _velas(), lim=1, nivel=97.0)
    assert np.isnan(p) and (f, x) == (-1, -1)


@pytest.mark.parametrize("impl", VARIANTES)
def test_limite_que_sale_en_la_vela_del_llenado(impl):
    v = _velas(); v[2][12] = 89.0
    p, am, f, x = _op(impl, v, lim=1, nivel=97.0)
    assert (f, x, p, am) == (12, 12, -7.0, 2)


@pytest.mark.parametrize("impl", VARIANTES)
def test_tick_siguiente_llena_en_k_mas_1_y_sale_por_ticks_en_esa_vela(impl):
    tstart = np.zeros(31, np.int64); tstart[7:] = 2
    p, am, f, x = _op(impl, _velas(), lim=2, tpx=np.array([100.0, 89.0]), tstart=tstart)
    assert (f, x, p, am) == (6, 6, -11.0, 1)


@pytest.mark.parametrize("impl", VARIANTES)
def test_tick_siguiente_en_otra_sesion_no_llena(impl):
    v = _velas(); v[4][6:] = 1
    p, _, f, x = _op(impl, v, lim=2)
    assert np.isnan(p) and (f, x) == (-1, -1)


@pytest.mark.parametrize("impl", VARIANTES)
def test_vela_ambigua_sale_en_esa_vela(impl):
    v = _velas(); v[1][9] = 112.0; v[2][9] = 89.0
    p, am, f, x = _op(impl, v)
    assert (f, x, am) == (5, 9, 2) and p == -10.0


def _lote(n=4000, seed=3):
    r = np.random.default_rng(seed); m = 3000
    c = 1000 + np.round(np.cumsum(r.normal(0, 2, m)) * 4) / 4
    o = np.r_[c[0], c[:-1]]; h = np.maximum(o, c) + r.integers(0, 12, m) / 4; l = np.minimum(o, c) - r.integers(0, 12, m) / 4
    ses = np.arange(m, dtype=np.int64) // 400
    tpx = np.column_stack([o, l, h, c]).ravel(); tstart = np.arange(m + 1, dtype=np.int64) * 4
    tstart[1000:1500] = tstart[1000]; tstart[1500:] -= 2000                 # un tramo sin ticks
    tpx = np.r_[tpx[:4000], tpx[6000:]]
    k = r.integers(0, m - 2, n).astype(np.int64); s = r.choice([-1, 1], n).astype(np.int64); lim = r.integers(0, 3, n).astype(np.int64)
    e = c[k] - s * lim * (lim == 1) * r.integers(1, 40, n) / 4
    return k, s, lim, e, e - s * r.integers(4, 60, n) / 4, e + s * r.integers(4, 60, n) / 4, r.integers(0, 2, n).astype(np.int64), o, h, l, c, ses, .25, tpx, tstart


def test_pnl_identico_al_de_simular_y_entre_variantes():
    A = _lote(); p0, a0 = AX.simular(*A); p1, a1, f1, x1 = AX.simular_cierre(*A)
    p2, a2, f2, x2 = getattr(AX.simular_cierre, "py_func", AX.simular_cierre)(*A)
    assert np.array_equal(p0, p1, equal_nan=True) and np.array_equal(p0, p2, equal_nan=True)
    assert np.array_equal(a0, a1) and np.array_equal(a0, a2) and np.array_equal(f1, f2) and np.array_equal(x1, x2)
    lleno = f1 >= 0
    assert np.array_equal(lleno, np.isfinite(p0)) and (x1[~lleno] == -1).all() and (x1[lleno] >= f1[lleno]).all() and (f1[lleno] >= A[0][lleno]).all()
    assert (x1[lleno] - f1[lleno]).max() <= 240 and (A[11][x1[lleno]] == A[11][f1[lleno]]).all()


def _anteponer(ctx, K):
    """El mismo mercado con K velas previas: los índices de ejecución dejan de coincidir con los del sensor."""
    ej = dict(ctx); pre = np.full(K, ctx["c"][0])
    for c in "ohlc": ej[c] = np.r_[pre, ctx[c]]
    ej["ses"] = np.r_[np.full(K, ctx["ses"][0] - 1), ctx["ses"]]; ej["t"] = np.r_[ctx["t"][0] - 60 * np.arange(K, 0, -1), ctx["t"]]
    ej["tstart"] = np.r_[np.zeros(K, np.int64), ctx["tstart"]]
    return ej


def test_operaciones_de_informa_horas_en_el_espacio_de_ejecucion():
    ctx = GG.contexto_m1(_bloques(dias=20, planta=True, seed=5), tick=0.25)
    cortes = GG.cortes_e0(U.disparos(ctx), U.VARIABLES); celda = [0, 1, 0, 2, 2, 2, 3, 3, 3, 0]
    kw = dict(modo="REP", friccion=1.0, extra_adverso=0.5, cortes=cortes, celdas=[celda], log=lambda s: None)
    _, cx = GG.correr(U, ctx, **kw); ops = GG.operaciones_de(cx, [celda])
    assert len(ops) and ops[["t_fill", "t_exit"]].notna().all(axis=None)
    assert (ops.t_fill >= ops.t).all() and (ops.t_exit >= ops.t_fill).all() and (ops.t_exit > ops.t_fill).any()
    assert np.isin(ops.t_fill, ctx["t"]).all() and np.isin(ops.t_exit, ctx["t"]).all()
    _, cx2 = GG.correr(U, ctx, cx_ej=_anteponer(ctx, 37), **kw); ops2 = GG.operaciones_de(cx2, [celda])
    assert ops2.equals(ops)
