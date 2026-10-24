"""Controles de las variables de régimen del agente (perímetro: docs/research/GUIA_GRILLA_MASIVA.md §6)."""
import numpy as np
import pandas as pd

from edgelab.research import grilla_generica as GG, indicadores as I, sintetico
from edgelab.research.agente import regimen as R


def _ctx(dias=45, seed=5, planta=False):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=planta, seed=seed), tick=0.25)


def _por_vela_df(ctx):
    return pd.DataFrame(dict(k=np.arange(len(ctx["c"])), **R.por_vela(ctx)))


def test_causal():
    assert I.causal(_por_vela_df, _ctx()) == []


def test_control_ruido():
    """Ruido puro: los cortes por cuantiles del E0 dan niveles balanceados y ningún bloque horario queda vacío."""
    ctx = _ctx(); D = R.agregar(pd.DataFrame(dict(k=np.arange(0, len(ctx["c"]), 7))), ctx)
    vs = list(R.VARIABLES_REGIMEN.values()); cortes = GG.cortes_e0(D, vs)
    for v, b in zip(vs, GG.discretizar(D, vs, cortes)):
        frac = np.bincount(b[b >= 0], minlength=v.categoria or v.cuantiles) / max((b >= 0).sum(), 1)
        assert frac.min() > (0.05 if v.categoria else 0.25), (v.nombre, frac)
    assert np.nanmax(D.reg_eficiencia) <= 1 and np.nanmin(D.reg_eficiencia) >= 0


def test_control_plantado():
    """Volatilidad plantada: si las últimas sesiones mueven el triple, reg_vol_diaria las marca altas DESDE la sesión siguiente."""
    ctx = _ctx(dias=40); ses = ctx["ses"]; corte = np.unique(ses)[30]; m = ses >= corte
    for k in ("o", "h", "l", "c"):
        x = ctx[k].copy(); ancla = x[np.argmax(m)]; x[m] = ancla + 3 * (x[m] - ancla); ctx[k] = x
    D = R.agregar(pd.DataFrame(dict(k=np.arange(len(ses)))), ctx)
    r = pd.Series(D.reg_rango_prev.to_numpy()).groupby(ses).first()
    assert r.loc[corte] < 2 and r.loc[np.unique(ses)[31]] > 2                       # la sesión del salto todavía no lo sabe
    assert np.nanmedian(D.reg_atr_rel[m & (ses > corte)]) < 2                       # contra la sesión anterior (ya alta): normal


def test_variables_listas_y_conteo():
    class Exp:
        VARIABLES = [R.VARIABLES_REGIMEN["vol_diaria"], R.VARIABLES_REGIMEN["hora"]]; EJECUCIONES = [0, 1]
    assert GG.n_celdas(Exp) == 3 * 5 * 2                                            # extremos 3 · eq_any 4+1 · ejecuciones 2
