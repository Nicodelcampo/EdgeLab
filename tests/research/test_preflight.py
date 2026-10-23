"""Preflight obligatorio: pasa un experimento sano y frena cada error de la revisión que puede detectarse solo."""
import types

import pytest

from edgelab.research import preflight as PF, u1_indaga as U
from edgelab.research.grilla_generica import Variable


def _exp(**cambios):
    m = types.ModuleType("exp_prueba")
    for a in ("NOMBRE", "VARIABLES", "EJECUCIONES", "disparos", "niveles", "BASE", "EJES_ORDINALES"): setattr(m, a, getattr(U, a))
    m.INDICADORES = ["LUX-IMB"]
    for k, v in cambios.items(): setattr(m, k, v)
    return m


def test_experimento_sano_pasa_estatico():
    assert PF.estatico(_exp()) == []


def test_errores_estaticos():
    assert any("falta INDICADORES" in e for e in PF.estatico(types.SimpleNamespace(**{a: 1 for a in PF.ATRIBUTOS if a != "INDICADORES"})))
    assert any("no usable" in e for e in PF.estatico(_exp(INDICADORES=["aVolCellPOI2"])))
    malo = [Variable("x", "xi", "extremos", cuantiles=4)]
    assert any("extremos" in e for e in PF.estatico(_exp(VARIABLES=malo, BASE={})))
    doble = [Variable("a", "c1", cuantiles=3, cortes=(1.0,))]
    assert any("exactamente uno" in e for e in PF.estatico(_exp(VARIABLES=doble, BASE={})))
    assert any("BASE nombra" in e for e in PF.estatico(_exp(BASE={"NO_EXISTE": 0})))


def test_dinamico_detecta_perillas_muertas_en_u1():
    err, _ = PF.dinamico(_exp(), dias=150)
    assert any("perillas muertas" in e for e in err)                         # el BE muerto de U1-INDAGA (error 4) se habría frenado


def test_campana_condicion_sin_test_y_seguimiento_sin_tope():
    base = dict(cid="X", titulo="t", experimento="m", kernel="k", fuente="NQ", modo="DESC", desde="20250101", hasta="20250301",
                needs=["NQ:2025-01-01:2025-03-01"], n_trials=1, family="F", spec="s", justificacion_economica="j", como_podria_refutarse="r")
    assert PF.verificar_campana(base) == []
    assert any("toca el holdout" in e for e in PF.verificar_campana(dict(base, needs=["NQ:2026-09-01:2026-10-10"])))
    assert any("sin test" in e for e in PF.verificar_campana(dict(base, condiciones=[dict(texto="MDE si no pasa ninguna", test="tests/no_existe.py::test_x")])))
    assert PF.verificar_campana(dict(base, condiciones=[dict(texto="ok", test="tests/research/test_preflight.py::test_experimento_sano_pasa_estatico")])) == []
    assert any("pérdida máxima" in e for e in PF.verificar_campana(dict(base, seguimiento=True)))


def test_dinamico_pasa_u1_sin_be():
    ej = [e for e in U.EJECUCIONES if e[3] == 0]
    m = _exp(EJECUCIONES=ej, BASE={"N": 0, "x": 1, "A/H": 1, "ejecución": ej.index(("E1A", "T1", "S3", 0))})
    err, avisos = PF.dinamico(m, dias=150)
    assert err == [], err


def test_ruido_sintetico_es_martingala():
    """Error 26: el generador reiniciaba el precio cada día. Sin efecto plantado, los incrementos futuros no se predicen con
    el movimiento pasado (ni dentro del día ni cruzando días)."""
    import numpy as np
    from edgelab.research import grilla_generica as GG, sintetico
    ctx = GG.contexto_m1(sintetico.bloques(dias=120, planta=False, seed=3), tick=0.25)
    c = ctx["c"]; k = np.arange(200, len(c) - 200, 7)
    pasado, futuro = c[k] - c[k - 120], c[k + 120] - c[k]
    assert abs(np.corrcoef(pasado, futuro)[0, 1]) < 0.05
    assert abs(c[ctx["ses"] != np.roll(ctx["ses"], 1)][1:] - c[np.flatnonzero(ctx["ses"] != np.roll(ctx["ses"], 1))[1:] - 1]).mean() < 5
