# -*- coding: utf-8 -*-
"""Truth-known tests de ZAMR-1. No usan datos reales ni outcomes."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from edgelab.research.zamr1 import parameter_dag as dag
from edgelab.research.zamr1 import structural_contract as sc

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "specs/zamr1_structural_contract_v0.json").read_text("utf-8"))
CUTOFF = CONTRACT["firewall"]["max_allowed_timestamp_ns_exclusive"]


def test_bigtrap_defaults_son_validos():
    assert dag.validate_param_set("BigTrap2", {}) == []


def test_parametro_visual_es_fail():
    issues = dag.validate_param_set("BigTrap2", {"AutoScale": True})
    assert any(item.code == "FORBIDDEN_PARAMETER" for item in issues)


def test_export_floor_debe_cubrir_umbral_offline():
    issues = dag.validate_param_set(
        "BigTrap2", {"min_export_volume": 40.0, "min_trap_volume": 30.0}
    )
    assert any(item.code == "EXPORT_FLOOR_TOO_HIGH" for item in issues)


def test_hash_canonico_no_depende_del_orden():
    a = dag.param_set_id("BigTrap2", {"imbalance_ratio": 2.0, "ticks_per_row": 2})
    b = dag.param_set_id("BigTrap2", {"ticks_per_row": 2, "imbalance_ratio": 2.0})
    assert a == b


def test_avol_exige_soporte_de_cola():
    issues = dag.validate_param_set(
        "aVolCellPOI2",
        {"detection_percentile": 99.75, "min_cell_samples": 1000},
    )
    assert any(item.code == "INSUFFICIENT_TAIL_SUPPORT" for item in issues)
    assert dag.validate_param_set(
        "aVolCellPOI2",
        {"detection_percentile": 99.75, "min_cell_samples": 4000},
    ) == []


def test_avol_no_varia_rama_inactiva():
    issues = dag.validate_param_set(
        "aVolCellPOI2",
        {"detection_method": "RobustZ", "detection_percentile": 98.0},
    )
    assert any(item.code == "INACTIVE_PARAMETER_VARIED" for item in issues)


def test_barrido_unifamiliar_rechaza_cruce():
    issues = dag.validate_single_family(
        "BigTrap2", {"ticks_per_row": 2, "imbalance_ratio": 2.0}, "footprint"
    )
    assert any(item.code == "CROSS_FAMILY_VARIATION" for item in issues)


def _manifest():
    return {
        "dataset_id": "synthetic",
        "dataset_schema_version": "zamr1_structural_contract_v0",
        "code_commit": "a" * 40,
        "code_dirty": False,
        "builder_id": "truth-known",
        "source_data_manifest_sha256": "b" * 64,
        "parameter_registry_sha256": "c" * 64,
        "instrument_manifest_sha256": "d" * 64,
        "created_at_utc": "2026-08-12T23:00:00Z",
        "research_cutoff_utc": "2026-06-30T22:00:00Z",
        "outcomes_accessed": False,
        "pnl_accessed": False,
        "holdout_included": False,
        "license_decision": "DERIVED_ONLY",
        "pilot_stage": "Z1_BIGTRAP2_DEFAULTS",
    }


def _tables(n_sessions=20):
    event_rows = []
    zone_rows = []
    for i in range(n_sessions):
        session = "6E|09-26|2026-06-%02d" % (i + 1)
        t = 1_700_000_000_000_000_000 + i * 1_000
        event_rows.append({
            "event_key": "e%d" % i, "session_key": session, "instrument": "6E",
            "contract": "09-26", "session_date": "2026-06-%02d" % (i + 1),
            "indicator_id": "BigTrap2", "indicator_version": "2.2",
            "bar_spec": "tick:25", "ticks_per_bar": 25, "param_set_id": "p",
            "source_run_id": "r", "event_id": str(i), "zone_id": str(i),
            "event_type": "ZONE_CREATED", "side": "trapped_buyers",
            "event_time_ns": t, "bar_end_ns": t, "available_at_ns": t,
            "anchor_price_tick": 100, "zone_lo_tick": 101, "zone_hi_tick": 102,
            "strength": 1.0, "aggressive_volume": 30.0, "bar_volume": 100.0,
            "oracle_parity_status": "PASS",
        })
        zone_rows.append({
            "zone_key": "z%d" % i, "session_key": session, "instrument": "6E",
            "contract": "09-26", "session_date": "2026-06-%02d" % (i + 1),
            "indicator_id": "BigTrap2", "indicator_version": "2.2",
            "bar_spec": "tick:25", "ticks_per_bar": 25, "param_set_id": "p",
            "source_run_id": "r", "zone_id": str(i), "side": "trapped_buyers",
            "created_at_ns": t, "available_at_ns": t, "ended_at_ns": None,
            "state": "ACTIVE", "end_reason": None, "zone_lo_tick": 101,
            "zone_hi_tick": 102, "strength": 1.0, "touch_count": 0,
            "oracle_parity_status": "PASS",
        })
    return pd.DataFrame(event_rows), pd.DataFrame(zone_rows)


def test_dataset_sintetico_valido_pasa():
    events, zones = _tables()
    report = sc.validate_structural_dataset(
        manifest=_manifest(), events=events, zones=zones, contract=CONTRACT
    )
    assert report.passed, report.to_dict()


def test_holdout_es_fail():
    events, zones = _tables()
    events.loc[0, "available_at_ns"] = CUTOFF
    report = sc.validate_structural_dataset(
        manifest=_manifest(), events=events, zones=zones, contract=CONTRACT
    )
    assert not report.passed
    assert any(item.name == "firewall[events_long]" and not item.passed for item in report.checks)


def test_outcome_column_es_fail():
    events, zones = _tables()
    zones["future_return"] = 0.0
    report = sc.validate_structural_dataset(
        manifest=_manifest(), events=events, zones=zones, contract=CONTRACT
    )
    assert not report.passed


def test_manifest_que_abre_outcomes_es_fail():
    events, zones = _tables()
    manifest = _manifest()
    manifest["outcomes_accessed"] = True
    report = sc.validate_structural_dataset(
        manifest=manifest, events=events, zones=zones, contract=CONTRACT
    )
    assert not report.passed


def test_geometria_invertida_es_fail():
    events, zones = _tables()
    zones.loc[0, "zone_lo_tick"] = 103
    report = sc.validate_structural_dataset(
        manifest=_manifest(), events=events, zones=zones, contract=CONTRACT
    )
    assert not report.passed


def test_reporte_vacio_no_pasa():
    assert sc.ValidationReport().passed is False
