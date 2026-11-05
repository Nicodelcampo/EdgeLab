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


def test_marginales_globales_cuadran_con_el_total(monkeypatch):
    """Cada perilla reparte todas las operaciones evaluables entre sus niveles: la suma por nivel = la suma total."""
    ctx, cx, cortes = _cx(monkeypatch)
    r = ET.ejecutar("MARGINALES", X, ctx, friccion=0.5, extra_adverso=0.25, params=dict(cortes=cortes, estadistico="R"), log=lambda s: None)
    mg = r["marginales_globales"]; tot = {k: sum(f["suma"] for f in v) for k, v in mg.items() if not k.endswith("etiquetas")}
    assert "ejecución.entrada" in mg and r["normalizado"]["metodo"] == "riesgo"
    assert np.allclose(tot["ejecución"], tot["ejecución.entrada"]) and np.allclose(tot["ejecución"], tot["ejecución.stop"])


def test_trayectorias_coherentes_con_el_simulador(monkeypatch):
    """La trayectoria arranca en la vela de llenado, el stop es −1R, y si la regla se detuvo por stop el camino toca −1R."""
    ctx, cx, cortes = _cx(monkeypatch)
    r = ET.ejecutar("TRAYECTORIAS", X, ctx, friccion=0.5, extra_adverso=0.25, params=dict(celdas=CELDAS, cortes=cortes, k=120), log=lambda s: None)
    T = r["trayectorias"]
    assert T and all(t["stop_R"] == -1.0 and len(t["f"]) == len(t["a"]) == len(t["c"]) >= 1 for t in T)
    for t in T:
        if t["R_regla"] is not None and t["R_regla"] < -0.99 - t["friccion_R"]:   # perdió el riesgo completo: tocó el stop
            assert min(t["a"]) <= -1.0 + 1e-6
    assert set(r["variables"]) <= set(T[0]["x"])


def test_riesgo_ops_descarta_residuo_de_coma_flotante():
    """2026-11-03: un stop en la entrada con residuo ~1e-10 no es riesgo; antes daba ±1e8 R en el atlas."""
    O = np.zeros((3, 8)); O[:, 3] = 1; O[:, 5] = [1.08500, 1.08500, 1.08500]
    O[:, 6] = [1.08500 + 1e-10, 1.08500, 1.08500 - 0.00050]
    sim = dict(o=np.array([1.085]), tick=0.00005)
    r = GG.riesgo_ops(O, np.zeros(3, np.int64), sim)
    assert np.isnan(r[0]) and np.isnan(r[1]) and abs(r[2] - 0.0005) < 1e-12
