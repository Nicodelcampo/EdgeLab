# -*- coding: utf-8 -*-
"""Contract, parity and Kaggle-envelope tests for the BigTrap2 NQ sweep."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

from edgelab.bridge.indicators.bigtrap2 import run as run_bigtrap2_canonical
from edgelab.bridge.indicators.bigtrap2_creation_only import detect_creations_only
from edgelab.bridge.ticks import make_synthetic
from edgelab.bridge.bars import build_tick_bars, build_time_bars, build_footprints
from tools.build_event_store_all5_v2 import expand_sessions
from tools.sweep_bigtrap2_nq_tickframes_v2 import (
    HOLDOUT_CUTOFF_UTC_NS,
    canonical_sha256,
    cme_session_to_utc_bounds_ns,
    compute_sha256,
    validate_kaggle_runtime,
    verify_inputs_fail_closed,
    verify_package_and_effective_registry,
    verify_runtime_execution_gates,
)


def test_v1_retrospective_spec_and_sidecar_hashes():
    spec = json.loads(
        (REPO_ROOT / "specs/bigtrap2_nq_tickframes_sweep_v1.json").read_text()
    )
    assert spec["status"] == "COMPLETE_RETROSPECTIVE_SWEEP_PUBLICATION_WITH_EXPOSURE"
    assert spec["firewalls"]["future_price_path_accessed"] is True
    assert spec["firewalls"]["first_touch_accessed"] is True
    assert spec["firewalls"]["holdout_rows_decoded"] is True
    assert spec["firewalls"]["winner_selected"] is False
    result_path = REPO_ROOT / spec["binding"]["output_result_path"]
    actual_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
    assert actual_hash == "4716148209c44ea42e801a0717ead2eb357cf4d635b0f0c01ed72e161d342713"
    sidecar = json.loads(
        (REPO_ROOT / "docs/research/bigtrap2_nq_tickframes_sweep_result_classification.json").read_text()
    )
    assert sidecar["original_reported_sha256"] == "ae631415478938882330f1e1812ea4e9ea07b84d96e436f10f292450784fb9d8"
    assert sidecar["normalized_lf_sha256"] == actual_hash
    assert sidecar["transformation"] == "EOL_NORMALIZATION_ONLY"
    assert sidecar["logical_payload_changed"] is False


def _is_hex64(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def test_v2_frozen_is_kaggle_only_and_package_bound():
    spec_path = REPO_ROOT / "specs/bigtrap2_nq_tickframes_sweep_v2.draft.json"
    spec = json.loads(spec_path.read_text())
    assert spec["status"] == "FROZEN_PREFLIGHT_READY"
    assert spec["execution_authorized"] is True
    assert spec["execution_token"] == "AUTHORIZE_RUN_BT2_NQ_TICKFRAMES_SWEEP_V2"
    assert _is_hex64(spec["frozen_commit"])
    assert spec["execution_platform"] == {
        "platform": "KAGGLE",
        "kaggle_only": True,
        "local_heavy_execution_allowed": False,
        "input_root": "/kaggle/input",
        "output_root": "/kaggle/working",
    }
    session_path = REPO_ROOT / spec["binding"]["session_registry_path"]
    source_path = REPO_ROOT / spec["binding"]["source_input_registry_path"]
    assert compute_sha256(session_path) == spec["binding"]["session_registry_sha256"]
    assert compute_sha256(source_path) == spec["binding"]["source_input_registry_sha256"]
    assert _is_hex64(spec["binding"]["package_manifest_sha256"])
    assert _is_hex64(spec["binding"]["effective_input_registry_sha256"])


def test_v2_comparator_selection_rule_is_ex_ante_and_matches_module_defaults():
    """The frozen K_BT2 comparator anchor must trace to values fixed before any
    sweep result exists (module DEFAULTS / GC's already-proven Gate 1 bar size),
    never to a value chosen by looking at this sweep's own output."""
    spec_path = REPO_ROOT / "specs/bigtrap2_nq_tickframes_sweep_v2.draft.json"
    spec = json.loads(spec_path.read_text())
    rule = spec["comparator_selection_rule"]
    from edgelab.bridge.indicators.bigtrap2_creation_only import DEFAULTS as CREATION_DEFAULTS
    assert rule["imbalance_ratio"] == CREATION_DEFAULTS["imbalance_ratio"]
    assert rule["min_trap_volume"] == CREATION_DEFAULTS["min_trap_volume"]
    assert rule["bar_type"] == "tick_25"
    assert rule["selected_cfg_id"] == "tick_25_IMB30_VOL10"
    grid = spec["grid"]
    assert rule["bar_type"] in grid["bar_series_types"]
    assert rule["imbalance_ratio"] in grid["imbalance_ratios"]
    assert rule["min_trap_volume"] in grid["min_trap_volumes"]


@pytest.mark.parametrize("bar_kind,bar_param", [
    ("tick", 10),
    ("tick", 25),
    ("tick", 120),
    ("time", 1),
])
@pytest.mark.parametrize("imbalance_ratio,minimum_volume", [
    (2.5, 10.0),
    (3.5, 50.0),
])
def test_representative_multi_resolution_creation_parity(
    bar_kind, bar_param, imbalance_ratio, minimum_volume
):
    """Representative Python-bridge creation parity; this is not NT8/C# parity."""
    ticks = make_synthetic(
        start_utc="2026-06-01T23:00:00",
        n_sessions=3,
        ticks_per_session=2000,
        tick_size=0.25,
        seed=42,
    )
    bars = (
        build_tick_bars(ticks, bar_param, reiniciar_por_sesion=True)
        if bar_kind == "tick"
        else build_time_bars(ticks, bar_param)
    )
    footprints = build_footprints(ticks, bars)
    params = {
        "imbalance_ratio": imbalance_ratio,
        "min_trap_volume": minimum_volume,
        "min_export_volume": minimum_volume,
        "use_wick_filter": False,
    }
    canonical = run_bigtrap2_canonical(ticks, bars, footprints, params=params)
    creation_only = detect_creations_only(ticks, bars, footprints, params=params)
    canonical_volumes = []
    for line in canonical["csv_lines"]:
        parts = line.split("|")
        if len(parts) >= 4 and parts[2] == "ZONE_CREATED":
            properties = dict(
                item.split("=") for item in parts[3].split(";") if "=" in item
            )
            canonical_volumes.append(float(properties["vol"]))

    assert len(canonical["zones"]) == len(creation_only) == len(canonical_volumes)
    for index, (expected, actual) in enumerate(zip(canonical["zones"], creation_only)):
        assert actual["bar_idx"] == expected["created_bar"], index
        assert actual["bar_time_ns"] // 1_000_000 == expected["created_ms"], index
        assert actual["kind"] == expected["kind"], index
        assert actual["side"] == (
            "B" if expected["kind"] == "trapped_buyers" else "S"
        ), index
        assert actual["top"] == expected["top"], index
        assert actual["bottom"] == expected["bottom"], index
        assert actual["vol"] == canonical_volumes[index], index
        # Centroid is a creation-only geometric invariant; canonical export omits it.
        assert actual["bottom"] <= actual["centroid"] <= actual["top"], index
        assert actual["width_ticks"] == int(
            round((expected["top"] - expected["bottom"]) / 0.25)
        ), index


def test_cme_session_utc_bounds_expansion_no_keyerror():
    registry = json.loads(
        (REPO_ROOT / "specs/bt2a_gate1_nq_all5_sessions_2026-08-27.json").read_text()
    )
    expanded = expand_sessions(registry)
    assert len(expanded) == 234
    sessions: dict[str, set[str]] = {}
    for row in expanded:
        start_ns, end_ns = cme_session_to_utc_bounds_ns(row["cme_session_id"])
        assert 0 < start_ns < end_ns <= HOLDOUT_CUTOFF_UTC_NS
        sessions.setdefault(row["contract"], set()).add(row["cme_session_id"])
    assert sum(map(len, sessions.values())) == 234
    assert len(sessions) == 5


def test_input_registry_validation_fails_closed(tmp_path):
    registry = json.loads(
        (REPO_ROOT / "specs/bt2a_gate1_nq_all5_input_registry_2026-08-27.json").read_text()
    )
    with pytest.raises(FileNotFoundError, match="Required input Parquet missing"):
        verify_inputs_fail_closed(tmp_path, registry)
    fake = tmp_path / "NQ_09-25_ticks.parquet"
    fake.write_bytes(b"corrupt")
    with pytest.raises(RuntimeError, match="Size mismatch"):
        verify_inputs_fail_closed(tmp_path, registry)


def test_runtime_gates_reject_draft_even_with_token():
    draft = {
        "status": "DRAFT_PREAUTHORIZATION_CREATION_ONLY",
        "execution_authorized": False,
        "execution_token": "TOKEN",
        "frozen_commit": "a" * 40,
    }
    with pytest.raises(PermissionError, match="draft specs remain non-executable"):
        verify_runtime_execution_gates(draft, "a" * 40, "TOKEN")

    unauthorized = {
        "status": "FROZEN_PREFLIGHT_READY",
        "execution_authorized": False,
        "execution_token": "TOKEN",
        "frozen_commit": "a" * 40,
    }
    with pytest.raises(PermissionError, match="execution_authorized"):
        verify_runtime_execution_gates(unauthorized, "a" * 40, "TOKEN")


def test_validate_kaggle_runtime_calls_production_gate(tmp_path):
    input_root = tmp_path / "kaggle/input"
    working_root = tmp_path / "kaggle/working"
    data_dir = input_root / "private-dataset"
    input_root.mkdir(parents=True)
    working_root.mkdir(parents=True)
    data_dir.mkdir()
    environment = {"KAGGLE_KERNEL_RUN_TYPE": "Batch"}

    _, output = validate_kaggle_runtime(
        data_dir,
        working_root / "job/result.json",
        input_root=input_root,
        working_root=working_root,
        environment=environment,
    )
    assert output == (working_root / "job/result.json").resolve()

    with pytest.raises(RuntimeError, match="data-dir"):
        validate_kaggle_runtime(
            tmp_path / "local-data",
            working_root / "result.json",
            input_root=input_root,
            working_root=working_root,
            environment=environment,
        )
    with pytest.raises(RuntimeError, match="output-json"):
        validate_kaggle_runtime(
            data_dir,
            tmp_path / "local-output.json",
            input_root=input_root,
            working_root=working_root,
            environment=environment,
        )
    with pytest.raises(RuntimeError, match="attestation"):
        validate_kaggle_runtime(
            data_dir,
            working_root / "result.json",
            input_root=input_root,
            working_root=working_root,
            environment={},
        )


def test_package_manifest_binds_effective_registry_and_physical_inputs(tmp_path):
    data_dir = tmp_path / "dataset"
    data_dir.mkdir()
    parquet = data_dir / "NQ_09-25_ticks.parquet"
    parquet.write_bytes(b"PAR1-test-pre-holdout")
    parquet_sha = compute_sha256(parquet)
    effective = {
        "selected_contracts": ["NQ 09-25"],
        "contracts": {
            "NQ 09-25": {
                "parquet_file": parquet.name,
                "bytes": parquet.stat().st_size,
                "parquet_sha256": parquet_sha,
            }
        },
    }
    effective_path = data_dir / "effective_input_registry.json"
    effective_path.write_text(json.dumps(effective), encoding="utf-8")
    effective_sha = compute_sha256(effective_path)
    source_sha = "a" * 64
    manifest = {
        "schema_version": "edgelab_kaggle_research_package_v1",
        "generated_utc": "2026-08-28T00:00:00Z",
        "dataset_id": "private/test",
        "visibility": "private_only",
        "source_input_registry_file_sha256": source_sha,
        "effective_input_registry_file": effective_path.name,
        "effective_input_registry_file_sha256": effective_sha,
        "holdout_open_utc_ns": HOLDOUT_CUTOFF_UTC_NS,
        "research_max_trade_date": 20260630,
        "research_dataset_holdout_present": False,
        "files": [
            {
                "contract": "NQ 09-25",
                "file": parquet.name,
                "bytes": parquet.stat().st_size,
                "sha256": parquet_sha,
                "ts_max_utc_ns": HOLDOUT_CUTOFF_UTC_NS - 1,
            }
        ],
    }
    manifest["payload_sha256"] = canonical_sha256(manifest)
    manifest_path = data_dir / "kaggle_research_package_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    spec = {
        "binding": {
            "package_manifest_file": manifest_path.name,
            "package_manifest_sha256": compute_sha256(manifest_path),
            "effective_input_registry_file": effective_path.name,
            "effective_input_registry_sha256": effective_sha,
            "source_input_registry_sha256": source_sha,
        },
        "universe": {"contracts": ["NQ 09-25"]},
    }
    _, _, provenance = verify_package_and_effective_registry(data_dir, spec)
    assert provenance["physical_holdout_absence"] is True
    assert provenance["verified_contracts"] == ["NQ 09-25"]

    effective_path.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Effective registry SHA-256 mismatch"):
        verify_package_and_effective_registry(data_dir, spec)
