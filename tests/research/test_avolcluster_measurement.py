# -*- coding: utf-8 -*-
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tools.run_avolcluster_measurement import (
    MeasurementAbort, SessionPanel, first_passage, forward_slice,
    holm_adjust, pick_controls, trigger_direction, validate_panel, wild_cluster,
)

ROOT = Path(__file__).resolve().parents[2]


def spec():
    return json.loads((ROOT / "specs/avolcluster_poi_compression_v1.json").read_text("utf-8"))


def panel_frame(session_id=20260630, bars=130):
    rows = []
    for c in range(5):
        contract = f"GC C{c + 1}"
        for i in range(bars):
            touch = i == 65
            rows.append({
                "instrument": "GC", "contract": contract, "session_id": session_id,
                "bar_index_in_session": i, "ts_utc_ns": 1_000_000_000 * (c * 10000 + i + 100),
                "time_bucket": i // 30, "high_tick": 1002 + (i % 2), "low_tick": 998 - (i % 2),
                "close_tick": 1000, "pre_touch_vol_ticks": 4.0, "is_zone_touch": int(touch),
                "kind": "OFF_PRICE" if touch else None, "zone_id": f"z{c}" if touch else None,
                "created_ts_utc_ns": 1_000_000_000 * (c * 10000 + i + 90) if touch else None,
                "lower_tick": 997 if touch else None, "upper_tick": 999 if touch else None,
                "zone_score": 10.0 if touch else None, "delta_z": 2.5 if touch else 0.0,
                "penetration_ticks": 1.0 if touch else 0.0, "displacement_ticks": 0.0,
                "bt2a_direction": -1 if touch else 0, "bt2_direction": 0,
                "vwap_tick": 999.0, "val_tick": 995.0, "vah_tick": 999.0,
            })
    return pd.DataFrame(rows)


def session_panel(df):
    g = df.sort_values("bar_index_in_session").reset_index(drop=True)
    return SessionPanel(g, {int(v): i for i, v in enumerate(g["bar_index_in_session"])},
                        np.flatnonzero(g["is_zone_touch"].to_numpy(dtype=bool)))


def test_spec_is_draft_fail_closed_and_scientifically_scoped():
    s = spec()
    assert s["status"] == "DRAFT_PREAUTHORIZATION_FAIL_CLOSED"
    assert s["population"]["instrument"] == "GC"
    assert s["detector"]["bar_type"] == "tick_60"
    assert s["detector"]["detection_percentile"] == 98.0
    assert s["epistemic_scope"]["execution_reads_future_price_path"] is False
    assert s["authorization"]["authorized"] is False
    assert s["hypothesis_1_compression"]["n_rand"]["same_session"] is False
    assert s["hypothesis_2_direction"]["composite"]["raw_three_vote_rule_status"].startswith("EXPLORATORY")
    assert len(s["review_blockers"]) >= 8


def test_preflight_components_accept_five_contract_pre_holdout_gc_panel():
    out, diag = validate_panel(panel_frame(), spec())
    assert len(diag["contracts"]) == 5
    assert diag["touch_events"] == 5
    assert int(out["session_id"].max()) == 20260630


def test_holdout_is_rejected_fail_closed():
    with pytest.raises(MeasurementAbort) as exc:
        validate_panel(panel_frame(session_id=20260701), spec())
    assert exc.value.label == "ABSTAIN_HOLDOUT_FIREWALL"


def test_pnl_or_target_columns_are_rejected():
    df = panel_frame(); df["pnl_net"] = 0.0
    with pytest.raises(MeasurementAbort) as exc:
        validate_panel(df, spec())
    assert exc.value.label == "ABSTAIN_INPUT_INTEGRITY"


def test_forward_window_requires_contiguous_same_session_indices():
    df = panel_frame().query("contract == 'GC C1'").copy()
    assert len(forward_slice(session_panel(df), 65, 30)) == 30
    assert forward_slice(session_panel(df[df["bar_index_in_session"] != 70]), 65, 30) is None


def test_conflicting_flow_votes_abstain_event_in_current_prototype():
    row = panel_frame().query("contract == 'GC C1' and is_zone_touch == 1").iloc[0].copy()
    row["delta_z"] = 2.1; row["bt2a_direction"] = 1
    row["vwap_tick"] = row["val_tick"] = row["vah_tick"] = row["close_tick"]
    direction, votes = trigger_direction(row, spec())
    assert votes == [-1, 1]
    assert direction == 0


def test_same_bar_dual_first_passage_is_zero():
    df = panel_frame().query("contract == 'GC C1'").copy()
    df.loc[df["bar_index_in_session"] == 66, ["high_tick", "low_tick"]] = [1010, 990]
    p = session_panel(df)
    assert first_passage(p, 65, 30, direction=1, barrier=4) == 0
    assert first_passage(p, 65, 30, direction=-1, barrier=4) == 0


def test_control_selection_is_cross_session_and_deterministic():
    event_df = panel_frame(bars=240).query("contract == 'GC C1'").copy()
    control_df = event_df.copy(); control_df["session_id"] = 20260629
    control_df["ts_utc_ns"] -= 86_400_000_000_000; control_df["is_zone_touch"] = 0
    for col in ("kind", "zone_id", "created_ts_utc_ns", "lower_tick", "upper_tick", "zone_score"):
        control_df[col] = None
    event_panel, control_panel = session_panel(event_df), session_panel(control_df)
    sessions = {("GC C1", 20260630): event_panel, ("GC C1", 20260629): control_panel}
    a = pick_controls(sessions, ("GC C1", 20260630), 65, 30, spec(), "event")
    b = pick_controls(sessions, ("GC C1", 20260630), 65, 30, spec(), "event")
    assert [(id(p), i) for p, i in a] == [(id(p), i) for p, i in b]
    assert a and all(panel is control_panel for panel, _ in a)


def test_wild_cluster_and_holm_are_reproducible():
    values = {f"s{i}": [float(i % 3) + 0.25] for i in range(50)}
    assert wild_cluster(values, 999, 123) == wild_cluster(values, 999, 123)
    out = holm_adjust({"5": 0.01, "15": 0.03, "60": 0.2})
    assert out["5"] <= out["15"] <= out["60"]
    assert out["5"] == pytest.approx(0.03)
