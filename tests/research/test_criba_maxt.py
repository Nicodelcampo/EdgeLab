"""Criba maxT por signos de sesión: error familiar bajo dependencia, potencia, opción por campaña y reproducibilidad de lo emitido."""
import json

import numpy as np
import pytest

from edgelab.research import embudo as EB, etapas as ET, grilla_generica as GG, grilla_masiva as GM, sintetico, u1_indaga as U

P = [GM.Perilla("a", 4, "ge"), GM.Perilla("b", 4, "ge"), GM.Perilla("ej", 3, "grupo")]
KW = dict(friccion=1.0, extra_adverso=0.5, log=lambda s: None)


def _datos(seed, efecto=0.0, n_ses=160):
    """Celdas anidadas y correladas, con factor común por sesión y operaciones de cola pesada; `efecto` planta una zona con ventaja."""
    r = np.random.default_rng(seed); ops = r.integers(1, 7, n_ses); ses = np.repeat(np.arange(n_ses), ops); n = len(ses)
    a, b, ej = r.integers(0, 4, n), r.integers(0, 4, n), r.integers(0, 3, n)
    # el factor común es lo que BH no ve: todas las celdas de la sesión se mueven juntas
    net = r.choice((-1.0, 1.0), n_ses)[ses] * r.gamma(2.0, 6.0, n_ses)[ses] + r.standard_t(4, n) * 8
    net = net + efecto * ((a >= 2) & (b >= 2) & (ej == 0))
    return [a, b, ej], net, ses


def _corrida(seed, efecto=0.0, B=299):
    idx, net, ses = _datos(seed, efecto); st = GM.estadisticas(*GM.tensor(P, idx, net), min_n=10)
    return GM.criba_maxt(P, idx, net, ses, st, B=B, alfa=0.10, seed=seed + 7), st


def test_sin_senal_pocas_corridas_con_alguna_nominada_y_bh_no_lo_logra():
    N = 1000; maxt = bh = 0
    for sd in range(N):
        mt, st = _corrida(sd); maxt += mt["n_nominadas"] > 0; bh += GM.criba(st, q=0.10)["n_nominadas"] > 0
    assert maxt / N <= 0.12                                                  # nominal 10 %, ee 0,95 %; 3.000 semillas midieron 10,4 %
    assert bh / N > 2 * maxt / N                                             # el defecto que motiva la criba sigue visible


def test_con_senal_plantada_la_detecta():
    """Zona de ~35 sesiones: T <= raíz(sesiones), una celda con menos de umbral² sesiones no se puede nominar nunca."""
    hits = 0
    for sd in range(40):
        mt, _ = _corrida(sd, efecto=40.0); hits += (2, 2, 0) in mt["nominadas"]
    assert hits / 40 >= 0.8


def test_determinista_y_coherente():
    a, _ = _corrida(5, efecto=40.0); b, _ = _corrida(5, efecto=40.0)
    assert a["nominadas"] == b["nominadas"] and a["umbral"] == b["umbral"]
    for c in a["nominadas"]: assert a["t"][c] > a["umbral"] and a["p_ajustado"][c] <= 0.10


def test_t_invariante_a_operaciones_de_otra_escala_y_sin_evaluables():
    idx, net, ses = _datos(1); st = GM.estadisticas(*GM.tensor(P, idx, net), min_n=10)
    x, y = GM.criba_maxt(P, idx, net, ses, st, B=50), GM.criba_maxt(P, idx, net * 1000, ses, st, B=50)
    assert np.allclose(x["t"], y["t"], equal_nan=True) and x["umbral"] == pytest.approx(y["umbral"])
    vacio = dict(st, evaluable=np.zeros_like(st["evaluable"]))
    assert GM.criba_maxt(P, idx, net, ses, vacio, B=50)["nominadas"] == []


def test_romano_wolf_no_cambia_por_el_refactor_de_sumas():
    idx, net, ses = _datos(2); st = GM.estadisticas(*GM.tensor(P, idx, net), min_n=10)
    us, inv = np.unique(ses, return_inverse=True); ev = st["evaluable"].ravel()
    W = np.random.default_rng(0).multinomial(len(us), np.full(len(us), 1 / len(us)), size=20).astype(float)
    bs = GM._Bootstrap(P, idx, net, inv, len(us), ev, W); M = np.concatenate([m for *_, m in bs.bloques()], 1)
    assert np.allclose(M, GM._medias_bootstrap_denso(P, idx, net, inv, ev, W), equal_nan=True)


@pytest.fixture(scope="module")
def ctx():
    return GG.contexto_m1(sintetico.bloques(dias=40, planta=True, seed=21), tick=0.25)


@pytest.fixture
def rw_chico(monkeypatch):
    monkeypatch.setattr(GG, "B_RW", 20)


def test_desc_fdr_sin_rastro_de_maxt_y_maxt_con_bh_informativo(ctx, rw_chico):
    viejo = ET.ejecutar("DESC", U, ctx, **KW); expl = ET.ejecutar("DESC", U, ctx, params=dict(criba="fdr"), **KW)
    assert json.dumps(viejo, default=float) == json.dumps(expl, default=float) and "maxt" not in json.dumps(viejo["canales"], default=float)
    nuevo = ET.ejecutar("DESC", U, ctx, params=dict(criba="maxt"), **KW)
    for c in ("total", "reciente"):
        v, n = viejo["canales"][c], nuevo["canales"][c]
        assert n["nominadas_fdr"] == v["nominadas_fdr"] and n["criba"] == "maxt" and n["maxt"]["seed"] == 20261030
        assert all(p["criba"] == "maxt" and "q_fdr" in p for p in n["pistas"])


def test_criba_desconocida_se_rechaza(ctx, rw_chico):
    with pytest.raises(ValueError, match="criba"): ET.ejecutar("DESC", U, ctx, params=dict(criba="otra"), **KW)


def test_compuerta_usa_la_marca_de_la_pista():
    fdr = dict(nominada_fdr=True, q_fdr=0.01, pi0_fdr=1.0, m_fdr=100)
    assert EB.nominada(fdr, como="informacion")[0]
    assert not EB.nominada(dict(fdr, criba="maxt", nominada_maxt=False), como="informacion")[0]        # BH nomina, maxT no: no pasa
    assert EB.nominada(dict(nominada_fdr=False, q_fdr=0.9, pi0_fdr=1.0, m_fdr=100, criba="maxt", nominada_maxt=True), como="informacion")[0]


def test_estado_viejo_conserva_fdr_y_nuevo_congela_maxt():
    assert EB._criba(dict(reglas=dict(linaje={}))) == "fdr" and EB._criba({}) == "fdr"
    assert EB._criba(dict(reglas=dict(criba=dict(metodo="maxt")))) == "maxt"


def test_alfa_por_canal_reparte_el_error_familiar_entre_los_dos_canales():
    """2026-10-31: con maxT en los canales total y reciente, cada uno usa alfa/2 (Bonferroni), así la campaña queda en <= 0,10."""
    import inspect
    from edgelab.research import grilla_generica as GG
    assert GG.ALFA_CRIBA_CANAL == GG.ALFA_RW / 2 == 0.05
    assert "alfa=ALFA_CRIBA_CANAL" in inspect.getsource(GG.canales)
