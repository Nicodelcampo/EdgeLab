"""Familias del plan del paquete del 2026-10-31 (TAU-TENDENCIA, EOD-MOM, RANGO-ASIA0100, RANGO-PREAPERTURA) y `regimen_sesion`:
preflight estático, causalidad, paridad lote/escalar, control de ruido y control con el efecto plantado."""
from __future__ import annotations

import numpy as np
import pytest

from edgelab.research import (eod_momentum as EOD, grilla_generica as GG, indicadores as IND, preflight as PF, rango_asia0100 as RA,
                              rango_preapertura as RP, regimen_sesion as RS, tau_tendencia as TAU)

MODULOS = (TAU, EOD, RA, RP)
T0 = 1754344800                                   # 2025-08-04 22:00 UTC = 18:00 ET (apertura de la sesión CME del 5-ago)


def ctx_sintetico(dias=60, seed=0, phi=0.0, eod=0.0, ruptura=0.0, tick=0.25):
    """M1 de 23 h por sesión con hora NY real. `phi`: autocorrelación de los retornos (tendencias). `eod`: deriva de la última
    media hora a favor del signo de la primera media hora. `ruptura`: deriva de 30 velas tras el primer cierre fuera del rango
    01:00–01:15 y 09:15–09:30 ET, a favor del quiebre."""
    rng = np.random.default_rng(seed); n_s = 1380; filas = []
    p = 20000.0
    for d in range(dias):
        t = T0 + d * 86400 + 60 * np.arange(1, n_s + 1); m = RS.minuto_ny(t)
        r = rng.normal(0, 1.0, n_s)
        for i in range(1, n_s): r[i] += phi * r[i - 1]
        if eod:
            a = int(np.flatnonzero(m == 571)[0]); b = int(np.flatnonzero(m == 600)[0]); z = np.flatnonzero((m > 930) & (m <= 960))
            r[z] += eod * np.sign(r[a:b + 1].sum())
        c = p + np.cumsum(r)
        if ruptura:
            for ini, fin in ((60, 75), (555, 570)):
                rg = np.flatnonzero((m > ini) & (m <= fin)); hi, lo = c[rg].max(), c[rg].min()
                for k in np.flatnonzero((m > fin) & (np.arange(n_s) > rg[-1])):
                    if c[k] > hi or c[k] < lo:
                        s = 1.0 if c[k] > hi else -1.0; c[k + 1:k + 31] += s * ruptura * np.arange(1, 31); c[k + 31:] += s * ruptura * 30
                        break
        c = np.round(c / tick) * tick; o = np.r_[p, c[:-1]]
        h = np.maximum(o, c) + tick * rng.integers(0, 3, n_s); l = np.minimum(o, c) - tick * rng.integers(0, 3, n_s)
        filas.append((t, o, h, l, c, rng.integers(50, 150, n_s).astype(float), np.full(n_s, d, np.int64))); p = c[-1]
    t, o, h, l, c, v, ses = (np.concatenate(x) for x in zip(*filas))
    return dict(t=t, o=o, h=h, l=l, c=c, v=v, ses=ses, tick=tick, tpx=np.zeros(0), tstart=np.zeros(len(c) + 1, np.int64))


_C = {}


def _ctx(**kw):
    k = tuple(sorted(kw.items()))
    if k not in _C: _C[k] = ctx_sintetico(**kw)
    return _C[k]


def _media(mod, ctx, ejecuciones=None):
    D = mod.disparos(ctx).reset_index(drop=True)
    di, ei, pnl, _, _ = GG.simular_ops(mod, D, ctx)
    sel = np.ones(len(ei), bool) if ejecuciones is None else np.isin(ei, ejecuciones)
    return float(np.nanmean(pnl[sel])), int(np.isfinite(pnl[sel]).sum())


def test_er_sesion_corta_en_la_sesion_y_minuto_ny():
    c = np.r_[np.arange(10.0), 100 + np.arange(10.0)]; ses = np.r_[np.zeros(10, np.int64), np.ones(10, np.int64)]
    er = RS.er_sesion(c, ses, 5)
    assert np.isnan(er[:5]).all() and np.isnan(er[10:15]).all() and np.allclose(er[5:10], 1.0) and np.allclose(er[15:], 1.0)
    assert RS.minuto_ny(np.array([T0]))[0] == 18 * 60                     # EDT
    assert RS.minuto_ny(np.array([T0 + 120 * 86400]))[0] == 17 * 60       # diciembre: EST, 22:00 UTC = 17:00


