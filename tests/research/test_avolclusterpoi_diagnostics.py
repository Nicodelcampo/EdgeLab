"""Target-free diagnostic contract for aVolClusterPOI."""
from edgelab.bridge.indicators import avolclusterpoi as avol


def _hot_cells():
    return {1: 1, 2: 1, 3: 1, 4: 1, 10: 10, 11: 10}


def test_no_history_exports_true_best_candidate_and_real_history_count():
    out = avol.detect_block(_hot_cells(), [1, 2, 3], {"min_samples_per_bucket": 20})
    assert out["best_score"] == 20
    assert out["history_samples"] == 3
    assert out["decision"] == "ABSTAIN_NO_HISTORY"
    assert out["abstain"] == "warmup"
    assert out["clusters"][0]["score"] == 20
    assert out["selected_cluster"] is None


def test_below_threshold_is_not_no_cluster():
    out = avol.detect_block(_hot_cells(), [100] * 20)
    assert out["best_score"] == 20
    assert out["threshold"] == 100
    assert out["decision"] == "ABSTAIN_BELOW_THRESHOLD"
    assert out["abstain"] is None


def test_create_preserves_legacy_keys_and_exports_selected_cluster():
    out = avol.detect_block(_hot_cells(), [1] * 20, close_tick=20)
    for key in ("best_score", "threshold", "zones", "abstain"):
        assert key in out
    assert out["decision"] == "CREATE"
    assert out["selected_cluster"]["lower_tick"] == 10
    assert out["selected_cluster"]["upper_tick"] == 11
    assert out["zones"][0]["kind"] == "OFF_PRICE"


def test_few_cells_has_explicit_decision():
    out = avol.detect_block({1: 1, 2: 2}, [1] * 20)
    assert out["decision"] == "ABSTAIN_FEW_CELLS"
    assert out["best_score"] == 0
    assert out["clusters"] == []
