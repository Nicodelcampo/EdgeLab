import copy
import json

import pytest

from edgelab.edge_brain.result_lineage import (
    IncompleteResultEvidence, REVIEW_AREAS, SCHEMA, main,
    require_complete_result_envelope, review_result_evidence,
)


def synthetic():
    return {
        "schema": SCHEMA, "run_id": "SYNTHETIC", "instrument": "MNQ",
        "contracts": ["MNQ_09-25"], "resolver_sha256": "a"*64,
        "execution": {"source_sha256": "b"*64, "code_bundle_sha256": "c"*64,
                      "runtime_sha256": "d"*64, "output_run_id": "synthetic-output",
                      "notebook_version": 1, "seed_policy": "stable_explicit_v1", "seed": 42},
        "campaign": {"spec_sha256": "e"*64, "authorization_sha256": "f"*64,
                     "data_start": "2025-07-01", "data_end": "2026-03-31",
                     "holdout_start": "2026-04-01"},
        "inputs": [{"dataset_version": "synthetic/mnq/1",
                    "file": "MNQ_09-25_ticks.parquet", "sha256": "0"*64}],
        "quality_review_refs": {area: "1"*64 for area in REVIEW_AREAS},
        "transformations": [], "outputs": [{"file": "result.json", "sha256": "2"*64}],
        "unresolved_issues": [],
    }


def test_complete_is_not_approval_and_does_not_mutate():
    b = synthetic(); before = copy.deepcopy(b)
    r = require_complete_result_envelope(b)
    assert r["status"] == "METADATA_COMPLETE_UNADJUDICATED"
    assert not r["research_authorized"] and not r["bias_adjudicated"]
    assert not r["original_evidence_modified"] and b == before


@pytest.mark.parametrize("field", ["inputs", "resolver_sha256", "execution", "campaign",
                                   "quality_review_refs", "outputs", "transformations",
                                   "unresolved_issues", "contracts", "instrument", "run_id"])
def test_missing_evidence_fails_closed(field):
    b = synthetic(); del b[field]
    with pytest.raises(IncompleteResultEvidence):
        require_complete_result_envelope(b)


def test_quarantine_is_scoped_not_attachment_or_micro_inference():
    b = synthetic()
    b["attached_datasets"] = ["nicolasbuttaro/edgelab-ticks-nq-preholdout/6"]
    assert review_result_evidence(b)["issues"] == []
    b["inputs"][0].update(dataset_version="nicolasbuttaro/edgelab-ticks-nq-preholdout/6",
                          file="NQ_09-26_ticks.parquet")
    assert "KNOWN_UNRESOLVED_SOURCE" in review_result_evidence(b)["issues"]


def test_unpinned_version_and_unknown_version_cannot_pass():
    b = synthetic(); b["inputs"][0]["dataset_version"] = "synthetic/mnq"
    assert "UNPINNED_DATASET_VERSION" in review_result_evidence(b)["issues"]


def test_original_holdout_not_global_october():
    b = synthetic(); b["campaign"]["data_end"] = "2026-07-01"
    assert "DECLARED_WINDOW_CONFLICTS_WITH_ORIGINAL_HOLDOUT" in review_result_evidence(b)["issues"]


@pytest.mark.parametrize("policy", ["python_hash", None, "caller_says_deterministic"])
def test_seed_policy_cannot_be_guessed(policy):
    b = synthetic(); b["execution"]["seed_policy"] = policy
    assert "UNSTABLE_OR_UNDECLARED_RANDOMNESS" in review_result_evidence(b)["issues"]


def test_boolean_seed_and_version_are_rejected():
    b = synthetic(); b["execution"].update(seed=True, notebook_version=True)
    issues = review_result_evidence(b)["issues"]
    assert "MISSING_EXPLICIT_SEED" in issues and "MISSING_EXACT_NOTEBOOK_VERSION" in issues


def test_unresolved_is_review_not_invalidation():
    b = synthetic(); b["unresolved_issues"] = ["clock provenance unavailable"]
    assert review_result_evidence(b)["status"] == "REQUIRES_REVIEW"


def test_transformations_need_evidence():
    b = synthetic(); b["transformations"] = [{"name": "clip maintenance interval"}]
    assert "UNDOCUMENTED_TRANSFORMATION" in review_result_evidence(b)["issues"]


def test_duplicate_inputs_and_contracts():
    b = synthetic(); b["inputs"] *= 2; b["contracts"] *= 2
    issues = review_result_evidence(b)["issues"]
    assert "DUPLICATE_CONSUMED_INPUT" in issues and "DUPLICATE_CONTRACT" in issues


def test_nonobject_and_bad_input_do_not_crash():
    assert review_result_evidence(None)["status"] == "REQUIRES_REVIEW"
    b = synthetic(); b["inputs"] = [{"dataset_version": [], "file": {}}]
    assert review_result_evidence(b)["status"] == "REQUIRES_REVIEW"


def test_cli_read_only(tmp_path, capsys):
    p = tmp_path / "synthetic.json"; p.write_text(json.dumps(synthetic()))
    before = p.read_bytes()
    assert main([str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["research_authorized"] is False
    assert before == p.read_bytes()
    p.write_text("{}")
    assert main([str(p)]) == 2