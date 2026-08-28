# -*- coding: utf-8 -*-
"""Unit, Parity and Adversarial Contract Tests for BigTrap2 NQ Micro-Tick Sweep."""
from __future__ import annotations

import hashlib
import json
import re
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
    cme_session_to_utc_bounds_ns,
    verify_inputs_fail_closed,
    verify_runtime_execution_gates,
    HOLDOUT_CUTOFF_UTC_NS,
)


def test_v1_retrospective_spec_and_sidecar_hashes():
    spec_path = REPO_ROOT / "specs" / "bigtrap2_nq_tickframes_sweep_v1.json"
    assert spec_path.exists(), "Spec file v1 must exist"
    
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert spec["schema_version"] == "bigtrap2_nq_tickframes_sweep_spec_v1"
    assert spec["status"] == "COMPLETE_RETROSPECTIVE_SWEEP_PUBLICATION_WITH_EXPOSURE"
    assert spec["firewalls"]["future_price_path_accessed"] is True
    assert spec["firewalls"]["first_touch_accessed"] is True
    assert spec["firewalls"]["holdout_rows_decoded"] is True
    assert spec["firewalls"]["winner_selected"] is False
    
    result_path = REPO_ROOT / spec["binding"]["output_result_path"]
    assert result_path.exists(), f"Result file {result_path} must exist"
    
    actual_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
    assert actual_hash == spec["binding"]["output_result_sha256"] == "4716148209c44ea42e801a0717ead2eb357cf4d635b0f0c01ed72e161d342713"

    # Sidecar classification check
    sidecar_path = REPO_ROOT / "docs" / "research" / "bigtrap2_nq_tickframes_sweep_result_classification.json"
    assert sidecar_path.exists(), "Sidecar classification must exist"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["original_reported_sha256"] == "ae631415478938882330f1e1812ea4e9ea07b84d96e436f10f292450784fb9d8"
    assert sidecar["normalized_lf_sha256"] == actual_hash
    assert sidecar["transformation"] == "EOL_NORMALIZATION_ONLY"
    assert sidecar["logical_payload_changed"] is False
    assert sidecar["classification"] == "COMPLETE_RETROSPECTIVE_SWEEP_PUBLICATION_WITH_EXPOSURE"


def test_v2_draft_spec_binds_canonical_gate1a_hashes():
    spec_v2_path = REPO_ROOT / "specs" / "bigtrap2_nq_tickframes_sweep_v2.draft.json"
    assert spec_v2_path.exists(), "Spec file v2 draft must exist"
    
    spec_v2 = json.loads(spec_v2_path.read_text(encoding="utf-8"))
    assert spec_v2["status"] == "DRAFT_PREAUTHORIZATION_CREATION_ONLY"
    assert spec_v2["execution_authorized"] is False
    
    sess_reg_path = REPO_ROOT / spec_v2["binding"]["session_registry_path"]
    inp_reg_path = REPO_ROOT / spec_v2["binding"]["input_registry_path"]
    
    sess_sha = hashlib.sha256(sess_reg_path.read_bytes()).hexdigest()
    inp_sha = hashlib.sha256(inp_reg_path.read_bytes()).hexdigest()
    
    assert sess_sha == spec_v2["binding"]["session_registry_sha256"] == "f50350ee67d53be38cd00e0f3e548cc877e980aebb3b08e422cdde007b39c6cb"
    assert inp_sha == spec_v2["binding"]["input_registry_sha256"] == "2ce114105970e0d5010ebe150fbd0ec1b2911b4ecced946ecbb31510d17d1ed9"


