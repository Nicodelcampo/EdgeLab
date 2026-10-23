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
