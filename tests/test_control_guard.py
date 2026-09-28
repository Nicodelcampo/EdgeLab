"""Guardia de controles evento-contra-control (LES-CTRL-TIMING-20260924)."""
import pytest

from edgelab.edge_brain.control_guard import RULE_VERSION, audit_event_controls, check_observation_design
from edgelab.edge_brain.hippocampus_store import DurableHippocampus

SHA = "a" * 64
S = 1_000_000


def test_controls_before_event_fail_and_show_drift():
    te = [100 * S] * 4
    tc = [40 * S, 90 * S, 200 * S, 300 * S]                 # dos previos: heredan el camino de aproximación
    a = audit_event_controls(te, tc, horizon_max_s=60, control_y=[-6.0, -20.0, -1.0, 0.0])
    assert a["status"] == "FAIL" and a["reason"] == "CONTROL_BEFORE_EVENT" and a["n_before_event"] == 2
    assert a["diagnostic_mean_y"]["antes"] == -13.0 and a["diagnostic_mean_y"]["despues"] == -0.5


def test_control_inside_window_fails_after_horizon_passes_other_session_exempt():
    a = audit_event_controls([100 * S], [130 * S], horizon_max_s=60)
    assert a["status"] == "FAIL" and a["reason"] == "CONTROL_INSIDE_EVENT_WINDOW"
    assert audit_event_controls([100 * S], [160 * S], horizon_max_s=60)["status"] == "PASS"
    b = audit_event_controls([100 * S, 100 * S], [10 * S, 200 * S], 60, same_session=[False, True])
    assert b["status"] == "PASS" and b["n_other_session"] == 1


def test_store_requires_design_and_passing_audit(tmp_path):
    s = DurableHippocampus(tmp_path / "l.jsonl")
    s.record_partition("P-EXP", "EXPLORATION", "x", ["d1"])
    with pytest.raises(ValueError, match="design must be declared"):
        s.record_observation("O-1", "abs", "RESPONSE_PROFILE", ["P-EXP"], {}, {}, SHA)
    with pytest.raises(ValueError, match="requires control_audit"):
        s.record_observation("O-1", "abs", "RESPONSE_PROFILE", ["P-EXP"], {}, {}, SHA, design="EVENT_VS_CONTROL")
    bad = audit_event_controls([100 * S], [50 * S], 60)
    with pytest.raises(ValueError, match="CONTROL_BEFORE_EVENT"):
        s.record_observation("O-1", "abs", "RESPONSE_PROFILE", ["P-EXP"], {}, {}, SHA, design="EVENT_VS_CONTROL",
                             control_audit=bad)
    forged = dict(bad, status="PASS", rule_version="CTRL_TIMING_V0")
    with pytest.raises(ValueError, match=RULE_VERSION):
        check_observation_design("RESPONSE_PROFILE", "EVENT_VS_CONTROL", forged)
    good = audit_event_controls([100 * S], [200 * S], 60)
    s.record_observation("O-1", "abs", "RESPONSE_PROFILE", ["P-EXP"], {}, {}, SHA, design="EVENT_VS_CONTROL",
                         control_audit=good)
    r = DurableHippocampus(tmp_path / "l.jsonl")          # el replay revalida la auditoría
    assert r.observations["O-1"]["control_audit"]["status"] == "PASS"
