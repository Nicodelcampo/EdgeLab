"""Durable, append-only, hash-chained storage for the Experimental Hippocampus.

The reconstructed hippocampus (`hippocampus.py`) keeps episodes, steps,
failures, lessons and counterexamples in memory: every process restart forgot
everything the Brain ever learned. This module closes that gap without
weakening any invariant:

- APPEND-ONLY: records are never mutated or deleted; corrections are new
  records (LEDGER_APPEND_ONLY).
- TAMPER-EVIDENT: every record carries the SHA-256 of the canonical payload
  chained to the previous record's hash. Replaying a modified ledger raises
  `LedgerIntegrityError` at the exact divergence point. A valid suffix rollback
  requires an externally trusted tip hash to detect; pass it when opening or
  verifying a ledger.
- DETERMINISTIC: replaying the same ledger always reconstructs the same
  in-memory hippocampus state.
- FAIL-CLOSED: outcomes/holdout flags are enforced on ingest; an invalidated
  artifact cannot be silently reused after a restart because invalidation
  status is itself persisted.

The store is a plain JSONL file so it stays diffable, greppable and hostable
anywhere (repo artifact, Kaggle package, object storage) without a database.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable

from .hippocampus import HippocampusMemory

LEDGER_SCHEMA = "edgelab_hippocampus_ledger_v1"
GENESIS_HASH = "0" * 64

_RECORD_TYPES = {
    "episode_registered",
    "step_recorded",
    "expectation_recorded",
    "failure_recorded",
    "success_recorded",
    "lesson_recorded",
    "counterexample_recorded",
    "repair_recorded",
    "invalidation_recorded",
}


class LedgerIntegrityError(ValueError):
    """Raised when a ledger fails hash-chain or schema verification."""


class UnknownRecordTypeError(ValueError):
    """Raised when a ledger contains a record type this build cannot replay."""


def _canonical(payload: Any) -> bytes:
    def default(value: Any) -> Any:
        if is_dataclass(value) and not isinstance(value, type):
            return asdict(value)
        raise TypeError(f"not serializable in ledger: {type(value)!r}")

    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        default=default,
    ).encode("utf-8")


def _record_hash(record_type: str, payload: Any, prev_hash: str) -> str:
    body = _canonical({"type": record_type, "payload": payload,
                       "prev_hash": prev_hash})
    return hashlib.sha256(body).hexdigest()


def _payload_dict(payload: Any) -> dict[str, Any]:
    if is_dataclass(payload) and not isinstance(payload, type):
        data = asdict(payload)
        # `robustness` and `conditions` were added to LessonCandidate after
        # ledger v1 was pinned. Omit their default values so deterministic v1
        # builders keep emitting the original canonical bytes; non-default
        # values remain representable without requiring a migration.
        if (hasattr(payload, "robustness") and data.get("robustness") == "UNRATED"
                and data.get("conditions") == []):
            data.pop("robustness", None)
            data.pop("conditions", None)
        return data
    if isinstance(payload, dict):
        return payload
    raise TypeError(f"ledger payload must be a dataclass or dict, got {type(payload)!r}")


class DurableHippocampus:
    """HippocampusMemory mirrored to an append-only hash-chained JSONL ledger.

    Every `record_*`/`register_*` call writes through to the ledger first and
    only then mutates memory, so a crash never leaves memory ahead of disk.
    """

    def __init__(self, ledger_path: str | Path,
                 memory: HippocampusMemory | None = None,
                 expected_tip_hash: str | None = None) -> None:
        self.ledger_path = Path(ledger_path)
        # Replay to a shadow object so an integrity/anchor failure cannot
        # partially mutate a caller-supplied memory instance.
        supplied_memory = memory
        self.memory = deepcopy(memory) if memory is not None else HippocampusMemory()
        self._prev_hash = GENESIS_HASH
        self._poisoned = False
        self.invalidations: dict[str, str] = {}
        if self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
            self._prev_hash = self._replay_into(self.memory)
        if expected_tip_hash is not None and self._prev_hash != expected_tip_hash:
            raise LedgerIntegrityError(
                "ledger tip does not match externally trusted expected_tip_hash")
        if supplied_memory is not None:
            supplied_memory.__dict__.clear()
            supplied_memory.__dict__.update(self.memory.__dict__)
            self.memory = supplied_memory

    # -- write path -------------------------------------------------------

    def _append(self, record_type: str, payload: Any) -> str:
        if self._poisoned:
            raise LedgerIntegrityError(
                "store disabled after a failed append; reopen and verify the ledger")
        if record_type not in _RECORD_TYPES:
            raise UnknownRecordTypeError(record_type)
        data = _payload_dict(payload)
        digest = _record_hash(record_type, data, self._prev_hash)
        line = json.dumps({
            "schema": LEDGER_SCHEMA,
            "type": record_type,
            "prev_hash": self._prev_hash,
            "hash": digest,
            "payload": data,
        }, ensure_ascii=False, sort_keys=True)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        serialized_line = line + "\n"
        try:
            with self.ledger_path.open("a", encoding="utf-8") as fh:
                written = fh.write(serialized_line)
                if written != len(serialized_line):
                    raise OSError("incomplete ledger append")
        except OSError:
            # An I/O exception may occur after a partial line reached disk.
            # Do not append behind an uncertain tail; require reopen/verification.
            self._poisoned = True
            raise
        self._prev_hash = digest
        return digest

    @staticmethod
    def _validate_lesson_authority(lesson) -> None:
        """Enforce the current durable-store ceiling: proposed, low confidence."""
        if lesson.status != "PROPOSED" or lesson.confidence != "LOW":
            raise ValueError(
                "durable ledger accepts only PROPOSED/LOW lessons; adjudication is separate")

    def _record(self, record_type: str, payload: Any, apply_to_memory) -> str:
        """Validate a record against a shadow state before touching the ledger.

        HippocampusMemory methods enforce semantic invariants (for example,
        episode existence and duplicate episode IDs). Validate on a copy first
        so a rejected operation cannot leave an orphaned row in the ledger.
        Publish the validated state only after the append succeeds.
        """
        candidate = deepcopy(self.memory)
        apply_to_memory(candidate)
        digest = self._append(record_type, payload)
        # Preserve the identity of a caller-supplied HippocampusMemory object.
        self.memory.__dict__.clear()
        self.memory.__dict__.update(candidate.__dict__)
        return digest

    def register_episode(self, episode) -> None:
        # __post_init__ only guards construction; re-check at the ledger gate so
        # a mutated episode can never be persisted with outcomes open.
        if getattr(episode, "outcomes_inspected", False):
            raise ValueError("outcomes_inspected must be False to enter the ledger")
        self._record("episode_registered", episode,
                     lambda memory: memory.register_episode(episode))

    def record_step(self, step) -> None:
        self._record("step_recorded", step,
                     lambda memory: memory.record_step(step))

    def record_expectation(self, expectation) -> None:
        self._record("expectation_recorded", expectation,
                     lambda memory: memory.record_expectation(expectation))

    def record_failure(self, failure) -> None:
        self._record("failure_recorded", failure,
                     lambda memory: memory.record_failure(failure))

    def record_success(self, success) -> None:
        self._record("success_recorded", success,
                     lambda memory: memory.record_success(success))

    def record_lesson(self, lesson) -> None:
        self._validate_lesson_authority(lesson)
        self._record("lesson_recorded", lesson,
                     lambda memory: memory.record_lesson(lesson))

    def record_counterexample(self, counterexample) -> None:
        self._record("counterexample_recorded", counterexample,
                     lambda memory: memory.record_counterexample(counterexample))

    def record_repair(self, repair, episode_id: str) -> None:
        payload = _payload_dict(repair)
        payload["episode_id"] = episode_id
        self._record("repair_recorded", payload,
                     lambda memory: memory.record_repair(repair, episode_id))

    def record_invalidation(self, artifact_id: str, status: str) -> None:
        """Persist an artifact invalidation status so restarts cannot forget it."""
        if not artifact_id.strip() or not status.strip():
            raise ValueError("artifact_id and status must be non-empty")
        candidate = dict(self.invalidations)
        candidate[artifact_id] = status
        self._append("invalidation_recorded",
                     {"artifact_id": artifact_id, "status": status})
        self.invalidations.clear()
        self.invalidations.update(candidate)

    def reuse_artifact(self, artifact_id: str, context: str = "") -> dict[str, Any]:
        """Gate artifact reuse against the *persisted* invalidation map."""
        if self._poisoned:
            raise LedgerIntegrityError(
                "store disabled after a failed append; reopen and verify the ledger")
        return self.memory.reuse_artifact(artifact_id, self.invalidations, context)

    # -- read path ---------------------------------------------------------

    def _replay_into(self, memory: HippocampusMemory) -> str:
        """Replay the ledger into `memory`; returns the verified tip hash."""
        prev = GENESIS_HASH
        tip = GENESIS_HASH
        with self.ledger_path.open("r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise LedgerIntegrityError(
                        f"line {lineno}: invalid JSON: {exc}") from exc
                if record.get("schema") != LEDGER_SCHEMA:
                    raise LedgerIntegrityError(
                        f"line {lineno}: unknown schema {record.get('schema')!r}")
                if record.get("prev_hash") != prev:
                    raise LedgerIntegrityError(
                        f"line {lineno}: chain break (prev_hash mismatch)")
                rtype = record.get("type")
                if rtype not in _RECORD_TYPES:
                    raise UnknownRecordTypeError(
                        f"line {lineno}: unknown record type {rtype!r}")
                payload = record.get("payload")
                expected = _record_hash(rtype, payload, prev)
                if record.get("hash") != expected:
                    raise LedgerIntegrityError(
                        f"line {lineno}: payload hash mismatch")
                self._apply(memory, rtype, payload)
                prev = expected
                tip = expected
        return tip

    def _apply(self, memory: HippocampusMemory, rtype: str,
               payload: dict[str, Any]) -> None:
        from . import hippocampus as h

        builders: dict[str, Callable[[], None]] = {
            "episode_registered": lambda: memory.register_episode(h.AnalysisEpisode(**payload)),
            "step_recorded": lambda: memory.record_step(h.StepExecution(**payload)),
            "expectation_recorded": lambda: memory.record_expectation(h.Expectation(**payload)),
            "failure_recorded": lambda: memory.record_failure(h.FailureEvent(**payload)),
            "success_recorded": lambda: memory.record_success(h.SuccessEvent(**payload)),
            "lesson_recorded": lambda: self._replay_lesson(memory, h, payload),
            "counterexample_recorded": lambda: memory.record_counterexample(h.Counterexample(**payload)),
            "repair_recorded": lambda: memory.record_repair(
                h.RepairAction(**{k: v for k, v in payload.items() if k != "episode_id"}),
                str(payload["episode_id"])),
            "invalidation_recorded": lambda: self.invalidations.__setitem__(
                str(payload["artifact_id"]), str(payload["status"])),
        }
        builders[rtype]()

    def _replay_lesson(self, memory: HippocampusMemory, h, payload: dict[str, Any]) -> None:
        lesson = h.LessonCandidate(**payload)
        try:
            self._validate_lesson_authority(lesson)
        except ValueError as exc:
            raise LedgerIntegrityError(
                "ledger contains a lesson above the PROPOSED/LOW authority ceiling") from exc
        memory.record_lesson(lesson)

    # -- introspection -----------------------------------------------------

    def render_markdown(self) -> str:
        """Narrative projection of the ledger (CerebroSSRN parity, 2026-09-23).

        The old brain's LEDGER_EXPERIMENTOS.md proved the value of a readable
        ledger; the durable JSONL is machine-canonical, this is the human view.
        Pure function of current memory state; deterministic ordering.
        """
        lines = ["# Ledger de experimentos — Hipocampo EdgeLab", ""]
        for ep_id in sorted(self.memory.episodes):
            rec = self.memory.reconstruct_episode(ep_id)
            ep = rec["episode"]
            lines.append(f"## {ep.episode_id} — {ep.status}")
            lines.append("")
            lines.append(f"**Goal**: {ep.goal}")
            for f in rec["failures"]:
                lines.append(f"- ❌ **{f.error_type}**: {f.description} (root: {f.root_cause})")
            for s in rec["successes"]:
                lines.append(f"- ✅ {s.description}")
            for l in rec["lessons"]:
                lines.append(
                    f"- 📘 **{l.lesson_id}** [{l.status}/{l.confidence}/{l.robustness}] {l.statement}")
            lines.append("")
        for target in sorted(self.memory.counterexamples):
            lines.append(f"## Contraejemplos — {target}")
            lines.append("")
            for cx in self.memory.counterexamples[target]:
                lines.append(f"- **{cx.counterexample_id}** ({cx.status}): {cx.observed_behavior} — {cx.why_it_violates} [{cx.evidence_ref}]")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    @property
    def tip_hash(self) -> str:
        """SHA-256 tip of the verified chain; genesis when empty."""
        return self._prev_hash

    def verify(self, expected_tip_hash: str | None = None) -> str:
        """Re-verify chain; optionally compare its tip to a trusted external hash.

        The expected hash must be stored independently of this ledger (for
        example, in a reviewed manifest); a value read from the ledger itself
        does not protect against suffix rollback.
        """
        probe = HippocampusMemory()
        saved = self.invalidations
        self.invalidations = {}
        try:
            tip = self._replay_into(probe)
            if expected_tip_hash is not None and tip != expected_tip_hash:
                raise LedgerIntegrityError(
                    "ledger tip does not match externally trusted expected_tip_hash")
            return tip
        finally:
            self.invalidations = saved
