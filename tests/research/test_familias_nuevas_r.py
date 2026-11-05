"""Familias nuevas del programa R (docs/research/programa_r_20261103/DISENO_FAMILIAS_NUEVAS.md): causalidad (cortar los datos en la
vela de cada disparo no lo cambia) y forma de las salidas, con datos sintéticos."""
import numpy as np
import pytest

from edgelab.research import grilla_generica as GG, indicadores as IND, lead_lag as LL, par_relativo as PR, sintetico, vwap_rev as VR

T0 = dict(t0_s=1754352000)          # 2025-08-05 00:00 UTC: velas alineadas con sesiones CME


def _ctx(conf=False, dias=12):
    c = GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=3, **T0), tick=0.25)
    if conf: c["conf"] = GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=4, **T0), tick=0.25)
    return c


@pytest.mark.parametrize("mod,conf", [(PR, True), (LL, True), (VR, False)])
def test_causal(mod, conf):
    ctx = _ctx(conf)
    assert IND.causal(mod.disparos, ctx) == []
    assert IND.causal_por_disparo(mod.disparos, ctx) == []


@pytest.mark.parametrize("mod,conf", [(PR, True), (LL, True), (VR, False)])
def test_disparos_y_niveles(mod, conf):
    ctx = _ctx(conf); D = mod.disparos(ctx)
    assert len(D) > 0 and set(mod.VACIO) <= set(D.columns) and set(D.lado.unique()) <= {-1, 1}
    for ej in mod.EJECUCIONES:
        O = mod.niveles_lote(D, ej, ctx); s, e, st, tp = O[:, 2], O[:, 3], O[:, 4], O[:, 5]
        assert ((st - e) * s < 0).all() and ((tp - e) * s > 0).all()          # stop del lado malo, objetivo del bueno
        assert np.allclose(O[0, :len(mod.niveles(D.iloc[0].to_dict(), ej, ctx))], mod.niveles(D.iloc[0].to_dict(), ej, ctx))
