"""Perfiles de HFTZones universal: el literal de NQ no cambia y el escalado es por activo, versionado y con evidencia."""
import json
from pathlib import Path

import pytest

from edgelab.bridge.indicators import hftzones_nq, hftzones_universal as hu

PROFILES = Path(hu.__file__).with_name("hftzones_universal_profiles.json")


def test_perfil_literal_es_el_de_nq_sin_cambios():
    assert hu.profile() == dict(hftzones_nq.ACCEPT_DEFAULTS)
    assert hu.profile(hu.LITERAL, "ZB") == dict(hftzones_nq.ACCEPT_DEFAULTS)


def test_perfil_escalado_exige_instrumento_y_rechaza_desconocidos():
    with pytest.raises(ValueError):
        hu.profile(hu.SCALED)
    with pytest.raises(ValueError):
        hu.profile(hu.SCALED, "XX")
    with pytest.raises(ValueError):
        hu.profile("otro", "NQ")


def test_escalado_de_nq_es_el_literal_y_el_resto_solo_toca_umbrales_de_aceptacion():
    assert hu.profile(hu.SCALED, "NQ") == dict(hftzones_nq.ACCEPT_DEFAULTS)
    estructurales = ("max_retroceso_ticks", "retroceso_pct_height", "detect_absorb")
    table = json.loads(PROFILES.read_text(encoding="utf-8"))["profiles"]
    for inst in table:
        p = hu.profile(hu.SCALED, inst)
        assert set(p) == set(hftzones_nq.ACCEPT_DEFAULTS)
        for k in estructurales:                      # cambiarlos cambiaria QUE rachas existen, no cuales se aceptan
            assert p[k] == hftzones_nq.ACCEPT_DEFAULTS[k]
        assert p["min_absorb_pasos"] <= p["min_pasos"]


def test_tabla_declara_evidencia_y_no_transporta_paridad():
    d = json.loads(PROFILES.read_text(encoding="utf-8"))
    assert d["name"] == hu.SCALED and len(d["evidence_sha256"]) == 64
    assert hu.transfer_status("ZB", None, hu.SCALED)["parity_status"] == "PARITY_ABSTAIN"
    assert hu.transfer_status("ZB", None, hu.SCALED)["parameter_status"] == "SCALED_FUNNEL_V1_TARGET_FREE"
    assert hu.transfer_status("ZB")["parameter_status"] == "PARAMETERS_UNCALIBRATED"
