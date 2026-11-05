"""Control nulo de DESC: determinismo por semilla, identidad sin nulo, media ~0, signo por sesión completa."""
import json

import numpy as np
import pytest

from edgelab.research import etapas as ET, grilla_generica as GG, sintetico, u1_indaga as U

KW = dict(friccion=1.0, extra_adverso=0.5, log=lambda s: None)


@pytest.fixture(scope="module")
def ctx():
    return GG.contexto_m1(sintetico.bloques(dias=40, planta=True, seed=21), tick=0.25)


@pytest.fixture(autouse=True)
def rw_chico(monkeypatch):
    monkeypatch.setattr(GG, "B_RW", 20)


def _serie():
    r = np.random.default_rng(0); n = 40000
    ei = r.integers(0, 4, n); ses = r.integers(0, 500, n); net = r.normal(1.0, 5.0, n) + ei
    net[::97] = np.nan
    return net, ei, ses


def test_neutralizar_determinista_y_semilla_importa():
    net, ei, ses = _serie()
    a, b, c = GG.neutralizar(net, ei, ses, 1), GG.neutralizar(net, ei, ses, 1), GG.neutralizar(net, ei, ses, 2)
    assert np.array_equal(a, b, equal_nan=True) and not np.array_equal(a, c, equal_nan=True)


def test_neutralizar_media_cero_y_nan_conservados():
    net, ei, ses = _serie(); x = GG.neutralizar(net, ei, ses, 3)
    assert np.array_equal(np.isnan(x), np.isnan(net))
    for e in range(4):
        v = x[ei == e]; assert abs(np.nanmean(v)) < 0.3


def test_neutralizar_signo_unico_por_sesion():
    net, ei, ses = _serie(); ok = np.isfinite(net); centrado = net.copy()
    for e in range(4): centrado[(ei == e) & ok] -= net[(ei == e) & ok].mean()
    x = GG.neutralizar(net, ei, ses, 4)
    signo = np.sign(x[ok] * centrado[ok]); s = ses[ok]
    assert all(len(set(signo[s == u])) == 1 for u in np.unique(s)) and set(signo) == {-1.0, 1.0}


def test_desc_sin_nulo_identico_y_con_nulo_determinista(ctx):
    base = ET.ejecutar("DESC", U, ctx, **KW)
    nada = ET.ejecutar("DESC", U, ctx, params=dict(nulo=None), **KW)
    assert "control_nulo" not in base and json.dumps(base, default=float) == json.dumps(nada, default=float)
    a = ET.ejecutar("DESC", U, ctx, params=dict(nulo=0), **KW); b = ET.ejecutar("DESC", U, ctx, params=dict(nulo=0), **KW)
    assert a["control_nulo"] == b["control_nulo"] and a["control_nulo"]["semilla"] == 0
    for c in ("total", "reciente"):
        r = a["control_nulo"][c]
        assert r["celdas_evaluables"] == a["canales"][c]["evaluables"] and r["nominadas_fdr"] == a["canales"][c]["nominadas_fdr"]
        m = [x["media"] for x in r["mejores_medias"]]; assert len(m) <= 5 and m == sorted(m, reverse=True)


def test_nulo_fuera_de_desc_se_rechaza(ctx):
    with pytest.raises(ValueError, match="nulo"):
        GG.correr(U, ctx, modo="E0", nulo=1, **KW)
