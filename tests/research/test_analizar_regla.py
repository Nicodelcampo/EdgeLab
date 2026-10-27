"""Etapa ANALIZAR_REGLA: el reporte del analizador sobre celdas congeladas coincide con la réplica del motor de la grilla."""
import numpy as np

from edgelab.research import etapas as ET, grilla_generica as GG, sintetico, u1_oro as X


def test_reporte_coincide_con_rep(monkeypatch):
    monkeypatch.setattr(X, "R_USATECH", 1.0)
    ctx = GG.contexto_m1(sintetico.bloques(dias=60, planta=True, seed=4), tick=0.25)
    D = X.disparos(ctx); cortes = GG.cortes_e0(D, X.VARIABLES)
    celdas = [[0, 1, 0, 1, 1, 1, 3, 3, 3, 1, 0], [1, 1, 0, 1, 1, 1, 3, 3, 3, 1, 0]]
    r = ET.ejecutar("ANALIZAR_REGLA", X, ctx, friccion=0.5, extra_adverso=0.25, params=dict(celdas=celdas, cortes=cortes), log=lambda s: None)
    res, cx = GG.correr(X, ctx, modo="REP", friccion=0.5, extra_adverso=0.25, cortes=cortes, celdas=celdas, log=lambda s: None)
    for a, b in zip(r["reportes"], res["replica"]):
        assert a["celda"] == b["celda"] and a.get("n", 0) == b["n"]
        mb = b.get("media_neta") if b.get("media_neta") is not None else b.get("media")
        if a.get("n") and mb is not None: assert np.isclose(a["media"], mb)
    assert any(a.get("n") for a in r["reportes"])
