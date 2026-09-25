"""Durable, one-shot reservation ledger for a future sealed final audit.

This local prototype stores audit identities and state transitions only; it
never stores or returns test contents, row-level outcomes, or candidate scores.
On POSIX it fails closed unless the ledger lives in a caller-owned 0700
 directory and the database is a caller-owned, single-link 0600 regular file.
SQLite triggers reject accidental identity edits, deletes, and invalid state
transitions. These are defense-in-depth against mistakes, NOT a security
boundary against the host owner, who can alter the file/schema or bypass this
module. Real custody still requires a separate trusted runner with exclusive
access to sealed data and authenticated receipts.
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
from urllib.parse import quote

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
    """SQLite one-shot ledger on a private, persistent local filesystem.

    `reserve_batch` commits the reservation before a runner opens any sealed
    inputs. Duplicate batch IDs and duplicate sealed-split hashes are rejected.
    Failed/interrupted runs stay RESERVED or become BURNED; neither is reusable.
    Only digest/state metadata is retained, never underlying scores.

    The 0700 directory is important: SQLite's transient journal files are
    created beside the database. This class deliberately rejects a shared
    directory instead of silently changing its permissions.
    """

    def __init__(self, path: str | Path):
        if os.name != "posix":
            raise AuditLedgerError("sealed audit custody requires POSIX file permissions")
        self.path = Path(os.path.abspath(Path(path).expanduser()))
        self._require_private_parent()
        self._secure_database_file()
        with closing(self._connect()) as db:
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
            db.execute("""CREATE TRIGGER IF NOT EXISTS sealed_audit_no_delete
                BEFORE DELETE ON sealed_audit_batches
                BEGIN SELECT RAISE(ABORT, 'sealed audit rows cannot be deleted'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS sealed_audit_immutable_identity
                BEFORE UPDATE OF batch_id, protocol_sha256, benchmark_sha256,
                    sealed_split_sha256, candidate_system_sha256s_json, created_at_utc
                ON sealed_audit_batches
                BEGIN SELECT RAISE(ABORT, 'sealed audit identity is immutable'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS sealed_audit_valid_transition
                BEFORE UPDATE ON sealed_audit_batches
                WHEN NOT (
                    OLD.status='RESERVED'
                    AND NEW.status IN ('FINALIZED','BURNED')
                    AND NEW.batch_id=OLD.batch_id
                    AND NEW.protocol_sha256=OLD.protocol_sha256
                    AND NEW.benchmark_sha256=OLD.benchmark_sha256
                    AND NEW.sealed_split_sha256=OLD.sealed_split_sha256
                    AND NEW.candidate_system_sha256s_json=OLD.candidate_system_sha256s_json
                    AND NEW.created_at_utc=OLD.created_at_utc
                    AND NEW.finished_at_utc IS NOT NULL
                    AND ((NEW.status='FINALIZED' AND NEW.result_sha256 IS NOT NULL AND NEW.burn_code IS NULL)
                      OR (NEW.status='BURNED' AND NEW.result_sha256 IS NULL AND NEW.burn_code IS NOT NULL))
                )
                BEGIN SELECT RAISE(ABORT, 'invalid sealed audit state transition'); END""")
            db.commit()

    def _require_private_parent(self) -> None:
        parent = self.path.parent
        if not parent.is_dir():
            raise ValueError("audit ledger parent directory must already exist")
        # Reject symlinked path components: a private-looking alias can point
        # at a shared directory with different access controls.
        if parent.resolve(strict=True) != parent:
            raise ValueError("audit ledger parent path must not contain symlinks")
        info = parent.stat(follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
            raise ValueError("audit ledger directory must be owned by the current user")
        mode = stat.S_IMODE(info.st_mode)
        if mode & 0o077 or mode & 0o700 != 0o700:
            raise ValueError("audit ledger directory must have owner-only 0700 permissions")

    def _secure_database_file(self) -> None:
        """Create as 0600; refuse symlinks, hard links, shared, or foreign files."""
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(self.path, flags, 0o600)
            created = True
        except FileExistsError:
            created = False
            try:
                fd = os.open(self.path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
            except OSError as exc:
                raise ValueError("audit ledger must be a non-symlink regular file") from exc
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("audit ledger must be a regular file")
            if info.st_uid != os.geteuid() or info.st_nlink != 1:
                raise ValueError("audit ledger must be caller-owned with exactly one hard link")
            mode = stat.S_IMODE(info.st_mode)
            if mode & 0o077 or mode & 0o600 != 0o600:
                raise ValueError("audit ledger file must have owner-only 0600 permissions")
            if created:
                os.fsync(fd)
        finally:
            os.close(fd)
        if created:
            dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            dir_fd = os.open(self.path.parent, dir_flags)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

    def _connect(self) -> sqlite3.Connection:
        # mode=rw prevents a typo or deletion from silently creating a new,
        # empty ledger and thereby reopening a previously consumed split.
        uri = "file:" + quote(str(self.path), safe="/") + "?mode=rw"
        db = sqlite3.connect(uri, uri=True, timeout=30, isolation_level=None)
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA temp_store=MEMORY")
        return db

    @staticmethod
    def _validate_batch(batch_id: str, protocol_sha256: str, benchmark_sha256: str,
                        sealed_split_sha256: str, candidate_system_sha256s: tuple[str, ...]) -> tuple[str, ...]:
        if not isinstance(batch_id, str) or not batch_id.strip() or len(batch_id) > 200:
            raise ValueError("batch_id must be a nonempty stable identifier")
        if not all(_valid_sha(v) for v in (protocol_sha256, benchmark_sha256, sealed_split_sha256)):
            raise ValueError("protocol, benchmark, and sealed split require SHA-256 identities")
        if not isinstance(candidate_system_sha256s, (tuple, list)):
            raise ValueError("candidate list must be a tuple or list of SHA-256 identities")
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
