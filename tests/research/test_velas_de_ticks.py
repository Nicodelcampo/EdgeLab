"""El embudo sobre velas de N ticks (2026-11-07): mismas claves que M1, velas dentro de la sesión, ticks de cada vela en orden y el
motor de la grilla (simulación y etapas) sin cambios."""
import numpy as np

from edgelab.research import grilla_generica as GG, sintetico


def _ctx(n=10, dias=6):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=3), tick=0.25, ticks_por_barra=n)


def test_velas_de_ticks_bien_armadas():
    c = _ctx()
    t, tp, ts = c["t"], c["tpx"], c["tstart"]
    assert (np.diff(t) > 0).all() and c["ticks_por_barra"] == 10
    assert (np.diff(ts) == 10).all() and len(tp) == ts[-1]
    for k in (0, 5, len(t) - 1):
        px = tp[ts[k]:ts[k + 1]]
        assert c["o"][k] == px[0] and c["c"][k] == px[-1] and c["h"][k] == px.max() and c["l"][k] == px.min()
    # ninguna vela cruza el corte de sesión
    b = sintetico.bloques(dias=6, planta=False, seed=3)
    assert len(np.unique(c["ses"])) == sum(len(np.unique(x.sesion)) for x in b if len(x))


def test_el_embudo_corre_igual_sobre_velas_de_ticks():
    from edgelab.research import cvgap2 as X, etapas as ET
    c = _ctx(n=10, dias=20)
    D = X.disparos(c); assert len(D) > 0
    di, ei, pnl, _, _ = GG.simular_ops(X, D, c)
    assert len(di) > 0 and np.isfinite(pnl).any()
    r = ET.ejecutar("MARGINALES", X, c, friccion=1.0, extra_adverso=0.0, cx_ej=None,
                    params=dict(cortes=GG.cortes_e0(D, X.VARIABLES), estadistico="R"), log=lambda *a: None)
    assert r["operaciones"] > 0
