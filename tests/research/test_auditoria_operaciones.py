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


def test_operaciones_traen_riesgo_positivo(monkeypatch):
    ctx, cx, cortes = _cx(monkeypatch)
    r = ET.ejecutar("ANALIZAR_REGLA", X, ctx, friccion=0.5, extra_adverso=0.25, params=dict(celdas=CELDAS, cortes=cortes, operaciones=True), log=lambda s: None)
    o = r["operaciones"]
    assert len(o["riesgo"]) == len(o["neto"]) > 0 and all(x > 0 for x in o["riesgo"])


def test_normalizar_riesgo_da_r(monkeypatch):
    """NORMALIZAR = "riesgo": el P&L neto de cada operación queda dividido por su riesgo inicial (R)."""
    ctx, cx, cortes = _cx(monkeypatch)
    monkeypatch.setattr(X, "NORMALIZAR", "riesgo", raising=False)
    res, cxr = GG.correr(X, ctx, modo="REP", friccion=0.5, extra_adverso=0.25, cortes=cortes, celdas=CELDAS, log=lambda s: None)
    m = np.isfinite(cx["net"]) & np.isfinite(cxr["net"])
    rg = GG.riesgo_ops(cx["O"], np.searchsorted(ctx["t"], cx["t_fill"]), ctx)
    assert m.sum() > 0 and np.allclose(cxr["net"][m], cx["net"][m] / rg[m]) and res["normalizado"]["metodo"] == "riesgo"


def test_estadistico_r_en_params(monkeypatch):
    """`estadistico: "R"` en los params mide la etapa en R y deja el módulo como estaba."""
    ctx, cx, cortes = _cx(monkeypatch)
    base = ET.ejecutar("ANALIZAR_REGLA", X, ctx, friccion=0.5, extra_adverso=0.25, params=dict(celdas=CELDAS, cortes=cortes, operaciones=True), log=lambda s: None)
    r = ET.ejecutar("ANALIZAR_REGLA", X, ctx, friccion=0.5, extra_adverso=0.25, params=dict(celdas=CELDAS, cortes=cortes, operaciones=True, estadistico="R"), log=lambda s: None)
    o, b = r["operaciones"], base["operaciones"]
    assert np.allclose(np.array(o["neto"]), np.array(b["neto"]) / np.array(b["riesgo"])) and not hasattr(X, "NORMALIZAR")
