"""Pruebas de contrato, causalidad y cobertura de EXTERNAS-ESTRUCTURALES-A5."""
from __future__ import annotations

from edgelab.research import externas_estructurales_a5 as mod
from edgelab.research import grilla_generica as GG
from edgelab.research import indicadores as I
from edgelab.research import sintetico
from edgelab.research import tablas


def test_contrato_y_preflight_externas_estructurales():
    assert tablas.contrato(mod) == []
    assert tablas.preflight("edgelab.research.externas_estructurales_a5") == []


def test_causalidad_y_columnas_externas_estructurales():
    ctx = GG.contexto_m1(sintetico.bloques(dias=60, planta=False, seed=11), tick=0.25)
    assert I.causal(mod.eventos, ctx) == []
    assert I.causal_por_disparo(mod.eventos, ctx) == []
    T = tablas.generar(mod, ctx)
    assert len(T) > 0
    for d in mod.DEFINICIONES:
        assert d in T.columns
        ctrl = mod.CONTROL[d]
        assert ctrl in T.columns
    assert (T["rg"] > 0).all()
