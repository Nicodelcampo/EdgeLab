from __future__ import annotations

import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
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


def private_path(tmp_path: Path) -> Path:
    directory = tmp_path / "audit-custody"
    directory.mkdir(mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    return directory / "audit.sqlite3"


def reserve(store, *, batch="audit-1", split=SPLIT, candidates=(C1, C2)):
    return store.reserve_batch(batch_id=batch, protocol_sha256=P,
                               benchmark_sha256=B, sealed_split_sha256=split,
                               candidate_system_sha256s=candidates)


@pytest.mark.skipif(os.name != "posix", reason="custody permissions are POSIX-specific")
def test_reservation_persists_one_shot_split_in_private_files(tmp_path):
    path = private_path(tmp_path)
    store = SealedAuditLedger(path)
    permit = reserve(store)
    assert permit.status == "RESERVED"
    assert permit.candidate_system_sha256s == (C1, C2)
    assert store.status("audit-1") == "RESERVED"
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    reopened = SealedAuditLedger(path)
    with pytest.raises(AuditAlreadyUsed):
        reserve(reopened, batch="second-id")
    with pytest.raises(AuditAlreadyUsed):
        reserve(reopened)


@pytest.mark.skipif(os.name != "posix", reason="custody permissions are POSIX-specific")
def test_rejects_shared_parent_symlinked_db_and_shared_db(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    shared.chmod(0o755)
    with pytest.raises(ValueError, match="0700"):
        SealedAuditLedger(shared / "audit.sqlite3")

    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    real_db = private / "real.sqlite3"
    real_db.write_bytes(b"")
    alias = private / "alias.sqlite3"
    alias.symlink_to(real_db)
    with pytest.raises(ValueError, match="non-symlink"):
        SealedAuditLedger(alias)

    insecure_db = private / "insecure.sqlite3"
    insecure_db.write_bytes(b"")
    insecure_db.chmod(0o640)
    with pytest.raises(ValueError, match="0600"):
        SealedAuditLedger(insecure_db)


def test_sqlite_triggers_reject_identity_edits_deletes_and_invalid_transitions(tmp_path):
    path = private_path(tmp_path)
    store = SealedAuditLedger(path)
    reserve(store)
    with sqlite3.connect(path) as db:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.execute("UPDATE sealed_audit_batches SET sealed_split_sha256=? WHERE batch_id=?", ("e" * 64, "audit-1"))
        with pytest.raises(sqlite3.IntegrityError, match="transition"):
            db.execute("UPDATE sealed_audit_batches SET status='RESERVED' WHERE batch_id=?", ("audit-1",))
        with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
            db.execute("DELETE FROM sealed_audit_batches WHERE batch_id=?", ("audit-1",))


def test_finalized_batch_cannot_be_replayed_and_scores_are_not_returned(tmp_path):
    store = SealedAuditLedger(private_path(tmp_path))
    reserve(store)
    store.finalize(batch_id="audit-1", result_sha256=RESULT)
    assert store.status("audit-1") == "FINALIZED"
    with pytest.raises(AuditLedgerError, match="invalid/repeated"):
        store.finalize(batch_id="audit-1", result_sha256=RESULT)
    with pytest.raises(AuditLedgerError, match="invalid/repeated"):
        store.burn(batch_id="audit-1", reason_code="RUN_FAILED")


def test_failed_or_interrupted_attempt_is_burned_not_retried(tmp_path):
    store = SealedAuditLedger(private_path(tmp_path))
    reserve(store)
    store.burn(batch_id="audit-1", reason_code="RUN_INTERRUPTED")
    assert store.status("audit-1") == "BURNED"
    with pytest.raises(AuditAlreadyUsed):
        reserve(store, batch="retry", split="e" * 64)


def test_concurrent_reservations_of_same_split_have_exactly_one_winner(tmp_path):
    path = private_path(tmp_path)
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
    store = SealedAuditLedger(private_path(tmp_path))
    with pytest.raises(ValueError, match="SHA-256"):
        store.reserve_batch(batch_id="bad", protocol_sha256="nope", benchmark_sha256=B,
                            sealed_split_sha256=SPLIT, candidate_system_sha256s=(C1,))
    with pytest.raises(ValueError, match="unique"):
        reserve(store, candidates=(C1, C1))
    with pytest.raises(ValueError, match="uppercase code"):
        store.burn(batch_id="absent", reason_code="api failed, secret=...")
