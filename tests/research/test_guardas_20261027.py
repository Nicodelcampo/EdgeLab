"""Guardas del 2026-10-27 (docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md, O13): el CONTEO del holdout con 0 disparos
en la ventana devuelve conteo 0 (el embudo sigue mirando) en vez de romper el kernel (U1-YM-GRILLA, U1-ES-GRILLA, U1-ORO-GRILLA)."""
import numpy as np
import pandas as pd

from edgelab.research import etapas as ET, grilla_generica as GG


class _ExpSinDisparos:
    NOMBRE = "SIN-DISPAROS"; VARIABLES = []; EJECUCIONES = [(1, 1.0)]

    @staticmethod
    def disparos(ctx):
        return pd.DataFrame(dict(k=[]))                                  # columna `k` vacía: dtype object, no entera

    @staticmethod
    def niveles(r, ej, ctx):
        raise AssertionError("sin disparos no hay niveles")


def _ctx(n=500):
    c = 20000 + np.cumsum(np.ones(n) * 0.25)
    return dict(t=np.arange(n) * 60.0, c=c, h=c + 0.25, l=c - 0.25, o=c, ses=np.arange(n) // 100, tick=0.25)


def test_correr_con_cero_disparos_no_rompe():
    res, D = GG.correr(_ExpSinDisparos, _ctx(), modo="REP", friccion=0.0, extra_adverso=0.0, cortes={}, celdas=[[0]])
    assert res["E0"]["disparos"] == 0 and len(D) == 0 and "ses" in D


def test_conteo_del_holdout_con_cero_disparos_da_cero():
    res = ET.ejecutar("HOLDOUT_CONTEO", _ExpSinDisparos, _ctx(), friccion=0.0, extra_adverso=0.0, params=dict(celdas=[[0], [0]], cortes={}))
    assert res["conteo"] == [0, 0]


def test_resumen_e0_con_cero_disparos_sin_columnas():
    """2026-10-27: U1 sin mes previo en el holdout devuelve un DataFrame vacío sin las columnas de las variables (KeyError 'r_vol')."""
    import pandas as pd
    from edgelab.research import grilla_generica as GG
    V = [GG.Variable("r", "r_vol", "grupo"), GG.Variable("z", "zt", "grupo", categoria=3)]
    r = GG.resumen_e0(pd.DataFrame(columns=["k", "ses"]), V, None)
    assert r["disparos"] == 0 and r["variables"]["r"]["faltantes"] == 0 and r["variables"]["z"]["conteo"] == {}


def test_correr_con_cero_disparos_sin_k_ni_columnas():
    """El experimento vacío puede no traer ni `k` ni las columnas de sus variables: correr devuelve E0 con 0 disparos, no rompe."""
    import types
    import pandas as pd
    from edgelab.research import grilla_generica as GG
    exp = types.SimpleNamespace(NOMBRE="X", VARIABLES=[GG.Variable("r", "r_vol", "grupo")], disparos=lambda c: pd.DataFrame(columns=["m"]))
    res, D = GG.correr(exp, {"ses": [1, 2]}, modo="REP", friccion=0.0, extra_adverso=0.0, cortes={}, celdas=[[0]], log=lambda *a: None)
    assert res["E0"]["disparos"] == 0 and len(D) == 0
