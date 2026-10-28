"""Compuerta de potencia del ACTA y anulación de aperturas sin mirar (decisión de Nico, 2026-10-26; error E8)."""
import json

import pytest

from edgelab.funnel.libro_lord import LibroLord
from edgelab.research import embudo as EM, holdout_ventanas as HV


def _st(media_desc, n=60, ancho=8.0, oos=None):
    p = dict(celda=[1], n=n, media_neta=media_desc, ic90=[media_desc - ancho / 2, media_desc + ancho / 2])
    st = dict(etapa="ACTA", fase="PENDIENTE", historial=[], regla=dict(celda=[1], tope=None), desc=dict(pistas=[p]), cortes={},
              reglas=dict(regimen=EM._cfg({}, "regimen")))
    if oos is not None: st["oos"] = dict(veredictos=[dict(celda=[1], media=oos)])
    return st


def test_plan_sube_n_o_espera(tmp_path):
    em = EM.Embudo(tmp_path, {}, libro=LibroLord(tmp_path / "l.json", permitir_otra_ruta=True), log=lambda s: None)
    spec = dict(cid="X", familia="F"); h = EM._cfg(spec, "holdout")
    grande = em._plan_holdout(spec, _st(10.0), h)
    assert grande["n_fijo"] == h["n_fijo"] and grande["potencia"] > 0.8                       # ya alcanza con 150
    medio = em._plan_holdout(spec, _st(6.0, ancho=8.0), h)
    assert h["n_fijo"] < medio["n_fijo"] <= h["n_max"] and medio["potencia"] >= 0.79            # se sube N antes de mirar
    chico = em._plan_holdout(spec, _st(0.3), h)
    assert chico["n_fijo"] is None                                                              # no alcanza ni con N máximo
    assert em._plan_holdout(spec, _st(10.0, oos=0.3), h)["fuente"] == "OOS"                     # manda lo más reciente no mirado


def test_anulacion_sin_mirar_devuelve_la_apertura(tmp_path):
    lib = tmp_path / "v.jsonl"
    HV.registrar_apertura("F", "A", 20261001, 150, lib)
    assert HV.problemas("F", 20261001, "B", lib)                                              # la familia ya tiene su apertura
    with pytest.raises(ValueError): HV.anular_apertura("F", "A", "x", n_mirado=3, libro=lib)    # mirado: no se anula
    HV.anular_apertura("F", "A", "registrada sin potencia", libro=lib)
    assert not HV.problemas("F", 20261001, "B", lib) and not HV.aperturas_vigentes("F", lib)
    assert HV.registrar_apertura("F", "A", 20261001, 300, lib)["n_fijo"] == 300                # se puede volver a registrar
    assert len(HV.leer(lib)) == 3                                                               # nada se borró
