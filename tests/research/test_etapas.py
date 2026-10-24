"""Etapas del embudo sobre sintéticos: cada una corre y devuelve lo prometido; HOLDOUT_CONTEO no expone P&L."""
import json

import numpy as np
import pytest

from edgelab.research import etapas as ET, grilla_generica as GG, sintetico, u1_indaga as U

CELDA = [0, 1, 0, 2, 2, 2, 3, 3, 3, U.EJECUCIONES.index(("E1A", "T1", "S3", 0))]


@pytest.fixture(scope="module")
def ctxs():
    ctx = GG.contexto_m1(sintetico.bloques(dias=40, planta=True, seed=21), tick=0.25)
    ej = dict(ctx)
    for k in ("o", "h", "l", "c", "tpx"): ej[k] = ctx[k] + 50.0
    return ctx, ej


def test_e0_trae_densidad(ctxs):
    r = ET.ejecutar("E0", U, ctxs[0], friccion=1.0, extra_adverso=0.5, log=lambda s: None)
    assert r["densidad"]["por_mes"] and all("ticks_dia" in v for v in r["densidad"]["por_mes"].values())


def test_rep_topes_integridad_indaga(ctxs, monkeypatch):
    ctx, ej = ctxs; cortes = GG.cortes_e0(U.disparos(ctx), U.VARIABLES); kw = dict(friccion=1.0, extra_adverso=0.5, log=lambda s: None, cx_ej=ej)
    r = ET.ejecutar("REP", U, ctx, params=dict(celdas=[CELDA], cortes=cortes), **kw)
    assert r["replica"][0]["n"] == len(r["operaciones"]["neto"])
    t = ET.ejecutar("TOPES", U, ctx, params=dict(celdas=[CELDA], cortes=cortes, topes=[None, ["pts", 20.0]]), **kw)
    assert set(t["por_tope"]) == {"sin tope", "pts:20"}
    i = ET.ejecutar("INTEGRIDAD", U, ctx, params=dict(celdas=[CELDA], cortes=cortes), **kw)
    assert set(i["latencia"]) == {0, 1, 2, 5} and len(i["placebo"][0]) == 5
    g = ET.ejecutar("INDAGA", U, ctx, params=dict(base=CELDA, cortes=cortes), **kw)
    assert g["indagacion"]["base"] == CELDA and U.BASE["N"] == 0                       # BASE restaurada


def test_holdout_conteo_sin_pnl(ctxs):
    ctx, ej = ctxs; cortes = GG.cortes_e0(U.disparos(ctx), U.VARIABLES)
    r = ET.ejecutar("HOLDOUT_CONTEO", U, ctx, friccion=1.0, extra_adverso=0.5, params=dict(celdas=[CELDA], cortes=cortes), log=lambda s: None, cx_ej=ej)
    txt = json.dumps(r)
    assert set(r) == {"conteo"} and "media" not in txt and "neto" not in txt and "p_sesiones" not in txt
