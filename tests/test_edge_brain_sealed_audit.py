from __future__ import annotations

import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

import pytest

_PATH = Path(__file__).resolve().parents[1] / "edgelab/edge_brain/sealed_audit.py"
_SPEC = importlib.util.spec_from_file_location("edge_brain_sealed_audit_tested", _PATH)
assert _SPEC and _SPEC.loader
sealed_audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sealed_audit
_SPEC.loader.exec_module(sealed_audit)
AuditAlreadyUsed = sealed_audit.AuditAlreadyUsed
AuditLedgerError = sealed_audit.AuditLedgerError
SealedAuditLedger = sealed_audit.SealedAuditLedger

P = "a" * 64
B = "b" * 64
SPLIT = "c" * 64
C1 = "1" * 64
C2 = "2" * 64
RESULT = "d" * 64


def reserve(store, *, batch="audit-1", split=SPLIT, candidates=(C1, C2)):
    return store.reserve_batch(batch_id=batch, protocol_sha256=P,
                               benchmark_sha256=B, sealed_split_sha256=split,
                               candidate_system_sha256s=candidates)


def test_reservation_is_persisted_and_same_split_never_reopens(tmp_path):
    path = tmp_path / "audit.sqlite3"
    store = SealedAuditLedger(path)
    permit = reserve(store)
    assert permit.status == "RESERVED"
    assert permit.candidate_system_sha256s == (C1, C2)
    assert store.status("audit-1") == "RESERVED"
    reopened = SealedAuditLedger(path)
    with pytest.raises(AuditAlreadyUsed):
        reserve(reopened, batch="second-id")
    with pytest.raises(AuditAlreadyUsed):
        reserve(reopened)


def test_finalized_batch_cannot_be_replayed_and_scores_are_not_returned(tmp_path):
    store = SealedAuditLedger(tmp_path / "audit.sqlite3")
    reserve(store)
    store.finalize(batch_id="audit-1", result_sha256=RESULT)
    assert store.status("audit-1") == "FINALIZED"
    with pytest.raises(AuditLedgerError, match="invalid/repeated"):
        store.finalize(batch_id="audit-1", result_sha256=RESULT)
    with pytest.raises(AuditLedgerError, match="invalid/repeated"):
        store.burn(batch_id="audit-1", reason_code="RUN_FAILED")


def test_failed_or_interrupted_attempt_is_burned_not_retried(tmp_path):
    store = SealedAuditLedger(tmp_path / "audit.sqlite3")
    reserve(store)
    store.burn(batch_id="audit-1", reason_code="RUN_INTERRUPTED")
    assert store.status("audit-1") == "BURNED"
    with pytest.raises(AuditAlreadyUsed):
        reserve(store, batch="retry", split="e" * 64)


def test_concurrent_reservations_of_same_split_have_exactly_one_winner(tmp_path):
    path = tmp_path / "audit.sqlite3"
    left = SealedAuditLedger(path)
    right = SealedAuditLedger(path)

    def attempt(store, batch):
        try:
            reserve(store, batch=batch)
            return "reserved"
        except AuditAlreadyUsed:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: attempt(*pair), [(left, "left"), (right, "right")]))
    assert sorted(results) == ["rejected", "reserved"]


def test_bad_hashes_duplicate_candidates_and_free_text_burn_reason_rejected(tmp_path):
    store = SealedAuditLedger(tmp_path / "audit.sqlite3")
    with pytest.raises(ValueError, match="SHA-256"):
        store.reserve_batch(batch_id="bad", protocol_sha256="nope", benchmark_sha256=B,
                            sealed_split_sha256=SPLIT, candidate_system_sha256s=(C1,))
    with pytest.raises(ValueError, match="unique"):
        reserve(store, candidates=(C1, C1))
    with pytest.raises(ValueError, match="uppercase code"):
        store.burn(batch_id="absent", reason_code="api failed, secret=...")
