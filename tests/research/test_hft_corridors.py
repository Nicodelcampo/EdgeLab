import pytest

from edgelab.research import hft_corridors as h

SHA = "a" * 64


def v2(**updates):
    row = {
        "start_ts_ns": 300_000_000_000_000_000,
        "end_ts_ns": 300_000_000_000_000_200,
        "available_ts_ns": 300_000_000_000_000_300,
        "price_lower": 100.0,
        "price_upper": 101.0,
        "zone_seq": 1,
        "session_id": "20260603",
        "contract": "NQ 06-26",
        "direction": 1,
        "termination_reason": "REVERSAL",
        "parameter_manifest_sha256": SHA,
        "indicator_source_sha256": SHA,
    }
    row.update(updates)
    return row


def test_v2_uses_available_not_end():
    zone = h.normalize_hft_zone(v2())
    assert zone["end_ts"] == 300_000_000_000_000_200
    assert zone["available_ts"] == 300_000_000_000_000_300
    assert zone["available_ts_source"] == "V2_AVAILABLE_NS"


def test_v2_missing_available_fails_closed():
    row = v2()
    del row["available_ts_ns"]
    with pytest.raises(ValueError, match="available_ts_ns"):
        h.normalize_hft_zone(row, mode="V2")


def test_v2_availability_before_end_fails():
    with pytest.raises(ValueError, match="precedes end"):
        h.normalize_hft_zone(v2(available_ts_ns=300_000_000_000_000_199))


@pytest.mark.parametrize("field", ["session_id", "contract", "zone_seq", "termination_reason", "parameter_manifest_sha256", "indicator_source_sha256"])
def test_v2_identity_and_provenance_are_required(field):
    row = v2()
    del row[field]
    with pytest.raises(ValueError, match=field):
        h.normalize_hft_zone(row, mode="V2")


def test_uncertifiable_end_of_input_fails():
    with pytest.raises(ValueError, match="termination_reason"):
        h.normalize_hft_zone(v2(termination_reason="END_OF_INPUT"))


def test_mixed_v1_v2_batch_fails():
    legacy = {"start_ms": 1000, "end_ms": 1250, "lo": 100.0, "hi": 101.0, "id": 7}
    with pytest.raises(ValueError, match="mixed"):
        h.normalize_hft_zones([v2(), legacy])


def test_legacy_requires_explicit_diagnostic_semantics():
    zone = h.normalize_hft_zone({"start_ms": 1000, "end_ms": 1250, "lo": 100.0, "hi": 101.0, "id": 7}, mode="V1_LEGACY")
    assert zone["available_ts"] == 1_250_000_000
    assert zone["available_ts_source"] == "V1_END_MS_DERIVED_DIAGNOSTIC"
    assert zone["parity_status"] == "LEGACY_DIAGNOSTIC_NOT_CERTIFIED"


def test_exact_integer_timestamp_rejects_fraction():
    with pytest.raises(ValueError, match="exact integer"):
        h.normalize_hft_zone(v2(available_ts_ns="300000000000000300.5"))


def test_no_predictive_language_or_outcome_fields():
    forbidden = {"pnl", "return", "target", "stop", "win_rate", "mae", "mfe"}
    assert not forbidden.intersection({key.lower() for cfg in h.HFT_VISUAL_CONFIGS for key in cfg})


def test_ranking_is_deterministic_and_not_scientific_selection(monkeypatch):
    def fake_field(zones, t_ref, tick_size, pmin, pmax, cfg):
        return {"density": [0.0, 1.0, 2.0, 1.0, 0.0], "price_ticks": list(range(5)), "field_hash": f"{cfg['id']}:{t_ref}"}
    monkeypatch.setattr(h, "compute_field", fake_field)
    monkeypatch.setattr(h, "detect_density_intervals", lambda *a, **k: {"low_density_intervals": [{}], "high_density_regions": [{}]})
    first = h.evaluate_visual_configurations([], [1, 2], 0.25, {1: (0, 4), 2: (0, 4)})
    second = h.evaluate_visual_configurations([], [1, 2], 0.25, {1: (0, 4), 2: (0, 4)})
    assert first == second
    assert first["status"] == "TARGET_FREE_VISUAL_HEURISTIC_ONLY_NOT_SCIENTIFIC_SELECTION"
    assert "NO_SCIENTIFIC_MODEL_SELECTION" in first["prohibitions"]
