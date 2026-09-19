import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/audit/EDGELAB_KAGGLE_NON_NQ_VERIFICATION_20260919.json"
MAN = ROOT / "artifacts/audit/EDGELAB_KAGGLE_CANONICAL_MANIFEST.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_non_nq_remote_listing_and_published_digests_match_manifest():
    art, man = _load(ART), _load(MAN)
    assert art["evidence_class"] == "REMOTE_LISTING_PLUS_PUBLISHED_DIGEST_NO_DOWNLOAD_PROOF"
    assert art["download_evidence"] == "NONE_LISTING_AND_REMOTE_DIGEST_ONLY"
    assert art["canonical_source"] is False
    expected = {r["file_name"]: r["source_sha256"] for r in man["CANONICAL_RAW_TICKS"] if r["instrument"] != "NQ"}
    digest = hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert len(art["dataset_observations"]) == 10
    assert sum(d["contract_file_count"] for d in art["dataset_observations"]) == len(expected) == 51
    assert art["digest_maps_equal"] is True
    assert art["published_digest_map_sha256"] == art["manifest_digest_map_sha256"] == digest


def test_non_nq_totals_and_metadata_are_fail_closed():
    art, man = _load(ART), _load(MAN)
    rows = [r for r in man["CANONICAL_RAW_TICKS"] if r["instrument"] != "NQ"]
    s = art["summary"]
    assert s["contracts_listed"] == 51
    assert s["rows_from_manifest"] == sum(r["row_count"] for r in rows) == 896_546_782
    assert s["source_bytes_from_manifest"] == sum(r["size_bytes"] for r in rows) == 14_725_073_511
    f = art["required_metadata_flags"]
    assert f["coverage_mode"] == "PARTIAL_CONTRACT_MONTH_SLICES"
    assert f["canonical_source"] is True
    assert f["is_complete_continuous_series"] is False
    assert f["includes_all_contracts"] is False
    assert f["has_certified_roll_methodology"] is False
    assert f["eligible_for_continuous_backtest"] is False
    assert f["missing_periods_mean_no_data"] is False
    assert f["holdout_enforcement"] == "STRICT_LESS_THAN (0 holdout rows)"


def test_nq_is_explicitly_excluded_after_replacement_regression():
    x = _load(ART)["excluded"]
    assert x["instrument"] == "NQ"
    assert x["version_history_evidence"] == "+1 new, -4 removed"
    assert x["custody_status"] == "RECONCILIATION_REQUIRED"
