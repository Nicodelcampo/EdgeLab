from __future__ import annotations

import json
import os

import pytest

from edgelab.bridge import coordinate_store, identity, store
from edgelab.bridge.indicators import REGISTRY
from edgelab.bridge.ticks import make_synthetic


def _result(created_ms=1780272000000):
    return {
        "header": "event_seq,event_type,unix_ms,zone_id",
        "csv_lines": [f"7,ZONE_CREATED,{created_ms},Z1"],
        "zones": [{
            "id": "Z1",
            "created_ms": created_ms,
            "bottom": 99.75,
            "top": 100.25,
            "kind": "poc_zone",
            "state": "EXPIRED",
            "touches": 99,
            "ended_ms": created_ms + 1000,
        }],
    }


def _meta():
    return {
        "run_id": "run1",
        "dataset_id": "data1",
        "kernel_id": "kernel1",
        "config_id": "config1",
        "indicator": "VolTicksPOC2",
        "instrument": "GC",
        "contract": "GC 06-26",
        "bar_key": "time_1",
    }


def test_projection_is_point_in_time_and_non_directional():
    rows = coordinate_store.build_coordinate_rows(
        kernel_result=_result(), tick_size=0.25, **_meta()
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["created_event_seq"] == 7
    assert row["available_event_seq"] == 7
    assert row["direction"] is None
    assert row["side"] == "none"
    assert not coordinate_store.FORBIDDEN_FUTURE_FIELDS.intersection(row)
    assert row["lower_tick"] == 399
    assert row["upper_tick"] == 401


def test_missing_creation_event_fails_closed():
    result = _result()
    result["csv_lines"] = []
    with pytest.raises(ValueError, match="sin evento causal"):
        coordinate_store.build_coordinate_rows(
            kernel_result=result, tick_size=0.25, **_meta()
        )


def test_holdout_row_is_rejected():
    with pytest.raises(ValueError, match="HOLDOUT_DATA_DETECTED"):
        coordinate_store.build_coordinate_rows(
            kernel_result=_result(created_ms=1782864000000),
            tick_size=0.25,
            **_meta(),
        )


def test_atomic_publication_is_idempotent_and_immutable(tmp_path):
    rows = coordinate_store.build_coordinate_rows(
        kernel_result=_result(), tick_size=0.25, **_meta()
    )
    manifest = {**_meta(), "counts": {"n_zones": 1}}
    first = coordinate_store.publish_coordinates(
        tmp_path, rows=rows, run_manifest=manifest,
        parity_state="parity_exact",
    )
    second = coordinate_store.publish_coordinates(
        tmp_path, rows=rows, run_manifest=manifest,
        parity_state="parity_exact",
    )
    assert first == second
    pdir = coordinate_store.coordinate_partition_dir(
        tmp_path, instrument="GC", contract="GC 06-26",
        indicator="VolTicksPOC2", kernel_id="kernel1", bar_key="time_1",
        config_id="config1", run_id="run1",
    )
    assert os.path.exists(os.path.join(pdir, "coordinates.parquet"))
    changed = [dict(rows[0], session_id="2026-06-02")]
    with pytest.raises(store.DeterminismError):
        coordinate_store.publish_coordinates(
            tmp_path, rows=changed, run_manifest=manifest,
            parity_state="parity_exact",
        )


def test_parity_pending_cannot_publish(tmp_path):
    rows = coordinate_store.build_coordinate_rows(
        kernel_result=_result(), tick_size=0.25, **_meta()
    )
    with pytest.raises(ValueError, match="paridad no autorizada"):
        coordinate_store.publish_coordinates(
            tmp_path, rows=rows, run_manifest={**_meta(), "counts": {}},
            parity_state="parity_pending",
        )


def test_bt2a_adapter_fulfils_bridge_contract_and_identity():
    module = REGISTRY["BigTrap2Absorption"]
    ticks = make_synthetic(n_sessions=1, ticks_per_session=200)
    result = module.run(ticks, params={"AbsorptionPct": 90.0})
    assert {"header", "csv_lines", "events", "zones", "params_line"} <= set(result)
    for zone in result["zones"]:
        assert zone["bottom"] is not None and zone["top"] is not None
    kernel_id = identity.kernel_id("BigTrap2Absorption")
    a = identity.config_id(
        "BigTrap2Absorption", {"AbsorptionPct": 90.0}, "tick_25", "UTC", kernel_id
    )
    b = identity.config_id(
        "BigTrap2Absorption", {"AbsorptionPct": 95.0}, "tick_25", "UTC", kernel_id
    )
    assert a != b


def test_catalogs_are_target_free_and_failed_indicators_disabled():
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    with open(os.path.join(root, "specs", "indicator_parity_catalog_v1.json"),
              encoding="utf-8") as fh:
        parity = json.load(fh)
    with open(os.path.join(root, "specs", "indicator_config_catalog_v1.json"),
              encoding="utf-8") as fh:
        configs = json.load(fh)
    assert parity["target_free"] is True
    assert configs["target_free"] is True
    states = {row["indicator"]: row["state"] for row in parity["entries"]}
    assert states["aVolCellPOI2"] == "parity_failed"
    assert states["aVolClusterPOI"] == "parity_under_review"
    assert all(row["indicator"] not in {"aVolCellPOI2", "aVolClusterPOI"}
               for row in configs["entries"] if row["enabled"])
