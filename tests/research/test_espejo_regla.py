"""La orden del espejo no hereda la mediana clavada ni un objetivo distinto de A."""
from __future__ import annotations

import numpy as np

from edgelab.research import espejo_regla as MOD, grilla_generica as GG, indicadores as IND, preflight as PF, sintetico

T0 = dict(t0_s=MOD.PREFLIGHT_T0_S)


def _ctx(dias=40, planta=False, seed=11):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=planta, seed=seed, **T0), tick=0.25)


def _camino():
    """Impulso 100→130 y vuelta hasta 115 (cruza 0,25 y 0,50; no llega a A). Precios en puntos."""
    tramos = [(100, 12), (130, 6), (115, 8), (115, 5)]
    c = [108.0]
    for dest, n in tramos:
        c += list(np.linspace(c[-1], dest, n + 1)[1:])
    C = np.asarray(c, float)
    O = np.r_[C[0], C[:-1]]
    t0 = MOD.PREFLIGHT_T0_S
    return dict(t=t0 + np.arange(len(C)) * 60.0, o=O, h=np.maximum(O, C), l=np.minimum(O, C), c=C,
                v=np.full(len(C), 10.0), ses=np.zeros(len(C), np.int64), tick=0.25)


def test_causal():
    ctx = _ctx(dias=20)
    assert PF.estatico(MOD) == []
    assert IND.causal(MOD.disparos, ctx) == []
    assert IND.causal_por_disparo(MOD.disparos, ctx, n=15) == []


def test_el_objetivo_es_a_y_el_stop_pasa_b():
    ctx = _camino()
    D = MOD.disparos(ctx)
    assert len(D) >= 1
    assert set(D.x_cat.unique()) <= {0, 1}
    assert set(D.lado.unique()) == {-1}
    nv = MOD.niveles(D.iloc[0].to_dict(), MOD.EJECUCIONES[0], ctx)
    assert nv is not None
    _k, limite, lado, entrada, stop, objetivo, be, kl, dl = nv
    assert limite == 2 and lado == -1 and be == 0 and kl == -1 and dl == 0.0
    assert stop > D.iloc[0].B >= entrada > objetivo
    assert abs(objetivo - D.iloc[0].A) < 1e-9


def test_niveles_lote_igual_a_niveles():
    ctx = _ctx(dias=20)
    D = MOD.disparos(ctx)
    assert len(D) > 0
    assert np.array_equal(GG.ops_por_fila(MOD, D, ctx), GG._ops_lote(MOD, D, ctx), equal_nan=True)


def test_control_ruido():
    ctx = _ctx(dias=40, planta=False, seed=3)
    D = MOD.disparos(ctx)
    di, ei, pnl, _, _ = GG.simular_ops(MOD, D, ctx)
    m = pnl[np.isfinite(pnl)]
    assert len(m) > 30 and float(np.mean(m)) < 2.0
