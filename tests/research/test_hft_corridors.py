import pytest

from edgelab.research import hft_corridors as h


def test_v1_end_is_availability_not_start():
    z = h.normalize_hft_zone({"start_ms": 1000, "end_ms": 1250, "lo": 100.0, "hi": 101.0, "dir": 1, "id": 7})
    assert z["origin_ts"] == 1_000_000_000
    assert z["available_ts"] == 1_250_000_000
    assert z["available_ts_source"] == "V1_END_MS_DERIVED"


def test_missing_completion_fails_closed():
    with pytest.raises(ValueError):
        h.normalize_hft_zone({"start_ms": 1000, "lo": 100.0, "hi": 101.0})


def test_v2_ns_preserved_and_ordered():
    rows = [
        {"start_ts_ns": 300_000_000_000_000_000, "end_ts_ns": 300_000_000_000_000_300, "lo": 2, "hi": 3, "zone_seq": 2, "session_id": "S", "contract": "NQ"},
        {"start_ts_ns": 300_000_000_000_000_000, "end_ts_ns": 300_000_000_000_000_200, "lo": 1, "hi": 2, "zone_seq": 1, "session_id": "S", "contract": "NQ"},
    ]
    z = h.normalize_hft_zones(rows)
    assert [x["zone_seq"] for x in z] == [1, 2]
    assert all(x["available_ts_source"] == "V2_END_NS" for x in z)


def test_completion_cannot_precede_origin():
    with pytest.raises(ValueError):
        h.normalize_hft_zone({"start_ts_ns": 300_000_000_000_000_000, "end_ts_ns": 200_000_000_000_000_000, "lo": 1, "hi": 2})


def test_no_predictive_language_or_outcome_fields():
    forbidden = {"pnl", "return", "target", "stop", "win_rate", "mae", "mfe"}
    assert not forbidden.intersection({k.lower() for c in h.HFT_VISUAL_CONFIGS for k in c})


def test_ranking_is_deterministic(monkeypatch):
    def fake_field(zones, t_ref, tick_size, pmin, pmax, cfg):
        return {"density": [0.0, 1.0, 2.0, 1.0, 0.0], "price_ticks": list(range(5)), "field_hash": f"{cfg['id']}:{t_ref}"}
    monkeypatch.setattr(h, "compute_field", fake_field)
    monkeypatch.setattr(h, "detect_density_intervals", lambda *a, **k: {"low_density_intervals": [{}], "high_density_regions": [{}]})
    a = h.evaluate_visual_configurations([], [1, 2], 0.25, {1: (0, 4), 2: (0, 4)})
    b = h.evaluate_visual_configurations([], [1, 2], 0.25, {1: (0, 4), 2: (0, 4)})
    assert a == b
    assert a["status"] == "TARGET_FREE_VISUAL_RANKING_ONLY"
    assert len(a["configurations"]) == len(h.HFT_VISUAL_CONFIGS)
