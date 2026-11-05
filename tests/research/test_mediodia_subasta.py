"""Tests de causalidad (cortes fijos y corte exacto en cada vela de disparo), preflight estático e invariantes de MEDIODIA-SUBASTA."""
from __future__ import annotations

import numpy as np

from edgelab.research import mediodia_subasta as MOD, grilla_generica as GG, indicadores as IND, preflight as PF, sintetico

T0 = dict(t0_s=getattr(MOD, "PREFLIGHT_T0_S", 1_760_047_200))


def _ctx(dias: int = 15):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=7, **T0), tick=0.25)


def test_causal():
    ctx = _ctx(dias=15)
    assert PF.estatico(MOD) == []
    assert IND.causal(MOD.disparos, ctx) == []
    assert IND.causal_por_disparo(MOD.disparos, ctx) == []


def test_disparos_y_niveles():
    ctx = _ctx(dias=15)
    D = MOD.disparos(ctx)
    assert len(D) > 0 and set(MOD.VACIO) <= set(D.columns) and set(D.lado.unique()) <= {-1, 1}
    assert 50 <= GG.n_celdas(MOD) <= 250
    O1 = GG.ops_por_fila(MOD, D, ctx)
    O2 = GG._ops_lote(MOD, D, ctx)
    assert O1.shape == O2.shape and np.array_equal(O1, O2, equal_nan=True)
    for ej in MOD.EJECUCIONES:
        O = MOD.niveles_lote(D, ej, ctx)
        s, e, st, tp = O[:, 2], O[:, 3], O[:, 4], O[:, 5]
        assert ((st - e) * s < 0).all() and ((tp - e) * s > 0).all()
        assert (np.abs(e - st) >= 3.99 * ctx["tick"]).all()
        nv0 = MOD.niveles(D.iloc[0].to_dict(), ej, ctx)
        assert nv0 is not None and np.allclose(O[0, :len(nv0)], nv0)
