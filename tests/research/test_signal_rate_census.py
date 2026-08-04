from __future__ import annotations

import pytest

from diag.tasa_senales.audit_post_sepmin import CensusAuditError, audit
from diag.tasa_senales.census_plan import (
    CensusPlanError,
    build_full_plan,
    build_run_manifest,
)


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


def test_plan_incluye_todas_las_sesiones_sin_muestreo_y_ordenadas():
    days = [
        {"fecha": "2026-02-02", "archivo": "b.parquet"},
        {"fecha": "2026-01-03", "archivo": "a.parquet"},
        {"fecha": "2026-01-02", "archivo": "a.parquet"},
    ]
    assert build_full_plan(days) == [
        ("a.parquet", ["2026-01-02", "2026-01-03"]),
        ("b.parquet", ["2026-02-02"]),
    ]


def test_plan_falla_si_una_sesion_aparece_en_dos_contratos():
    days = [
        {"fecha": "2026-01-02", "archivo": "a.parquet"},
        {"fecha": "2026-01-02", "archivo": "b.parquet"},
    ]
    with pytest.raises(CensusPlanError, match="aparece en contratos"):
        build_full_plan(days)


def test_run_manifest_declara_cobertura_configuracion_y_cero_outcomes():
    plan = [("a.parquet", ["d1", "d2"]), ("b.parquet", ["d3"])]
    manifest = build_run_manifest(
        plan=plan,
        universe_sha256="a" * 64,
        output_sha256="b" * 64,
        code_commit="c" * 40,
        universe_info={"descartados_holdout": 5,
                       "descartados_cuarentena": 2},
        indicators=["BigTrap2", "Gaps2"],
        generated_utc="2026-08-04T03:00:00Z",
    )
    assert manifest["schema_version"] == "signal_rate_census_run_v1"
    assert manifest["session_count"] == 3
    assert manifest["configuration"]["outcomes_accessed"] is False
    assert manifest["configuration"]["sep_min_minutes"] == 120
    assert manifest["indicators"] == ["BigTrap2", "Gaps2"]
