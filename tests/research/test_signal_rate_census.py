from __future__ import annotations

import pytest

from diag.tasa_senales.audit_post_sepmin import CensusAuditError, audit


def contract(dates, counts, name="BigTrap2"):
    return {"fechas": dates, "ind": {name: {
        "n_dias": len(dates),
        "post_por_dia": dict(zip(dates, counts)),
    }}}


def test_piloto_parcial_no_cierra_el_censo():
    payload = {"c1": contract(["d1", "d2"], [8, 10])}
    report = audit(payload, expected_days=4)
    assert report["status"] == "INSUFFICIENT"
    assert report["observed_unique_days"] == 2
    assert "cobertura insuficiente: 2/4 sesiones" in report["problems"]
    assert report["indicators"]["BigTrap2"]["mean_per_day"] == 9


def test_censo_completo_agrega_numerador_y_dias_no_medias_de_contrato():
    payload = {
        "c1": contract(["d1"], [10]),
        "c2": contract(["d2", "d3", "d4"], [1, 2, 3]),
    }
    report = audit(payload, expected_days=4)
    assert report["status"] == "COMPLETE"
    assert report["indicators"]["BigTrap2"]["signals"] == 16
    assert report["indicators"]["BigTrap2"]["mean_per_day"] == 4


def test_sesiones_duplicadas_entre_contratos_fallan():
    payload = {
        "c1": contract(["d1", "d2"], [1, 1]),
        "c2": contract(["d2", "d3"], [1, 1]),
    }
    with pytest.raises(CensusAuditError, match="repetidas"):
        audit(payload, expected_days=3)


def test_conteos_o_n_dias_inconsistentes_no_pasan():
    payload = {"c1": contract(["d1", "d2"], [1, -1])}
    payload["c1"]["ind"]["BigTrap2"]["n_dias"] = 9
    report = audit(payload, expected_days=2)
    assert report["status"] == "INSUFFICIENT"
    assert any("n_dias" in x for x in report["problems"])
    assert any("conteos" in x for x in report["problems"])
