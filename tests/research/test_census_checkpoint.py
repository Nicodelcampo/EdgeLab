# -*- coding: utf-8 -*-
"""Checkpoint del censo de tasa de señales.

Existe porque una corrida completa cuesta ~25 h de CPU en la máquina operativa
(HFTZones2 solo tardó 5 h sobre 60 sesiones) y hasta ahora el resultado se
escribía UNA vez, al final: una caída a la hora 24 costaba las 24.

El grano es (contrato × indicador), que es la unidad de cómputo real.
"""
import json

import pytest

from diag.tasa_senales import post_sepmin as P

PLAN = [("6E_03-26_ticks.parquet", ["2026-01-05", "2026-01-06"]),
        ("6E_06-26_ticks.parquet", ["2026-04-01"])]
INDS = ["Gaps2", "BigTrap2"]


def _clave(plan=PLAN, universo="u0", commit="c0", sep=120, lead=20):
    return P.clave_de_corrida(plan, universo, commit, sep, lead)


def test_sin_checkpoint_devuelve_vacio(tmp_path):
    assert P.leer_checkpoint(tmp_path / "no_existe.json", _clave()) == {}


def test_round_trip_conserva_lo_calculado(tmp_path):
    p = tmp_path / "c.checkpoint.json"
    hecho = {"6E_03-26_ticks.parquet": {"Gaps2": {"segundos": 8143.0}}}
    P.escribir_checkpoint(p, _clave(), hecho, PLAN, INDS)
    assert P.leer_checkpoint(p, _clave()) == hecho


def test_el_checkpoint_se_declara_incompleto(tmp_path):
    """Nunca puede confundirse con un censo cerrado."""
    p = tmp_path / "c.checkpoint.json"
    P.escribir_checkpoint(p, _clave(), {}, PLAN, INDS)
    ck = json.loads(p.read_text(encoding="utf-8"))
    assert ck["complete"] is False
    assert "PARCIAL" in ck["aviso"]
    assert ck["unidades_pendientes"] == len(PLAN) * len(INDS)


def test_cuenta_las_unidades_que_faltan(tmp_path):
    p = tmp_path / "c.checkpoint.json"
    hecho = {"6E_03-26_ticks.parquet": {"Gaps2": {}, "BigTrap2": {}}}
    P.escribir_checkpoint(p, _clave(), hecho, PLAN, INDS)
    ck = json.loads(p.read_text(encoding="utf-8"))
    assert ck["unidades_pendientes"] == 2      # el otro contrato, dos indicadores


@pytest.mark.parametrize("cambio", [
    dict(universo="OTRO"),
    dict(commit="OTRO"),
    dict(sep=60),
    dict(lead=5),
    dict(plan=[("6E_03-26_ticks.parquet", ["2026-01-05"])]),
])
def test_falla_cerrado_si_el_checkpoint_es_de_otra_corrida(tmp_path, cambio):
    """Mezclar resultados de dos configuraciones dentro de un mismo censo es
    justo lo que el manifiesto existe para hacer imposible. No se descarta en
    silencio: se avisa."""
    p = tmp_path / "c.checkpoint.json"
    P.escribir_checkpoint(p, _clave(), {"x": {"Gaps2": {}}}, PLAN, INDS)
    with pytest.raises(P.CheckpointMismatch):
        P.leer_checkpoint(p, _clave(**cambio))


def test_se_puede_descartar_explicitamente(tmp_path):
    p = tmp_path / "c.checkpoint.json"
    P.escribir_checkpoint(p, _clave(), {"x": {"Gaps2": {}}}, PLAN, INDS)
    assert P.leer_checkpoint(p, _clave(commit="OTRO"),
                             permitir_descartar=True) == {}


def test_el_checkpoint_ajeno_no_se_borra(tmp_path):
    """Fail-closed de verdad: si no es tuyo, no lo pisás."""
    p = tmp_path / "c.checkpoint.json"
    P.escribir_checkpoint(p, _clave(), {"x": {"Gaps2": {}}}, PLAN, INDS)
    antes = p.read_bytes()
    with pytest.raises(P.CheckpointMismatch):
        P.leer_checkpoint(p, _clave(commit="OTRO"))
    assert p.read_bytes() == antes


def test_la_escritura_es_atomica(tmp_path):
    """Se escribe a .tmp y se renombra: una caída a mitad de escritura no deja
    un checkpoint truncado que después no parsee."""
    p = tmp_path / "c.checkpoint.json"
    P.escribir_checkpoint(p, _clave(), {}, PLAN, INDS)
    P.escribir_checkpoint(p, _clave(), {"x": {"Gaps2": {}}}, PLAN, INDS)
    assert json.loads(p.read_text(encoding="utf-8"))["hecho"] == {"x": {"Gaps2": {}}}
    assert not list(tmp_path.glob("*.tmp"))
