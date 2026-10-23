"""U1-CRUZADO: señal en USATECH, operación en NQ. Oráculo (misma serie = U1 propio), invariancia a la base, minutos faltantes."""
import numpy as np
import pytest

from edgelab.research import areas_expansion as AX, grilla_generica as GG, u1_cruzado as X, u1_indaga as U
from tests.research.test_u1_indaga import _bloques


@pytest.fixture(scope="module")
def ctx():
    return GG.contexto_m1(_bloques(dias=60, planta=True, seed=7), tick=0.25)


def test_misma_serie_reproduce_u1_propio(ctx):
    F = X.operar(ctx, ctx); S = X.senales(ctx)
    assert len(S) > 5 and F.base.dropna().eq(0).all()
    for i, (en, ob, sl) in enumerate(X.EJECUCIONES):
        g = F[(F.ejecucion == f"{en}/{ob}/{sl}") & F.motivo.eq("")]
        ref = [U.niveles(r, (en, ob, sl, 0), ctx) for r in S.to_dict("records")]
        ref = [x for x in ref if x is not None]
        st0, lim, s, e, st, tp, be = (np.array(v) for v in zip(*ref))
        pnl, _ = AX.simular(st0.astype(np.int64), s.astype(np.int64), lim.astype(np.int64), e, st, tp, be.astype(np.int64),
                            ctx["o"], ctx["h"], ctx["l"], ctx["c"], ctx["ses"], 0.25, ctx["tpx"], ctx["tstart"])
        assert np.allclose(np.sort(g.bruto.to_numpy()), np.sort(pnl), equal_nan=True)


def test_invariante_a_una_base_constante(ctx):
    nq = dict(ctx); off = 100.0
    for k in ("o", "h", "l", "c", "tpx"): nq[k] = ctx[k] + off
    a, b = X.operar(ctx, ctx), X.operar(ctx, nq)
    assert b.base.dropna().eq(off).all() and np.allclose(a.bruto.to_numpy(), b.bruto.to_numpy(), equal_nan=True)


def test_minuto_sin_nq_no_se_opera(ctx):
    nq = dict(ctx); nq["t"] = ctx["t"] + 30                                      # ningún minuto coincide
    F = X.operar(ctx, nq)
    assert F.motivo.eq("sin vela NQ en ese minuto").all() and F.bruto.isna().all()


def test_retraso_cero_es_identico_y_retraso_no_mira_el_futuro(ctx):
    a, b = X.operar(ctx, ctx), X.operar(ctx, ctx, retraso=0)
    assert np.allclose(a.bruto.to_numpy(), b.bruto.to_numpy(), equal_nan=True)
    c = X.operar(ctx, ctx, retraso=2)
    ok = c.motivo.eq("")
    assert (c[ok].j_nq.to_numpy() >= 2).all() and set(c.motivo) <= {"", "resolvió antes de entrar", "niveles no válidos en NQ", "retraso fuera de la sesión", "sin vela NQ en ese minuto"}


def test_placebo_con_ruido_no_gana():
    nz = GG.contexto_m1(_bloques(dias=60, planta=False, seed=9), tick=0.25)
    P = X.placebo(nz, nz, seed=1)
    assert len(P) > 10 and np.nanmean(P.bruto) < 2.0                           # sin contenido: ~0 bruto (la fricción lo deja negativo)


def test_alineacion_detecta_un_desfasaje_plantado():
    import pandas as pd
    rng = np.random.default_rng(0); n = 20000; ts = (1_790_000_000 + np.arange(n)) * 10**9
    p = 20000 + np.cumsum(rng.normal(0, 1, n))
    us = [pd.DataFrame(dict(ts_ns=ts, px=p))]
    nq = [pd.DataFrame(dict(ts_ns=ts + 3 * 10**9, px=p + 100))]               # NQ 3 s detrás del CFD
    r = X.alineacion_segundos(iter(us), iter(nq))
    assert r["pico_lag_s"] == 3 and "revisar" in r["lectura"]
    r0 = X.alineacion_segundos(iter(us), iter([pd.DataFrame(dict(ts_ns=ts, px=p + 100))]))
    assert r0["pico_lag_s"] == 0


def test_tope_nunca_afloja_y_none_es_el_original(ctx):
    assert X.aplicar_tope(100.0, 1, 40.0, 110.0, None, 0.25) == 40.0
    assert X.aplicar_tope(100.0, 1, 40.0, 110.0, ("pts", 30.0), 0.25) == 70.0               # largo: stop sube a entrada − 30
    assert X.aplicar_tope(100.0, -1, 160.0, 90.0, ("mult", 2.0), 0.25) == 120.0             # corto: 2 × distancia al objetivo (10)
    assert X.aplicar_tope(100.0, 1, 95.0, 110.0, ("pts", 30.0), 0.25) == 95.0               # ya estaba más cerca: no cambia
    a, b = X.operar(ctx, ctx), X.operar(ctx, ctx, tope=None)
    assert np.allclose(a.bruto.to_numpy(), b.bruto.to_numpy(), equal_nan=True)
    c = X.operar(ctx, ctx, tope=("pts", 5.0))
    ok = c.motivo.eq("")
    assert (np.abs(c[ok].entrada_plan - c[ok].stop) <= 5.0 + 1e-9).all()
    assert np.nanmin(c.bruto) >= -5.0 - 60                                      # pérdida acotada salvo hueco


def test_conductor_generico_reproduce_u1_cruzado(ctx):
    """Oráculo: la ejecución cruzada genérica (grilla_generica.simular_ops con cx_ej) = u1_cruzado.operar (validado a mano)."""
    import types
    nq = dict(ctx); off = 37.0
    for k in ("o", "h", "l", "c", "tpx"): nq[k] = ctx[k] + off
    S = X.senales(ctx).reset_index(drop=True)
    exp = types.SimpleNamespace(EJECUCIONES=[("E1A", "T1", "S3", 0), ("E1A", "T3", "S3", 0)], niveles=U.niveles)
    for kw in (dict(), dict(retraso=2), dict(tope=("mult", 3.0))):
        di, ei, pnl, _, _ = GG.simular_ops(exp, S, ctx, cx_ej=nq, **kw)
        ref = X.operar(ctx, nq, S, **kw)
        for e, (en, ob, sl, _b) in enumerate(exp.EJECUCIONES):
            a = np.sort(pnl[(ei == e) & np.isfinite(pnl)]); b = np.sort(ref[(ref.ejecucion == f"{en}/{ob}/{sl}")].bruto.dropna().to_numpy())
            assert np.allclose(a, b), (kw, e, len(a), len(b))
