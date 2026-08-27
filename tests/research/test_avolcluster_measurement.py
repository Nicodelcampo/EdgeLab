# -*- coding: utf-8 -*-
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tools.run_avolcluster_measurement import (
    MeasurementAbort,
    SessionPanel,
    first_passage,
    forward_slice,
    holm_adjust,
    pick_controls,
    trigger_direction,
    validate_panel,
    wild_cluster,
)

ROOT = Path(__file__).resolve().parents[2]


def spec():
    return json.loads((ROOT / "specs/avolcluster_poi_compression_v1.json").read_text("utf-8"))


def panel_frame(session_id=20260630, bars=130):
    rows = []
    for c in range(5):
        contract = f"NQ C{c + 1}"
        for i in range(bars):
            touch = i == 65
            rows.append({
                "instrument": "NQ", "contract": contract,
                "session_id": session_id, "bar_index_in_session": i,
                "ts_utc_ns": 1_000_000_000 * (c * 10000 + i + 100),
                "time_bucket": i // 30, "high_tick": 1002 + (i % 2),
                "low_tick": 998 - (i % 2), "close_tick": 1000,
                "pre_touch_vol_ticks": 4.0, "is_zone_touch": int(touch),
                "kind": "OFF_PRICE" if touch else None,
                "zone_id": f"z{c}" if touch else None,
                "created_ts_utc_ns": 1_000_000_000 * (c * 10000 + i + 90) if touch else None,
                "lower_tick": 997 if touch else None,
                "upper_tick": 999 if touch else None,
                "zone_score": 10.0 if touch else None,
                "delta_z": 2.5 if touch else 0.0,
                "penetration_ticks": 1.0 if touch else 0.0,
                "displacement_ticks": 0.0,
                "bt2a_direction": -1 if touch else 0,
                "bt2_direction": 0,
                "vwap_tick": 999.0, "val_tick": 995.0, "vah_tick": 999.0,
            })
    return pd.DataFrame(rows)


def session_panel(df):
    g = df.sort_values("bar_index_in_session").reset_index(drop=True)
    return SessionPanel(g, {int(v): i for i, v in enumerate(g["bar_index_in_session"])},
                        np.flatnonzero(g["is_zone_touch"].to_numpy(dtype=bool)))


def test_spec_is_frozen_json():
    s = spec()
    assert s["status"] == "FROZEN_METHOD"
    assert s["population"]["holdout_session_id_min_inclusive"] == "20260701"
    assert s["epistemic_scope"]["execution_reads_future_price_path"] is True
    assert s["epistemic_scope"]["pnl_accessed"] is False


def test_preflight_accepts_five_contract_pre_holdout_panel():
    out, diag = validate_panel(panel_frame(), spec())
    assert len(diag["contracts"]) == 5
    assert diag["touch_events"] == 5
    assert int(out["session_id"].max()) == 20260630


def test_holdout_is_rejected_fail_closed():
    with pytest.raises(MeasurementAbort) as exc:
        validate_panel(panel_frame(session_id=20260701), spec())
    assert exc.value.label == "ABSTAIN_HOLDOUT_FIREWALL"


def test_pnl_or_target_columns_are_rejected():
    df = panel_frame()
    df["pnl_net"] = 0.0
    with pytest.raises(MeasurementAbort) as exc:
        validate_panel(df, spec())
    assert exc.value.label == "ABSTAIN_INPUT_INTEGRITY"


def test_forward_window_requires_contiguous_same_session_indices():
    df = panel_frame().query("contract == 'NQ C1'").copy()
    p = session_panel(df)
    assert len(forward_slice(p, 65, 30)) == 30
    broken = df[df["bar_index_in_session"] != 70]
    assert forward_slice(session_panel(broken), 65, 30) is None


def test_absorption_plus_context_produces_short_vote():
    row = panel_frame().query("contract == 'NQ C1' and is_zone_touch == 1").iloc[0].copy()
    row["bt2a_direction"] = 0
    row["delta_z"] = 2.1
    row["close_tick"] = 1002
    row["vwap_tick"] = 1000
    row["vah_tick"] = 1001
    direction, votes = trigger_direction(row, spec())
    assert direction == -1
    assert votes == [-1, -1]


def test_conflicting_votes_abstain_event():
    row = panel_frame().query("contract == 'NQ C1' and is_zone_touch == 1").iloc[0].copy()
    row["delta_z"] = 2.1
    row["bt2a_direction"] = 1
    row["vwap_tick"] = row["val_tick"] = row["vah_tick"] = row["close_tick"]
    direction, votes = trigger_direction(row, spec())
    assert votes == [-1, 1]
    assert direction == 0


def test_same_bar_dual_first_passage_is_zero():
    df = panel_frame().query("contract == 'NQ C1'").copy()
    df.loc[df["bar_index_in_session"] == 66, ["high_tick", "low_tick"]] = [1010, 990]
    p = session_panel(df)
    assert first_passage(p, 65, 30, direction=1, barrier=4) == 0
    assert first_passage(p, 65, 30, direction=-1, barrier=4) == 0


def test_control_selection_is_deterministic_and_respects_blackout():
    df = panel_frame(bars=240).query("contract == 'NQ C1'").copy()
    p = session_panel(df)
    a = pick_controls(p, 65, 30, spec(), "event")
    b = pick_controls(p, 65, 30, spec(), "event")
    assert a == b
    assert all(abs(i - 65) > 60 for i in a)


def test_wild_cluster_bootstrap_is_reproducible():
    values = {f"s{i}": [float(i % 3) + 0.25] for i in range(50)}
    a = wild_cluster(values, 999, 123)
    b = wild_cluster(values, 999, 123)
    assert a == b
    assert a["clusters"] == 50
    assert a["estimate"] > 0


def test_holm_is_monotone_in_sorted_p_values():
    out = holm_adjust({"5": 0.01, "15": 0.03, "60": 0.2})
    assert out["5"] <= out["15"] <= out["60"]
    assert out["5"] == pytest.approx(0.03)
