"""Motor de regímenes offline: codificación del cubo, series diarias por celda, walk-forward con controles y nulo de signo."""
import numpy as np

from edgelab.research import grilla_masiva as GM, regimen_offline as RO


def _cubo(nombre, plantar, seed):
    rng = np.random.default_rng(seed)
    dias = np.array([20250101 + 100 * (m % 12) + 10000 * (m // 12) + d for m in range(12) for d in range(1, 21)])
    n = 30000; ses = rng.choice(dias, n); a = rng.integers(0, 3, n); b = rng.integers(0, 3, n); e = rng.integers(0, 2, n)
    net = rng.normal(0, 1, n)
    if plantar: net[(a == 2) & (b == 1)] += 0.6                   # celda con ventaja estable todos los meses
    P = [GM.Perilla("a", 3, "grupo"), GM.Perilla("b", 3, "eq_any"), GM.Perilla("ejecución", 2, "grupo")]
    cx = dict(net=net, indices=[a, b, e], ses=ses, perillas=P)
    return RO.decodificar(RO.codificar(cx), nombre)


def test_codificar_y_series_diarias():
    c = _cubo("x", True, 1)
    d = RO.series_diarias(c, min_ops=30)
    assert d.S.shape == d.C.shape == (len(np.unique(c.ses)), len(d.celdas))
    assert abs(d.C.sum() - sum(d.C.sum(0))) < 1e-6 and d.C.max() > 0


def test_walk_forward_encuentra_la_celda_plantada_y_el_nulo_no():
    D = [RO.series_diarias(_cubo(f"c{i}", i == 0, i), min_ops=30) for i in range(4)]
    r = RO.walk_forward(D, W=3, k=1, min_ops=20, min_dias=10, B_azar=50, seed=3)
    assert r["n_ventanas"] >= 8 and r["delta_azar"] > 0.2
    nul = RO.nulo_signo(D, B=10, seed=4, W=3, k=1, min_ops=20, min_dias=10)
    assert nul["p_nulo"] <= 0.2


def test_etapa_cubo_de_punta_a_punta(monkeypatch):
    from edgelab.research import cvgap2 as X, etapas as ET, grilla_generica as GG, sintetico
    ctx = GG.contexto_m1(sintetico.bloques(dias=30, planta=False, seed=19), tick=0.25)
    D = X.disparos(ctx); cortes = GG.cortes_e0(D, X.VARIABLES)
    r = ET.ejecutar("CUBO", X, ctx, friccion=1.0, extra_adverso=0.0, cx_ej=None, params=dict(cortes=cortes, estadistico="R"), log=lambda *a: None)
    c = RO.decodificar(r["cubo"], "cvgap2"); d = RO.series_diarias(c, min_ops=5)
    assert c.idx.shape[1] == len(X.VARIABLES) + 1 and len(c.net) == r["cubo"]["n"] > 0 and d.S.shape[1] > 0