@pytest.mark.parametrize("mod", MODULOS, ids=lambda m: m.NOMBRE)
def test_preflight_estatico(mod):
    assert PF.estatico(mod) == []


@pytest.mark.parametrize("mod", MODULOS, ids=lambda m: m.NOMBRE)
def test_causal(mod):
    assert IND.causal(mod.disparos, _ctx(dias=12, seed=1)) == []


@pytest.mark.parametrize("mod", MODULOS, ids=lambda m: m.NOMBRE)
def test_niveles_lote_identico_a_niveles(mod):
    ctx = _ctx(dias=12, seed=1); D = mod.disparos(ctx)
    assert len(D) > 0
    O1 = GG.ops_por_fila(mod, D, ctx); O2 = GG._ops_lote(mod, D, ctx)
    assert O1.shape == O2.shape and O1.shape[1] == 11 and np.array_equal(O1, O2, equal_nan=True)


def test_tau_control_ruido_y_plantado():
    tau = [i for i, e in enumerate(TAU.EJECUCIONES) if e[0] == "TAU"]
    m0, n0 = _media(TAU, _ctx(dias=20, seed=3), tau)
    m1, _ = _media(TAU, _ctx(dias=20, seed=3, phi=0.5), tau)
    assert n0 > 500 and abs(m0) < 1.5 and m1 > m0 + 1.0, (m0, m1)


def test_eod_control_ruido_y_plantado():
    m0, n0 = _media(EOD, _ctx(dias=60, seed=5))
    m1, _ = _media(EOD, _ctx(dias=60, seed=5, eod=0.6))
    assert n0 > 100 and abs(m0) < 2.0 and m1 > m0 + 2.0, (m0, m1)


@pytest.mark.parametrize("mod", (RA, RP), ids=lambda m: m.NOMBRE)
def test_rango_control_ruido_y_plantado(mod):
    m0, n0 = _media(mod, _ctx(dias=60, seed=7))
    m1, _ = _media(mod, _ctx(dias=60, seed=7, ruptura=0.5))
    assert n0 > 100 and abs(m0) < 2.0 and m1 > m0 + 2.0, (m0, m1)


def test_eod_sale_a_las_1559():
    ctx = _ctx(dias=12, seed=1); D = EOD.disparos(ctx)
    r = GG.simular_ops(EOD, D, ctx, devolver_barras=True); fb, xb = r[-2], r[-1]; m = RS.minuto_ny(ctx["t"])
    ok = fb >= 0
    assert (m[fb[ok]] == 931).all() and (m[xb[ok]] <= 960).all()


def test_tau_linea_no_mira_el_futuro():
    """La línea de la vela j sólo usa pivotes confirmados hasta j: truncar la serie no cambia las líneas ya calculadas."""
    ctx = _ctx(dias=6, seed=2); n = len(ctx["c"]) // 2
    L = TAU.lineas_salida(dict(ctx))
    corto = {k: (v[:n] if k in ("t", "o", "h", "l", "c", "v", "ses") else v) for k, v in ctx.items()}
    L2 = TAU.lineas_salida(corto)
    assert np.array_equal(L[:, :n], L2, equal_nan=True)


def test_salida_por_linea_no_admite_otro_instrumento():
    ctx = _ctx(dias=6, seed=2); D = EOD.disparos(ctx)
    with pytest.raises(ValueError, match="otro instrumento"):
        GG.simular_ops(EOD, D, ctx, cx_ej=ctx)


def test_variante_tau_original_identica_y_celdas():
    from edgelab.research import corredor_vol_gaps as B, variante_tau as VT, vtau_cvgap as V, sintetico
    ctx = GG.contexto_m1(sintetico.bloques(dias=20, planta=False, seed=4), tick=0.25)
    D = V.disparos(ctx).reset_index(drop=True)
    assert len(D) > 0 and len(V.EJECUCIONES) == 4 * len(B.EJECUCIONES) and V.VARIABLES == B.VARIABLES
    r0 = GG.simular_ops(B, D, ctx); r1 = GG.simular_ops(V, D, ctx)
    assert np.array_equal(r0[2], r1[2][r1[1] % 4 == 0], equal_nan=True)            # la variante ORIGINAL es el experimento base
    assert VT.celda_variante([1, 2, 5], 3) == [1, 2, 23]
    O1 = GG.ops_por_fila(V, D.head(100), ctx); O2 = GG._ops_lote(V, D.head(100), ctx)
    assert np.array_equal(O1, O2, equal_nan=True)
