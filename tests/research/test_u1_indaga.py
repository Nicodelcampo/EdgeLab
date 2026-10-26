"""U1-INDAGA sobre el conductor genérico: oráculo de la anatomía compilada, causalidad, y controles ruido / plantado."""
import numpy as np
import pandas as pd
import pytest

from edgelab.research import grilla_generica as GG, u1_indaga as U


def _bloques(dias=40, seed=1, planta=True):
    from edgelab.research.sintetico import bloques
    return bloques(dias=dias, seed=seed, planta=planta)


@pytest.fixture(scope="module")
def ctx_plantado():
    return GG.contexto_m1(_bloques(planta=True), tick=0.25)


def test_anatomia_contra_oraculo_python(ctx_plantado):
    D = U.disparos(ctx_plantado)
    assert len(D) > 20
    h, l, c, v = (ctx_plantado[x] for x in "hlcv")
    for r in D.sample(min(25, len(D)), random_state=0).to_dict("records"):
        d, m, k = int(r["lado"]), int(r["m"]), int(r["k"])
        tE = max([j for j in range(m + 1, k + 1) if (h[j] >= r["E"] - 1e-9 if d == 1 else l[j] <= r["E"] + 1e-9)] or [m + 1])
        js = tE
        while js > m + 1 and not (r["lo"] <= c[js - 1] <= r["hi"]): js -= 1
        assert r["dur_ida"] == tE - js + 1 and r["dur_vuelta"] == k - tE
        assert r["vol_ida"] == pytest.approx(v[js:tE + 1].sum()) and r["vol_vuelta"] == pytest.approx(v[tE + 1:k + 1].sum())


def test_variables_causales_no_cambian_al_cortar_el_futuro(ctx_plantado):
    D = U.disparos(ctx_plantado)
    corte = int(np.quantile(D.k, 0.5)); n = corte + 1
    cx = {k: (v[:n] if isinstance(v, np.ndarray) and len(v) == len(ctx_plantado["c"]) else v) for k, v in ctx_plantado.items()}
    cx["vp_start"] = ctx_plantado["vp_start"][:n + 1]; cx["tstart"] = ctx_plantado["tstart"][:n + 1]
    D2 = U.disparos(cx)
    cols = ["k", "dur_ida", "dur_vuelta", "vol_ida", "vol_vuelta", "fr_ida", "fr_vuelta", "r_vol", "vwap_pos"]
    a = D[D.k <= corte - 5][cols].sort_values(cols[:3]).reset_index(drop=True)
    b = D2[D2.k <= corte - 5][cols].sort_values(cols[:3]).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def _correr(planta, monkeypatch):
    monkeypatch.setattr(GG, "B_RW", 40)
    ctx = GG.contexto_m1(_bloques(dias=150, planta=planta, seed=3 if planta else 4), tick=0.25)
    res, _ = GG.correr(U, ctx, modo="DESC", friccion=1.0, extra_adverso=0.5, log=lambda s: None)
    return res


def test_control_ruido(monkeypatch):
    res = _correr(False, monkeypatch)
    assert res["canales"]["total"]["evaluables"] > 1000                       # que el control tenga con qué fallar
    assert res["canales"]["total"]["n_rechazadas_rw"] == 0


def test_control_plantado(monkeypatch):
    monkeypatch.setattr(U, "MARGINALES_POOL", ("x",), raising=False)
    res = _correr(True, monkeypatch)
    vr = res["indagacion"]["por_perilla"]["vol_vuelta/ida"]
    assert all(f["agregado"]["n"] >= f["n"] for f in vr)                    # agregar sobre x sólo suma operaciones
    tot = res["canales"]["total"]
    assert tot["n_rechazadas_rw"] > 0 or tot["nominadas_fdr"] > 0
    assert res["indagacion"]["por_perilla"]["ejecución"]                     # marginales armadas alrededor de BASE
    assert GG.n_celdas(U) == res["celdas"]


def test_detecta_ejecuciones_equivalentes():
    di = np.array([0, 0, 0, 1, 1, 1]); ei = np.array([0, 1, 2, 0, 1, 2]); pnl = np.array([1.0, 1.0, 2.0, -1.0, -1.0, 3.0])
    assert GG.ejecuciones_equivalentes(di, ei, pnl, [("a",), ("b",), ("c",)]) == [[["a"], ["b"]]]


def test_rep_informa_el_n_real_de_celdas_chicas():
    from edgelab.research import grilla_masiva as GM
    ctx = GG.contexto_m1(_bloques(dias=20, planta=True, seed=5), tick=0.25)
    cortes = GG.cortes_e0(U.disparos(ctx), U.VARIABLES)
    celda = (0, 1, 1, 0, 0, 0, 0, 0, 0, 0)                                      # muy filtrada: pocas operaciones
    rep, cx = GG.correr(U, ctx, modo="REP", friccion=1.0, extra_adverso=0.5, cortes=cortes, celdas=[list(celda)], log=lambda s: None)
    esperado = int((GM.mascara(cx["perillas"], cx["indices"], celda) & np.isfinite(cx["net"])).sum())
    assert rep["replica"][0]["n"] == esperado


def test_operaciones_de_reproduce_el_resumen_de_la_replica():
    ctx = GG.contexto_m1(_bloques(dias=20, planta=True, seed=5), tick=0.25)
    cortes = GG.cortes_e0(U.disparos(ctx), U.VARIABLES)
    celda = [0, 1, 0, 2, 2, 2, 3, 3, 3, 0]
    rep, cx = GG.correr(U, ctx, modo="REP", friccion=1.0, extra_adverso=0.5, cortes=cortes, celdas=[celda], log=lambda s: None)
    ops = GG.operaciones_de(cx, [celda])
    assert len(ops) == rep["replica"][0]["n"] and (ops.t.diff().dropna() >= 0).all()
    if "media_neta" in rep["replica"][0]: assert ops.neto.mean() == pytest.approx(rep["replica"][0]["media_neta"])


def test_normalizar_divide_por_el_rango_de_la_sesion_previa(monkeypatch):
    ctx = GG.contexto_m1(_bloques(dias=20, planta=True, seed=5), tick=0.25)
    cortes = GG.cortes_e0(U.disparos(ctx), U.VARIABLES)
    celda = [0, 1, 0, 2, 2, 2, 3, 3, 3, 0]
    _, cx0 = GG.correr(U, ctx, modo="REP", friccion=1.0, extra_adverso=0.5, cortes=cortes, celdas=[celda], log=lambda s: None)
    monkeypatch.setattr(U, "NORMALIZAR", "rango_sesion_previa", raising=False)
    rep, cx1 = GG.correr(U, ctx, modo="REP", friccion=1.0, extra_adverso=0.5, cortes=cortes, celdas=[celda], log=lambda s: None)
    assert rep["normalizado"]["metodo"] == "rango_sesion_previa"
    ok = np.isfinite(cx1["net"])
    assert ok.any() and np.allclose(cx1["net"][ok] * GG.escala_ops("rango_sesion_previa", cx1["ses"][ok], ctx), cx0["net"][ok])
