# -*- coding: utf-8 -*-
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MOD = REPO / "diag" / "tasa_senales" / "F2.9_bar_classifier.py"
_spec = importlib.util.spec_from_file_location("f29_runner", MOD)
f29 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f29)

from edgelab.research.f29.labels import probe_interval, probe_side, wick_fracs


def test_s0_uses_range_extremes_not_japanese_wick():
    w = wick_fracs(20, 0, 5)
    assert w["range_ticks"] == 20
    assert w["upper_wick_frac"] == 0.75
    assert w["lower_wick_frac"] == 0.25
    assert w["range_ticks"] >= 3 and max(w["upper_wick_frac"], w["lower_wick_frac"]) >= 0.30


def test_probe_is_one_tick_at_distance_two():
    assert probe_side(20, 0, 5) == "bull"
    assert probe_interval(1000, "bull") == (1002, 1002)
    assert probe_interval(1000, "bear") == (998, 998)


def test_zeros_enter_session_mean():
    pairs = [
        ("2026-06-01", 1.0, "real_first"),
        ("2026-06-01", 0.0, "double_censoring"),
        ("2026-06-01", -1.0, "mirror_first"),
        ("2026-06-02", 0.0, "empate_tecnico"),
    ]
    means = f29.session_mean_map(pairs)
    assert means["2026-06-01"] == 0.0
    assert means["2026-06-02"] == 0.0
    metrics = f29.metrics_from_pairs(pairs)
    assert metrics["empate_tecnico"] == 1
    assert metrics["double_censoring"] == 1
    assert metrics["n_resolved"] == 2


def test_ties_are_not_dumped_into_double_censor():
    assert f29.classify_category("empate_tecnico") == "empate_tecnico"
    assert f29.classify_category("same_bar_needs_tick_tiebreak") == "empate_tecnico"
    assert f29.classify_category("double_censoring") == "double_censoring"


def test_paired_contrast_uses_common_sessions_only():
    a = [("s1", 1.0, "real_first"), ("s2", 0.0, "double_censoring")]
    b = [("s1", 0.0, "double_censoring"), ("s3", 1.0, "real_first")]
    out = f29.paired_contrast(a, b)
    assert out["n_sessions"] == 1
    assert out["delta"] == 1.0