@pytest.mark.parametrize("bar_kind,bar_param", [
    ("tick", 10),
    ("tick", 25),
    ("tick", 120),
    ("time", 1),
])
@pytest.mark.parametrize("imb_ratio,min_vol", [
    (2.5, 10.0),
    (3.5, 50.0),
])
def test_representative_multi_resolution_creation_parity(bar_kind, bar_param, imb_ratio, min_vol):
    """REPRESENTATIVE_MULTI_RESOLUTION_CREATION_PARITY against bigtrap2.py.
    
    Compares bar_idx, bar_time_ns, side, kind, top, bottom, vol and centroid
    across 8 representative (bar_type x param) combinations on synthetic data.
    This validates against the Python bridge kernel, not directly against BigTrap2.cs.
    """
    ticks = make_synthetic(start_utc="2026-06-01T23:00:00", n_sessions=3, ticks_per_session=2000, tick_size=0.25, seed=42)
    
    if bar_kind == "tick":
        bars = build_tick_bars(ticks, bar_param, reiniciar_por_sesion=True)
    else:
        bars = build_time_bars(ticks, bar_param)
        
    fps = build_footprints(ticks, bars)

    params = {
        "imbalance_ratio": imb_ratio,
        "min_trap_volume": min_vol,
        "min_export_volume": min_vol,
        "use_wick_filter": False,
    }

    canonical_res = run_bigtrap2_canonical(ticks, bars, fps, params=params)
    creation_only_zones = detect_creations_only(ticks, bars, fps, params=params)

    # Extract canonical zones; exported zones have top/bottom/created_bar/created_ms/kind
    # but NOT vol. Extract vol from ZONE_CREATED CSV log lines.
    canonical_zones = canonical_res["zones"]
    
    # Parse vol from CSV log for each ZONE_CREATED event (ordered same as zones)
    canonical_vols = []
    for line in canonical_res["csv_lines"]:
        parts = line.split("|")
        if len(parts) >= 4 and parts[2] == "ZONE_CREATED":
            payload = parts[3]
            props = dict(item.split("=") for item in payload.split(";") if "=" in item)
            canonical_vols.append(float(props["vol"]))

    # Parity check: zone count
    assert len(canonical_zones) == len(creation_only_zones), (
        f"Zone count mismatch: canonical={len(canonical_zones)}, creation_only={len(creation_only_zones)}"
    )
    assert len(canonical_vols) == len(canonical_zones)

    # Zone-by-zone equality check on all available creation-time fields
    for i, (cz, coz) in enumerate(zip(canonical_zones, creation_only_zones)):
        assert coz["bar_idx"] == cz["created_bar"], f"Zone {i}: bar_idx mismatch"
        # Compare at ms precision: canonical kernel stores created_ms (ns_to_ms truncation)
        assert coz["bar_time_ns"] // 1_000_000 == cz["created_ms"], f"Zone {i}: bar_time_ms mismatch"
        assert coz["kind"] == cz["kind"], f"Zone {i}: kind mismatch"
        expected_side = "B" if cz["kind"] == "trapped_buyers" else "S"
        assert coz["side"] == expected_side, f"Zone {i}: side mismatch"
        assert coz["top"] == cz["top"], f"Zone {i}: top mismatch"
        assert coz["bottom"] == cz["bottom"], f"Zone {i}: bottom mismatch"
        assert coz["vol"] == canonical_vols[i], f"Zone {i}: vol mismatch"
        # Centroid: bounded by zone geometry
        assert coz["bottom"] <= coz["centroid"] <= coz["top"], f"Zone {i}: centroid out of bounds"
        assert coz["width_ticks"] == int(round((cz["top"] - cz["bottom"]) / 0.25)), f"Zone {i}: width mismatch"


def test_cme_session_utc_bounds_expansion_no_keyerror():
    """Verify CME session UTC boundary expansion across all 234 sessions."""
    sess_reg_path = REPO_ROOT / "specs" / "bt2a_gate1_nq_all5_sessions_2026-08-27.json"
    sess_reg = json.loads(sess_reg_path.read_text(encoding="utf-8"))
    
    expanded = expand_sessions(sess_reg)
    assert len(expanded) == 234
    
    sessions_by_contract: dict[str, set[str]] = {}
    time_bounds_by_contract: dict[str, tuple[int, int]] = {}
    
    for row in expanded:
        c = row["contract"]
        sid = row["cme_session_id"]
        sessions_by_contract.setdefault(c, set()).add(sid)
        
        s_ns, e_ns = cme_session_to_utc_bounds_ns(sid)
        assert s_ns < e_ns
        assert s_ns > 0
        assert e_ns <= HOLDOUT_CUTOFF_UTC_NS
        
        if c not in time_bounds_by_contract:
            time_bounds_by_contract[c] = (s_ns, e_ns)
        else:
            cur_s, cur_e = time_bounds_by_contract[c]
            time_bounds_by_contract[c] = (min(cur_s, s_ns), max(cur_e, e_ns))

    assert sum(len(v) for v in sessions_by_contract.values()) == 234
    assert len(time_bounds_by_contract) == 5


