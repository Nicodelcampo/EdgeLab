"""KALMAN-FADE: preflight estático, causalidad, paridad lote/escalar y controles (ruido sin efecto, efecto plantado)."""
from __future__ import annotations

import numpy as np

from edgelab.research import grilla_generica as GG, indicadores as IND, kalman_fade as KF, preflight as PF, sintetico

_CTX = {}


def _ctx(planta=False, seed=21):
    if (planta, seed) not in _CTX:
        _CTX[(planta, seed)] = GG.contexto_m1(sintetico.bloques(dias=45, planta=planta, seed=seed), tick=0.25)
    return _CTX[(planta, seed)]


def test_preflight_estatico():
    assert PF.estatico(KF) == []


def test_causal():
    assert IND.causal(KF.disparos, _ctx()) == []


def test_niveles_lote_identico_a_niveles():
    ctx = _ctx()
    D = KF.disparos(ctx)
    assert len(D) > 0
    O1 = GG.ops_por_fila(KF, D, ctx); O2 = GG._ops_lote(KF, D, ctx)
    assert O1.shape == O2.shape and np.array_equal(O1, O2, equal_nan=True)


def test_disparos_respetan_umbral_enfriamiento_y_sesion():
    ctx = _ctx()
    D = KF.disparos(ctx)
    assert (D.z_abs >= KF.Z_MIN).all()
    for (_, su), g in D.groupby(["ses", "suav"]):
        assert (np.diff(g.k.to_numpy()) >= KF.ENFRIAMIENTO).all()
    ses = np.asarray(ctx["ses"])
    assert (ses[D.k.to_numpy()] == ses[D.k.to_numpy() - 1]).all(), "nunca en la primera vela de la sesión"


def test_fade_apunta_al_nivel_y_continuacion_al_reves():
    ctx = _ctx()
    D = KF.disparos(ctx).head(50)
    for _, d in D.iterrows():
        k, _, s, e, sl, tp, _ = KF.niveles(d, ("FADE", "NIVEL", "S2"), ctx)
        assert s == -int(np.sign(d.z)) and (tp - e) * s > 0 and (e - sl) * s > 0
        _, _, s2, _, _, _, _ = KF.niveles(d, ("CONTINUACION", "NIVEL", "S2"), ctx)
        assert s2 == -s


def _media_fade(ctx):
    D = KF.disparos(ctx).reset_index(drop=True)
    di, ei, pnl, _, _ = GG.simular_ops(KF, D, ctx)
    fade = np.isin(ei, [i for i, e in enumerate(KF.EJECUCIONES) if e[0] == "FADE"])
    return float(np.nanmean(pnl[fade])), int(fade.sum())


def test_control_ruido():
    """Sin efecto plantado (saltos que NO revierten), el fade no gana de forma sistemática."""
    m, n = _media_fade(_ctx(planta=False, seed=3))
    assert n > 100 and m < 1.0


def test_control_plantado():
    """Con saltos que revierten hacia el nivel previo (sintetico.bloques planta=True), el fade gana más que sobre ruido."""
    mp, _ = _media_fade(_ctx(planta=True, seed=3))
    mr, _ = _media_fade(_ctx(planta=False, seed=3))
    assert mp > mr + 1.0, (mp, mr)
