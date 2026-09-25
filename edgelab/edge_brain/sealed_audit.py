"""Durable, one-shot reservation ledger for a future sealed final audit.

This module stores audit identities and state transitions only; it never stores
or returns test contents, row-level outcomes, or candidate scores. It prevents
accidental replay by compliant callers. It is NOT an access-control boundary:
only a separate trusted runner with exclusive access to the sealed data can
prevent a model/operator from reading that data or bypassing this ledger.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import stat
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_HEX_256 = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


class AuditLedgerError(RuntimeError):
    """Invalid audit ledger operation or corrupt state."""


class AuditAlreadyUsed(AuditLedgerError):
    """The audit batch or sealed split has already been reserved."""


@dataclass(frozen=True)
class AuditPermit:
    batch_id: str
    protocol_sha256: str
    benchmark_sha256: str
    sealed_split_sha256: str
    candidate_system_sha256s: tuple[str, ...]
    status: str = "RESERVED"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_sha(value: str) -> bool:
    return isinstance(value, str) and bool(_HEX_256.fullmatch(value))


class SealedAuditLedger:
    """SQLite one-shot ledger. Use on a private, persistent local filesystem.

    `reserve_batch` commits the reservation before a runner opens any sealed
    inputs. Duplicate batch IDs and duplicate sealed-split hashes are rejected.
    Failed/interrupted runs stay RESERVED or become BURNED; neither is reusable.
    Only digest/state metadata is retained, never underlying scores.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().absolute()
        if not self.path.parent.is_dir():
            raise ValueError("audit ledger parent directory must already exist")
        self._secure_database_file()
        with closing(self._connect()) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("""CREATE TABLE IF NOT EXISTS sealed_audit_batches (
                batch_id TEXT PRIMARY KEY,
                protocol_sha256 TEXT NOT NULL,
                benchmark_sha256 TEXT NOT NULL,
                sealed_split_sha256 TEXT NOT NULL UNIQUE,
                candidate_system_sha256s_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('RESERVED','FINALIZED','BURNED')),
                created_at_utc TEXT NOT NULL,
                finished_at_utc TEXT,
                result_sha256 TEXT,
                burn_code TEXT,
                CHECK ((status='RESERVED' AND finished_at_utc IS NULL AND result_sha256 IS NULL AND burn_code IS NULL)
                    OR (status='FINALIZED' AND finished_at_utc IS NOT NULL AND result_sha256 IS NOT NULL AND burn_code IS NULL)
                    OR (status='BURNED' AND finished_at_utc IS NOT NULL AND result_sha256 IS NULL AND burn_code IS NOT NULL))
            )""")
            db.commit()

    def _secure_database_file(self) -> None:
        """Create the DB as owner-only and refuse symlink/non-regular targets."""
        if self.path.is_symlink():
            raise ValueError("audit ledger must not be a symlink")
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(self.path, flags, 0o600)
            os.close(fd)
        except FileExistsError:
            pass
        info = self.path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("audit ledger must be a regular file")
        if os.name == "posix":
            os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _validate_batch(batch_id: str, protocol_sha256: str, benchmark_sha256: str,
                        sealed_split_sha256: str, candidate_system_sha256s: tuple[str, ...]) -> tuple[str, ...]:
        if not isinstance(batch_id, str) or not batch_id.strip() or len(batch_id) > 200:
            raise ValueError("batch_id must be a nonempty stable identifier")
        if not all(_valid_sha(v) for v in (protocol_sha256, benchmark_sha256, sealed_split_sha256)):
            raise ValueError("protocol, benchmark, and sealed split require SHA-256 identities")
        candidates = tuple(sorted(candidate_system_sha256s))
        if not candidates or not all(_valid_sha(v) for v in candidates):
            raise ValueError("pre-registered candidate list must contain SHA-256 identities")
        if len(candidates) != len(set(candidates)):
            raise ValueError("candidate identities must be unique")
        return candidates

    def reserve_batch(self, *, batch_id: str, protocol_sha256: str,
                      benchmark_sha256: str, sealed_split_sha256: str,
                      candidate_system_sha256s: tuple[str, ...]) -> AuditPermit:
        """Irreversibly reserve the complete, pre-registered candidate set.

        Call and durably commit this before the trusted runner accesses the
        sealed split. Reservation itself spends the one-shot opportunity; a
        crash or failed run must be diagnosed out-of-band, not rerun on same data.
        """
        candidates = self._validate_batch(batch_id, protocol_sha256, benchmark_sha256,
                                         sealed_split_sha256, candidate_system_sha256s)
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("""INSERT INTO sealed_audit_batches
                    (batch_id, protocol_sha256, benchmark_sha256, sealed_split_sha256,
                     candidate_system_sha256s_json, status, created_at_utc)
                    VALUES (?, ?, ?, ?, ?, 'RESERVED', ?)""",
                           (batch_id, protocol_sha256, benchmark_sha256, sealed_split_sha256,
                            json.dumps(candidates, separators=(",", ":")), _now()))
                db.commit()
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise AuditAlreadyUsed("batch ID or sealed split already reserved; do not retry") from exc
            except BaseException:
                db.rollback()
                raise
        return AuditPermit(batch_id, protocol_sha256, benchmark_sha256,
                           sealed_split_sha256, candidates)

    def finalize(self, *, batch_id: str, result_sha256: str) -> None:
        """Finalize with a result digest only; the raw score stays outside this ledger."""
        if not _valid_sha(result_sha256):
            raise ValueError("result requires a SHA-256 identity")
        self._transition(batch_id, "FINALIZED", result_sha256=result_sha256)

    def burn(self, *, batch_id: str, reason_code: str) -> None:
        """Permanently consume an interrupted/failed reservation without raw errors."""
        if not isinstance(reason_code, str) or not _REASON.fullmatch(reason_code):
            raise ValueError("reason_code must be a short uppercase code, not free text")
        self._transition(batch_id, "BURNED", burn_code=reason_code)

    def _transition(self, batch_id: str, status: str, *, result_sha256: str | None = None,
                    burn_code: str | None = None) -> None:
        if not isinstance(batch_id, str) or not batch_id.strip():
            raise ValueError("batch_id must be nonempty")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                cur = db.execute("""UPDATE sealed_audit_batches
                    SET status=?, finished_at_utc=?, result_sha256=?, burn_code=?
                    WHERE batch_id=? AND status='RESERVED'""",
                                 (status, _now(), result_sha256, burn_code, batch_id))
                if cur.rowcount != 1:
                    raise AuditLedgerError("unknown batch or invalid/repeated state transition")
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def status(self, batch_id: str) -> str | None:
        """Read state only; never returns candidate scores or final result digest."""
        with closing(self._connect()) as db:
            row = db.execute("SELECT status FROM sealed_audit_batches WHERE batch_id=?", (batch_id,)).fetchone()
        return row[0] if row else None