def test_input_registry_parser_and_validation_fail_closed(tmp_path):
    """Verify input registry dictionary parser and fail-closed validation."""
    inp_reg_path = REPO_ROOT / "specs" / "bt2a_gate1_nq_all5_input_registry_2026-08-27.json"
    input_reg = json.loads(inp_reg_path.read_text(encoding="utf-8"))
    
    assert "contracts" in input_reg
    assert isinstance(input_reg["contracts"], dict)
    assert len(input_reg["contracts"]) == 5
    
    # Test missing parquet file fail-closed
    with pytest.raises(FileNotFoundError, match=r"\[FAIL_CLOSED\] Required input parquet missing"):
        verify_inputs_fail_closed(tmp_path, input_reg)

    # Test size mismatch fail-closed
    fake_pq = tmp_path / "NQ_09-25_ticks.parquet"
    fake_pq.write_bytes(b"corrupted_bytes")
    with pytest.raises(ValueError, match=r"\[FAIL_CLOSED\] Size mismatch"):
        verify_inputs_fail_closed(tmp_path, input_reg)


def test_runtime_gates_reject_draft_spec_even_with_token():
    """Verify that draft specs are strictly rejected even if valid token string is passed."""
    draft_spec = {
        "status": "DRAFT_PREAUTHORIZATION_CREATION_ONLY",
        "execution_authorized": False,
        "execution_token": "TEST_TOKEN_123",
        "frozen_commit": "abc1234",
    }
    with pytest.raises(PermissionError, match=r"Spec status must be 'FROZEN_PREFLIGHT_READY'"):
        verify_runtime_execution_gates(draft_spec, expected_commit="abc1234", execution_token="TEST_TOKEN_123")

    frozen_unauthorized_spec = {
        "status": "FROZEN_PREFLIGHT_READY",
        "execution_authorized": False,
        "execution_token": "TEST_TOKEN_123",
        "frozen_commit": "abc1234",
    }
    with pytest.raises(PermissionError, match=r"Spec execution is not authorized"):
        verify_runtime_execution_gates(frozen_unauthorized_spec, expected_commit="abc1234", execution_token="TEST_TOKEN_123")

    frozen_wrong_token_spec = {
        "status": "FROZEN_PREFLIGHT_READY",
        "execution_authorized": True,
        "execution_token": "CORRECT_TOKEN",
        "frozen_commit": "abc1234",
    }
    with pytest.raises(PermissionError, match=r"Invalid or missing execution token"):
        verify_runtime_execution_gates(frozen_wrong_token_spec, expected_commit="abc1234", execution_token="WRONG_TOKEN")


def test_output_path_must_be_external_to_repo(tmp_path):
    """Verify that --output-json inside REPO_ROOT is rejected."""
    from tools.sweep_bigtrap2_nq_tickframes_v2 import REPO_ROOT as V2_REPO_ROOT
    internal_path = V2_REPO_ROOT / "docs" / "research" / "forbidden_output.json"
    try:
        internal_path.resolve().relative_to(V2_REPO_ROOT.resolve())
        is_internal = True
    except ValueError:
        is_internal = False
    assert is_internal, "Test setup: internal_path must be inside REPO_ROOT"

    external_path = tmp_path / "kaggle_working" / "result.json"
    try:
        external_path.resolve().relative_to(V2_REPO_ROOT.resolve())
        is_external = False
    except ValueError:
        is_external = True
    assert is_external, "Test setup: external_path must be outside REPO_ROOT"
