"""Read-only result evidence-envelope checks; never scientific approval.

No prices, network, ledger mutation or automatic invalidation. Hash-shaped
references are declarations until independently verified against actual bytes.
This opt-in check is not wired into legacy kernels or promotion gates.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re

SCHEMA = "edgelab_result_evidence_v1"
REVIEW_AREAS = ("calendar", "coverage", "liquidity", "clock", "selection", "source")


class IncompleteResultEvidence(ValueError):
    """The envelope is incomplete, contradictory or explicitly unresolved."""


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def review_result_evidence(bundle):
    """Check declared lineage only, not the truth/authority of those declarations.

    `inputs` means consumed sources, not merely attached Kaggle datasets.
    An uncertainty is never upgraded to INVALIDATED or a proven bias.
    """
    issues = set()
    if not isinstance(bundle, dict):
        bundle = {}
        issues.add("INVALID_ENVELOPE")
    if bundle.get("schema") != SCHEMA:
        issues.add("UNSUPPORTED_SCHEMA")
    for field in ("run_id", "instrument"):
        if not isinstance(bundle.get(field), str) or not bundle[field].strip():
            issues.add("MISSING_" + field.upper())
    contracts = bundle.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        issues.add("MISSING_CONSUMED_CONTRACTS")
    else:
        if any(not isinstance(c, str) or not c.startswith(str(bundle.get("instrument")) + "_") for c in contracts):
            issues.add("CONTRACT_INSTRUMENT_MISMATCH")
        if len({str(c) for c in contracts}) != len(contracts):
            issues.add("DUPLICATE_CONTRACT")

    def object_field(name):
        obj = bundle.get(name)
        if not isinstance(obj, dict):
            issues.add("MISSING_" + name.upper())
            return {}
        return obj

    execution = object_field("execution")
    for field in ("source_sha256", "code_bundle_sha256", "runtime_sha256"):
        if not _sha(execution.get(field)):
            issues.add("MISSING_EXECUTION_" + field.upper())
    if not isinstance(execution.get("output_run_id"), str) or not execution["output_run_id"].strip():
        issues.add("MISSING_OUTPUT_RUN_BINDING")
    if type(execution.get("notebook_version")) is not int or execution["notebook_version"] < 1:
        issues.add("MISSING_EXACT_NOTEBOOK_VERSION")
    if execution.get("seed_policy") not in ("stable_explicit_v1", "no_randomness"):
        issues.add("UNSTABLE_OR_UNDECLARED_RANDOMNESS")
    if execution.get("seed_policy") == "stable_explicit_v1" and (
        type(execution.get("seed")) is not int or execution["seed"] < 0
    ):
        issues.add("MISSING_EXPLICIT_SEED")

    campaign = object_field("campaign")
    for field in ("spec_sha256", "authorization_sha256"):
        if not _sha(campaign.get(field)):
            issues.add("MISSING_CAMPAIGN_" + field.upper())
    days = {}
    for field in ("data_start", "data_end", "holdout_start"):
        try:
            value = campaign.get(field)
            if not isinstance(value, str):
                raise ValueError
            days[field] = date.fromisoformat(value)
        except ValueError:
            issues.add("INVALID_CAMPAIGN_" + field.upper())
    if len(days) == 3 and not (days["data_start"] <= days["data_end"] < days["holdout_start"]):
        issues.add("DECLARED_WINDOW_CONFLICTS_WITH_ORIGINAL_HOLDOUT")

    # Reuse the exact version/file quarantine; NEVER equate NQ with MNQ.
    from edgelab.kaggle.research_access import KNOWN_UNRESOLVED_SOURCES

    inputs = bundle.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        issues.add("MISSING_CONSUMED_INPUTS")
        inputs = []
    identities = set()
    for row in inputs:
        if not isinstance(row, dict):
            issues.add("INVALID_CONSUMED_INPUT")
            continue
        ref, filename = row.get("dataset_version"), row.get("file")
        if not isinstance(ref, str) or not re.fullmatch(r"[^/\s]+/[^/\s]+/[1-9][0-9]*", ref):
            issues.add("UNPINNED_DATASET_VERSION")
        if not isinstance(filename, str) or not filename.strip():
            issues.add("MISSING_INPUT_FILE")
        if not _sha(row.get("sha256")):
            issues.add("MISSING_INPUT_SHA256")
        identity = (str(ref), str(filename))
        if identity in identities:
            issues.add("DUPLICATE_CONSUMED_INPUT")
        identities.add(identity)
        if isinstance(ref, str) and isinstance(filename, str) and (ref, filename) in KNOWN_UNRESOLVED_SOURCES:
            issues.add("KNOWN_UNRESOLVED_SOURCE")
    if not _sha(bundle.get("resolver_sha256")):
        issues.add("MISSING_RESOLVER_SHA256")
    review = object_field("quality_review_refs")
    for area in REVIEW_AREAS:
        if not _sha(review.get(area)):
            issues.add("MISSING_REVIEW_" + area.upper())
    transforms = bundle.get("transformations")
    if not isinstance(transforms, list):
        issues.add("MISSING_TRANSFORMATION_DECLARATIONS")
    elif any(not isinstance(t, dict) or not isinstance(t.get("name"), str) or not t["name"].strip()
             or not _sha(t.get("evidence_sha256")) for t in transforms):
        issues.add("UNDOCUMENTED_TRANSFORMATION")
    outputs = bundle.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        issues.add("MISSING_PINNED_OUTPUTS")
    elif any(not isinstance(o, dict) or not isinstance(o.get("file"), str) or not o["file"].strip()
             or not _sha(o.get("sha256")) for o in outputs):
        issues.add("UNPINNED_OUTPUT")
    unresolved = bundle.get("unresolved_issues")
    if not isinstance(unresolved, list):
        issues.add("MISSING_UNRESOLVED_ISSUES_DECLARATION")
    elif unresolved:
        issues.add("EXPLICIT_UNRESOLVED_ISSUES")
    return {
        "schema": "edgelab_result_lineage_review_v1",
        "run_id": bundle.get("run_id"),
        "status": "REQUIRES_REVIEW" if issues else "METADATA_COMPLETE_UNADJUDICATED",
        "issues": sorted(issues),
        "research_authorized": False,
        "bias_adjudicated": False,
        "original_evidence_modified": False,
        "scope": "declared_metadata_consistency_only",
    }


def require_complete_result_envelope(bundle):
    """Opt-in envelope preflight, not data-access or economic permission."""
    review = review_result_evidence(bundle)
    if review["issues"]:
        raise IncompleteResultEvidence(", ".join(review["issues"]))
    return review


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "REQUIRES_REVIEW", "error": str(exc), "research_authorized": False}))
        return 2
    review = review_result_evidence(bundle)
    print(json.dumps(review, indent=2, sort_keys=True))
    return 2 if review["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())