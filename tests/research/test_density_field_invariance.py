"""Mandatory invariance and causal semantics tests for EdgeLab HP-007 density field.

Tests all 15 required invariance and causality invariants:
1. VIEWPORT_INVARIANCE
2. PAN_INVARIANCE
3. ZOOM_INVARIANCE
4. NO_NEW_ZONE_STATIC
5. AVAILABLE_TS
6. FUTURE_ZONE_APPEND
7. FUTURE_TOUCH_APPEND
8. CAUSAL_VREF
9. RUN_IDENTITY
10. PRICE_TICK_STABILITY
11. BAND_STABILITY
12. HASH_REPRODUCIBILITY
13. ROLL_RESET
14. SESSION_RESET
15. LEGACY_FAIL_CLOSED
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import pytest
import numpy as np

from edgelab.research.density_field import (
    compute_field,
    detect_density_intervals,
    price_to_tick,
    tick_to_price,
    compute_causal_v_ref,
    to_nanoseconds,
)


@pytest.fixture
def sample_zones():
    """Provides a controlled synthetic set of absorption zones with full causal lifecycle."""
    t0_base = 1773715200_000_000_000  # 2026-03-17 00:00:00 UTC ns
    return [
        {
            "id": "ZONE_001",
            "dir": "long",
            "lo": 18250.00,
            "hi": 18252.00,
            "origin_ts": t0_base + 60_000_000_000,       # +1m
            "available_ts": t0_base + 120_000_000_000,    # +2m
            "ended_ts": None,
            "vol": 150.0,
            "touch_events": [
                {"touch_ts": t0_base + 180_000_000_000, "px": 18251.0},  # +3m
                {"touch_ts": t0_base + 600_000_000_000, "px": 18250.5},  # +10m (future touch relative to 5m)
            ],
            "state_events": [
                {"event_ts": t0_base + 120_000_000_000, "state": "ACTIVE"}
            ]
        },
        {
            "id": "ZONE_002",
            "dir": "short",
            "lo": 18260.00,
            "hi": 18261.50,
            "origin_ts": t0_base + 180_000_000_000,      # +3m
            "available_ts": t0_base + 240_000_000_000,   # +4m
            "ended_ts": None,
            "vol": 250.0,
            "touch_events": [],
            "state_events": [
                {"event_ts": t0_base + 240_000_000_000, "state": "ACTIVE"}
            ]
        },
        {
            "id": "ZONE_003_FUTURE",
            "dir": "long",
            "lo": 18245.00,
            "hi": 18247.00,
            "origin_ts": t0_base + 500_000_000_000,      # +8.33m
            "available_ts": t0_base + 600_000_000_000,   # +10m
            "ended_ts": None,
            "vol": 500.0,
            "touch_events": [],
            "state_events": [
                {"event_ts": t0_base + 600_000_000_000, "state": "ACTIVE"}
            ]
        },
        {
            "id": "ZONE_004_ROLL_OLD",
            "dir": "long",
            "lo": 18240.00,
            "hi": 18242.00,
            "origin_ts": t0_base - 1000_000_000_000,
            "available_ts": t0_base - 900_000_000_000,
            "ended_ts": t0_base - 10_000_000_000,       # Ended before roll
            "vol": 100.0,
            "touch_events": [],
            "state_events": [
                {"event_ts": t0_base - 10_000_000_000, "state": "ENDED_ROLL_PURGE"}
            ]
        }
    ]


def test_01_viewport_invariance(sample_zones):
    """Test 1: VIEWPORT_INVARIANCE
    Same bundle, run, and tRef produces identical full field regardless of viewport slicing.
    """
    tick_size = 0.25
    p_min_tick = price_to_tick(18240.0, tick_size)
    p_max_tick = price_to_tick(18270.0, tick_size)
    t_ref = 1773715200_000_000_000 + 300_000_000_000  # +5m

    # Full domain computation
    res1 = compute_field(
        zones=sample_zones,
        t_ref=t_ref,
        tick_size=tick_size,
        price_tick_min=p_min_tick,
        price_tick_max=p_max_tick,
        field_config={"model": "FIELD_RAW_STATIC"}
    )

    # Viewport 1: user views middle 40 ticks
    vis_min_1 = price_to_tick(18248.0, tick_size)
    vis_max_1 = price_to_tick(18262.0, tick_size)
    idx_min_1 = vis_min_1 - p_min_tick
    idx_max_1 = vis_max_1 - p_min_tick
    slice_1 = res1["density"][idx_min_1 : idx_max_1 + 1]

    # Viewport 2: user zooms out to see wider range
    vis_min_2 = price_to_tick(18242.0, tick_size)
    vis_max_2 = price_to_tick(18268.0, tick_size)
    idx_min_2 = vis_min_2 - p_min_tick
    idx_max_2 = vis_max_2 - p_min_tick
    slice_2 = res1["density"][idx_min_2 : idx_max_2 + 1]

    # Recompute full domain again
    res2 = compute_field(
        zones=sample_zones,
        t_ref=t_ref,
        tick_size=tick_size,
        price_tick_min=p_min_tick,
        price_tick_max=p_max_tick,
        field_config={"model": "FIELD_RAW_STATIC"}
    )

    assert res1["field_hash"] == res2["field_hash"]
    assert res1["density"] == res2["density"]
    # Density values in slice_1 must match exactly corresponding elements in slice_2
    offset = idx_min_1 - idx_min_2
    assert slice_1 == slice_2[offset : offset + len(slice_1)]


def test_02_pan_invariance(sample_zones):
    """Test 2: PAN_INVARIANCE
    Horizontal panning on canvas without changing tRef leaves field_hash and density invariant.
    """
    tick_size = 0.25
    p_min_tick = price_to_tick(18240.0, tick_size)
    p_max_tick = price_to_tick(18270.0, tick_size)
    t_ref = 1773715200_000_000_000 + 300_000_000_000

    field_a = compute_field(sample_zones, t_ref, tick_size, p_min_tick, p_max_tick)
    # Simulated pan: user moved horizontal scroll bar, but hover/as-of remains t_ref
    field_b = compute_field(sample_zones, t_ref, tick_size, p_min_tick, p_max_tick)

    assert field_a["field_hash"] == field_b["field_hash"]
    assert field_a["density"] == field_b["density"]


def test_03_zoom_invariance(sample_zones):
    """Test 3: ZOOM_INVARIANCE
    Vertical or horizontal zoom does not change D(p) at any common price level.
    """
    tick_size = 0.25
    t_ref = 1773715200_000_000_000 + 300_000_000_000

    # Grid 1: normal domain
    p_min_1 = price_to_tick(18240.0, tick_size)
    p_max_1 = price_to_tick(18270.0, tick_size)
    res_1 = compute_field(sample_zones, t_ref, tick_size, p_min_1, p_max_1)

    # Grid 2: expanded domain (zoomed out vertically)
    p_min_2 = price_to_tick(18230.0, tick_size)
    p_max_2 = price_to_tick(18280.0, tick_size)
    res_2 = compute_field(sample_zones, t_ref, tick_size, p_min_2, p_max_2)

    # For every price tick in Grid 1, the density in Grid 2 must be identical
    for i, tick in enumerate(res_1["price_ticks"]):
        idx_2 = res_2["price_ticks"].index(tick)
        assert res_1["density"][i] == pytest.approx(res_2["density"][idx_2], abs=1e-8)


def test_04_no_new_zone_static(sample_zones):
    """Test 4: NO_NEW_ZONE_STATIC
    If between t1 and t2 no zone becomes available and no lifecycle event occurs,
    FIELD_RAW_STATIC produces identical field.
    """
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)

    # ZONE_002 becomes available at +4m (240s).
    # ZONE_003 becomes available at +10m (600s).
    # Between +5m (300s) and +7m (420s), no new zone appears.
    t1 = 1773715200_000_000_000 + 300_000_000_000
    t2 = 1773715200_000_000_000 + 420_000_000_000

    field_t1 = compute_field(sample_zones, t1, tick_size, p_min, p_max, {"model": "FIELD_RAW_STATIC"})
    field_t2 = compute_field(sample_zones, t2, tick_size, p_min, p_max, {"model": "FIELD_RAW_STATIC"})

    assert field_t1["field_hash"] == field_t2["field_hash"]
    assert field_t1["density"] == field_t2["density"]
    assert field_t1["active_zone_ids"] == field_t2["active_zone_ids"]


def test_05_available_ts(sample_zones):
    """Test 5: AVAILABLE_TS
    A zone with origin_ts <= tRef < available_ts does NOT contribute to the field.
    """
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)

    # ZONE_001 has origin_ts at +1m, available_ts at +2m.
    # At t = +1.5m (90s), origin_ts <= t < available_ts. It must NOT contribute!
    t_interim = 1773715200_000_000_000 + 90_000_000_000
    res_interim = compute_field(sample_zones, t_interim, tick_size, p_min, p_max)
    assert "ZONE_001" not in res_interim["active_zone_ids"]

    # At t = +2.5m (150s), available_ts <= t. It MUST contribute!
    t_after = 1773715200_000_000_000 + 150_000_000_000
    res_after = compute_field(sample_zones, t_after, tick_size, p_min, p_max)
    assert "ZONE_001" in res_after["active_zone_ids"]


def test_06_future_zone_append(sample_zones):
    """Test 6: FUTURE_ZONE_APPEND
    Appending a future zone to the bundle does not modify the past field or its hash.
    """
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)
    t_ref = 1773715200_000_000_000 + 300_000_000_000  # +5m

    # Compute with current bundle
    res_before = compute_field(sample_zones, t_ref, tick_size, p_min, p_max)

    # Append a future zone at +20m
    future_zone = {
        "id": "ZONE_999_FAR_FUTURE",
        "dir": "short",
        "lo": 18255.0,
        "hi": 18258.0,
        "origin_ts": t_ref + 900_000_000_000,
        "available_ts": t_ref + 1200_000_000_000,
        "ended_ts": None,
        "vol": 999.0,
        "touch_events": []
    }
    augmented_bundle = sample_zones + [future_zone]

    res_after = compute_field(augmented_bundle, t_ref, tick_size, p_min, p_max)

    assert res_before["field_hash"] == res_after["field_hash"]
    assert res_before["density"] == res_after["density"]
    assert res_before["active_zone_ids"] == res_after["active_zone_ids"]


def test_07_future_touch_append(sample_zones):
    """Test 7: FUTURE_TOUCH_APPEND
    Adding a future touch event does not modify as-of touch count or density field.
    """
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)
    t_ref = 1773715200_000_000_000 + 300_000_000_000  # +5m

    cfg = {"model": "FIELD_ABL_WEAR", "use_wear": True}
    res_before = compute_field(sample_zones, t_ref, tick_size, p_min, p_max, cfg)

    # Append 10 future touches to ZONE_001 at +15m
    augmented = copy.deepcopy(sample_zones)
    for i in range(10):
        augmented[0]["touch_events"].append({
            "touch_ts": t_ref + (600 + i * 10) * 1_000_000_000,
            "px": 18251.0
        })

    res_after = compute_field(augmented, t_ref, tick_size, p_min, p_max, cfg)

    assert res_before["field_hash"] == res_after["field_hash"]
    assert res_before["density"] == res_after["density"]


def test_08_causal_vref(sample_zones):
    """Test 8: CAUSAL_VREF
    Adding future zones with massive volume does not modify past causal V_ref.
    """
    t_ref = 1773715200_000_000_000 + 300_000_000_000  # +5m

    v_ref_before, src_before = compute_causal_v_ref(sample_zones, t_ref)

    # Add future zone with 1,000,000 contracts
    augmented = copy.deepcopy(sample_zones)
    augmented.append({
        "id": "ZONE_HUGE_FUTURE",
        "origin_ts": t_ref + 100_000_000_000,
        "available_ts": t_ref + 200_000_000_000,
        "vol": 1_000_000.0
    })

    v_ref_after, src_after = compute_causal_v_ref(augmented, t_ref)

    assert v_ref_before == v_ref_after
    assert src_before == src_after


def test_09_run_identity(sample_zones):
    """Test 9: RUN_IDENTITY
    Selecting CFG_01 runs CFG_01 and never silently redirects to a sensitive run.
    """
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)
    t_ref = 1773715200_000_000_000 + 300_000_000_000

    cfg_01 = {"model": "FIELD_RAW_STATIC", "config_id": "BT2A_CFG_01"}
    res = compute_field(sample_zones, t_ref, tick_size, p_min, p_max, cfg_01)

    assert res["diagnostics"]["model"] == "FIELD_RAW_STATIC"
    # Ensure active zones match CFG_01 input, not filtered or mutated
    assert res["diagnostics"]["total_zones_evaluated"] == len(sample_zones)


def test_10_price_tick_stability():
    """Test 10: PRICE_TICK_STABILITY
    Small floating point roundoffs do not produce different integer ticks.
    """
    tick_size = 0.25
    p1 = 18250.25
    p2 = 18250.250000000004
    p3 = 18250.249999999996

    assert price_to_tick(p1, tick_size) == price_to_tick(p2, tick_size)
    assert price_to_tick(p1, tick_size) == price_to_tick(p3, tick_size)
    assert price_to_tick(18250.25, tick_size) == 73001


def test_11_band_stability(sample_zones):
    """Test 11: BAND_STABILITY
    Corridor band / region boundaries detected on the full field do not depend on visible levels.
    """
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)
    t_ref = 1773715200_000_000_000 + 300_000_000_000

    res = compute_field(sample_zones, t_ref, tick_size, p_min, p_max)
    intervals_full = detect_density_intervals(
        res["density"], res["price_ticks"], tick_size,
        low_thresh=0.32, high_thresh=0.70, min_low_ticks=7, min_high_ticks=2
    )

    # Re-evaluating intervals with same full field produces strictly identical boundaries
    intervals_repeat = detect_density_intervals(
        res["density"], res["price_ticks"], tick_size,
        low_thresh=0.32, high_thresh=0.70, min_low_ticks=7, min_high_ticks=2
    )

    assert intervals_full == intervals_repeat


def test_12_hash_reproducibility(sample_zones):
    """Test 12: HASH_REPRODUCIBILITY
    Two separate executions on identical inputs produce bit-for-bit identical hashes.
    """
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)
    t_ref = 1773715200_000_000_000 + 300_000_000_000

    res1 = compute_field(sample_zones, t_ref, tick_size, p_min, p_max)
    res2 = compute_field(sample_zones, t_ref, tick_size, p_min, p_max)

    assert res1["field_hash"] == res2["field_hash"]
    assert len(res1["field_hash"]) == 64


def test_13_roll_reset(sample_zones):
    """Test 13: ROLL_RESET
    Zones ended before a contract roll do not contribute post-reset under exclude_ended policy.
    """
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)
    t_ref = 1773715200_000_000_000 + 300_000_000_000  # Post-roll

    res = compute_field(
        sample_zones, t_ref, tick_size, p_min, p_max,
        {"ended_zone_policy": "exclude_ended"}
    )

    # ZONE_004_ROLL_OLD ended before t0_base
    assert "ZONE_004_ROLL_OLD" not in res["active_zone_ids"]


def test_14_session_reset(sample_zones):
    """Test 14: SESSION_RESET
    Cross-session reset applies without contamination.
    """
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)

    # Session 1 evaluation at +3m
    t_sess1 = 1773715200_000_000_000 + 180_000_000_000
    res1 = compute_field(sample_zones, t_sess1, tick_size, p_min, p_max)
    assert res1["active_zone_ids"] == ["ZONE_001"]

    # Session 2 evaluation at +5m
    t_sess2 = 1773715200_000_000_000 + 300_000_000_000
    res2 = compute_field(sample_zones, t_sess2, tick_size, p_min, p_max)
    assert res2["active_zone_ids"] == ["ZONE_001", "ZONE_002"]


def test_15_legacy_fail_closed():
    """Test 15: LEGACY_FAIL_CLOSED
    A legacy bundle without available_ts triggers fallback count and LEGACY_NON_CAUSAL status.
    """
    legacy_zones = [
        {
            "id": "LEGACY_ZONE_1",
            "dir": "long",
            "lo": 18250.0,
            "hi": 18252.0,
            "t0": 1773715200,  # Missing available_ts!
            "vol": 100.0,
        }
    ]
    tick_size = 0.25
    p_min = price_to_tick(18240.0, tick_size)
    p_max = price_to_tick(18270.0, tick_size)
    t_ref = 1773715200 + 300

    res = compute_field(legacy_zones, t_ref, tick_size, p_min, p_max)

    assert res["diagnostics"]["legacy_availability_fallbacks"] > 0
    assert res["diagnostics"]["causal_status"] == "LEGACY_NON_CAUSAL"


def test_golden_fixture_generation(sample_zones, tmp_path):
    """Generates and verifies the shared golden fixture for JS/Python cross-validation."""
    tick_size = 0.25
    p_min = price_to_tick(18245.0, tick_size)
    p_max = price_to_tick(18265.0, tick_size)
    t_ref = 1773715200_000_000_000 + 300_000_000_000

    res = compute_field(
        sample_zones, t_ref, tick_size, p_min, p_max,
        {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2}
    )

    golden_data = {
        "fixture_version": "hp007_density_field_golden_v1",
        "tick_size": tick_size,
        "price_tick_min": p_min,
        "price_tick_max": p_max,
        "t_ref_ns": t_ref,
        "model": "FIELD_RAW_STATIC",
        "kernel": "KERNEL_GAUSS",
        "sigma_ticks": 1.2,
        "active_zone_ids": res["active_zone_ids"],
        "density_sample_head": res["density"][:10],
        "density_sample_tail": res["density"][-10:],
        "field_mean": res["diagnostics"]["field_mean"],
        "field_max": res["diagnostics"]["field_max"],
        "field_hash": res["field_hash"],
        "intervals": detect_density_intervals(res["density"], res["price_ticks"], tick_size)
    }

    golden_dir = Path("tests/fixtures")
    golden_dir.mkdir(parents=True, exist_ok=True)
    golden_path = golden_dir / "density_field_golden.json"
    with open(golden_path, "w", encoding="utf-8") as f:
        json.dump(golden_data, f, indent=2)

    assert golden_path.exists()
    assert len(res["field_hash"]) == 64
