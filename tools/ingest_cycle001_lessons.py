#!/usr/bin/env python3
"""Build the CYCLE-001 genesis ledger for the durable Experimental Hippocampus.

Materializes the verified lessons of CYCLE-001 (2026-09-21/22) as the first
real records of the durable hippocampus. The build is deterministic: fixed
timestamps and canonical serialization mean the same script always produces
byte-identical output and the same tip hash, which the test suite pins.

Usage: python tools/ingest_cycle001_lessons.py --out artifacts/hippocampus/cycle001_genesis_ledger.jsonl
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(module_name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Load by path: avoids edgelab.edge_brain.__init__ optional dependencies.
for pkg, pkg_path in (
    ("edgelab", ROOT / "edgelab"),
    ("edgelab.edge_brain", ROOT / "edgelab" / "edge_brain"),
):
    if pkg not in sys.modules:
        module = types.ModuleType(pkg)
        module.__path__ = [str(pkg_path)]
        sys.modules[pkg] = module

h = _load("edgelab.edge_brain.hippocampus", ROOT / "edgelab" / "edge_brain" / "hippocampus.py")
store_mod = _load("edgelab.edge_brain.hippocampus_store",
                  ROOT / "edgelab" / "edge_brain" / "hippocampus_store.py")

TS = "2026-09-22T00:00:00Z"  # fixed for deterministic genesis
EPISODE_ID = "EPISODE-CYCLE-001-MULTIAGENT"

# Verified CYCLE-001 lessons. evidence refs point at commits/artifacts; nothing
# here is promoted beyond LESSON_CANDIDATE.
LESSONS = [
    {
        "id": "LESSON-CYCLE001-PRIVACY-BY-PROBE",
        "statement": "privacy-by-report != privacy-by-probe: an authenticated session reported the Kaggle dataset private while it was publicly listable; visibility claims require an unauthenticated probe.",
        "scope": "OPERATIONAL",
    },
    {
        "id": "LESSON-CYCLE001-WORKER-IDENTITY-DETERMINES-RESULT",
        "statement": "access-probe results are only attributable with worker_id + capability: the duplicate Worker returned 400 while the canonical one returned 200 on the same credential family.",
        "scope": "OPERATIONAL",
    },
    {
        "id": "LESSON-CYCLE001-NO-CALLER-SUPPLIED-TRUTH",
        "statement": "a caller-supplied boolean can never be evidence: json_shape_valid=True authenticated without payload or schema until internal endpoint validation was made mandatory.",
        "scope": "METHODOLOGICAL",
    },
    {
        "id": "LESSON-CYCLE001-EXCEPTIONS-ARE-NOT-DURABLE",
        "statement": "raw exception strings can carry secrets (Authorization/Bearer); durable records store bounded error enums only, and secret-bearing keys must be normalized across case/whitespace/separators.",
        "scope": "METHODOLOGICAL",
    },
    {
        "id": "LESSON-CYCLE001-LOCAL-PASS-NOT-CI-PASS",
        "statement": "a locally passing test can deterministically fail CI: hardcoded machine paths, unprovisioned browser deps and single-wheel lock hashes all produced green-local red-CI divergences.",
        "scope": "METHODOLOGICAL",
    },
]

COUNTEREXAMPLES = [
    {
        "id": "CX-CYCLE001-D-C-001",
        "target": "KAGGLE-ACCESS-CERTIFICATION-V1",
        "context": "ProbeObservation(200, json_shape_valid=True) without payload",
        "behavior": "verdict AUTHENTICATED_ENDPOINT_ONLY without any payload, endpoint or schema evidence",
        "why": "MEASUREMENT_INVALID: caller-controlled truth substituted for independent validation",
        "evidence_ref": "commit:3a90f8881b57b4f56fce3875fb369a5015ff0663",
        "status": "CONFIRMED",
    },
    {
        "id": "CX-CYCLE001-D-C-002",
        "target": "KAGGLE-ACCESS-CERTIFICATION-V1",
        "context": "network_error='Authorization: Bearer KGAT_REDACT_ME'",
        "behavior": "secret-bearing exception text emitted verbatim into the durable packet",
        "why": "SECRET_REDACTION_GAP: exception strings can contain headers, signed URLs or tokens",
        "evidence_ref": "commit:3a90f8881b57b4f56fce3875fb369a5015ff0663",
        "status": "CONFIRMED",
    },
    {
        "id": "CX-CYCLE001-D-C-003",
        "target": "KAGGLE-ACCESS-CERTIFICATION-V1",
        "context": "keys 'Authorization ', 'api-key', 'Kaggle-Api-Token'",
        "behavior": "exact lowercase denylist accepted normalized secret-bearing keys",
        "why": "denylists must compare normalized key families, not exact strings",
        "evidence_ref": "commit:3a90f8881b57b4f56fce3875fb369a5015ff0663",
        "status": "CONFIRMED",
    },
    {
        "id": "CX-CYCLE001-KAGGLE-PUBLIC-DATASET",
        "target": "KAGGLE-DATASET-VISIBILITY-V1",
        "context": "dataset created private per authenticated session report",
        "behavior": "dataset was publicly listable (isPrivate:false) until deleted and recreated",
        "why": "CUSTODY_CONTROL_FAILURE: privacy reported by an authenticated session is not evidence of privacy",
        "evidence_ref": "commit:68182282e613a33b9831f4b8fe51f3a9ff411f1c",
        "status": "CONFIRMED",
    },
]

FAILURES = [
    {
        "id": "FAILURE-CYCLE001-CI-COMMON-CAUSE",
        "step": "STEP-CYCLE001:01",
        "error_type": "CI_COMMON_CAUSE_COMPOUND",
        "description": "whole PR wave red: single-wheel rpds-py hash, absolute E:/ calendar path, missing null_out fixture, data-dependent tests without guards, 57 untriaged ULP expressions, missing CURRENT.md freshness header",
        "root_cause": "environmental assumptions written as if portable; fixed in fix/cycle001-ci-common-cause-20260922 (merged 70daaad0980fe5554c68988a5f83e78ee525af9f)",
    },
    {
        "id": "FAILURE-CYCLE001-WORKER-DUPLICATE-400",
        "step": "STEP-CYCLE001:00",
        "error_type": "ABSTAIN_AUTH_OR_ENDPOINT",
        "description": "first hosted probe ran on a duplicate Worker and returned HTTP 400; canonical Worker later returned 200",
        "root_cause": "worker identity was ambiguous until A adjudicated the three-Worker inventory",
    },
]

STEPS = [
    "Coordinate four agents with mandatory cross-review and fail-closed contracts",
    "Adjudicate the three-Worker Kaggle inventory without executing duplicates",
]


def build(out_path: Path) -> str:
    store = store_mod.DurableHippocampus(out_path)
    store.register_episode(h.AnalysisEpisode(
        episode_id=EPISODE_ID,
        goal="Preserve verified CYCLE-001 lessons without promoting them beyond LESSON_CANDIDATE",
        status="COMPLETED_UNADJUDICATED",
        created_at_utc=TS, updated_at_utc=TS,
        recorded_by="cycle-001-single-agent", outcomes_inspected=False,
    ))
    for i, action in enumerate(STEPS):
        store.record_step(h.StepExecution(
            step_id=f"STEP-CYCLE001:{i:02d}", episode_id=EPISODE_ID, step_index=i,
            action=action, tool_name="cycle-001-coordination",
            status="SUCCEEDED_UNADJUDICATED", input_params={},
            output_summary="durable artifacts in Notion + GitHub", executed_at_utc=TS,
        ))
    for f in FAILURES:
        store.record_failure(h.FailureEvent(
            failure_id=f["id"], episode_id=EPISODE_ID, step_id=f["step"],
            error_type=f["error_type"], description=f["description"],
            root_cause=f["root_cause"], occurred_at_utc=TS,
        ))
    for lesson in LESSONS:
        store.record_lesson(h.LessonCandidate(
            lesson_id=lesson["id"], episode_id=EPISODE_ID,
            statement=lesson["statement"], evidence_record_ids=[],
            confidence="LOW", status="PROPOSED", scope=lesson["scope"],
            created_at_utc=TS,
        ))
    for cx in COUNTEREXAMPLES:
        store.record_counterexample(h.Counterexample(
            counterexample_id=cx["id"], target_claim_or_rule_id=cx["target"],
            context=cx["context"], observed_behavior=cx["behavior"],
            why_it_violates=cx["why"], evidence_ref=cx["evidence_ref"],
            status=cx["status"], recorded_at_utc=TS,
        ))
    return store.tip_hash


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        args.out.unlink()  # deterministic rebuild: genesis is rebuilt from scratch
    tip = build(args.out)
    print(f"genesis ledger written: {args.out}")
    print(f"tip_sha256: {tip}")


if __name__ == "__main__":
    main()
