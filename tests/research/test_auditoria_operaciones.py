"""Auditoría vela a vela (experimento 4): sobre la simulación real de la grilla no hay fallas; una operación adulterada se detecta,
y la etapa ANALIZAR_REGLA la devuelve con `auditoria=True`."""
import numpy as np

from edgelab.research import etapas as ET, grilla_generica as GG, sintetico, u1_oro as X

CELDAS = [[0, 1, 0, 1, 1, 1, 3, 3, 3, 1, 0], [1, 1, 0, 1, 1, 1, 3, 3, 3, 1, 0]]


def _cx(monkeypatch):
    monkeypatch.setattr(X, "R_USATECH", 1.0)
    ctx = GG.contexto_m1(sintetico.bloques(dias=60, planta=True, seed=4), tick=0.25)
    cortes = GG.cortes_e0(X.disparos(ctx), X.VARIABLES)
    res, cx = GG.correr(X, ctx, modo="REP", friccion=0.5, extra_adverso=0.25, cortes=cortes, celdas=CELDAS, log=lambda s: None)
    return ctx, cx, cortes


def test_simulacion_real_sin_fallas(monkeypatch):
    ctx, cx, cortes = _cx(monkeypatch)
    a = GG.auditar_operaciones(cx, CELDAS, ctx)
    assert a["operaciones"] > 0 and a["causal"] == a["entrada"] == a["orden"] == a["toque_previo"] == 0, a
    r = ET.ejecutar("ANALIZAR_REGLA", X, ctx, friccion=0.5, extra_adverso=0.25, params=dict(celdas=CELDAS, cortes=cortes, auditoria=True), log=lambda s: None)
    assert r["auditoria"]["operaciones"] == a["operaciones"]


def test_detecta_entrada_imposible_y_llenado_anticipado(monkeypatch):
    ctx, cx, _ = _cx(monkeypatch)
    mk = np.zeros(len(cx["net"]), bool)
    for c in CELDAS: mk |= GG.GM.mascara(cx["perillas"], cx["indices"], tuple(c))
    m = int(np.flatnonzero(mk & np.isfinite(cx["net"]))[0])
    cx = dict(cx, O=cx["O"].copy(), t_fill=cx["t_fill"].copy())
    cx["O"][m, 3] = 1; cx["O"][m, 5] = 1e9; cx["t_fill"][m] = cx["t"][m]      # límite a un precio imposible y llenado anticipado
    a = GG.auditar_operaciones(cx, CELDAS, ctx)
    assert a["entrada"] >= 1 and a["causal"] >= 1
