"""Durable, append-only, hash-chained storage for the Experimental Hippocampus.

The reconstructed hippocampus (`hippocampus.py`) keeps episodes, steps,
failures, lessons and counterexamples in memory: every process restart forgot
everything the Brain ever learned. This module closes that gap without
weakening any invariant:

- APPEND-ONLY: records are never mutated or deleted; corrections are new
  records (LEDGER_APPEND_ONLY).
- TAMPER-EVIDENT: every record carries the SHA-256 of the canonical payload
  chained to the previous record's hash. Replaying a modified ledger raises
  `LedgerIntegrityError` at the exact divergence point.
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
        return asdict(payload)
    if isinstance(payload, dict):
        return payload
    raise TypeError(f"ledger payload must be a dataclass or dict, got {type(payload)!r}")


class DurableHippocampus:
    """HippocampusMemory mirrored to an append-only hash-chained JSONL ledger.

    Every `record_*`/`register_*` call writes through to the ledger first and
    only then mutates memory, so a crash never leaves memory ahead of disk.
    """

    def __init__(self, ledger_path: str | Path,
                 memory: HippocampusMemory | None = None) -> None:
        self.ledger_path = Path(ledger_path)
        self.memory = memory if memory is not None else HippocampusMemory()
        self._prev_hash = GENESIS_HASH
        self.invalidations: dict[str, str] = {}
        if self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
            self._prev_hash = self._replay_into(self.memory)

    # -- write path -------------------------------------------------------

    def _append(self, record_type: str, payload: Any) -> str:
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
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        self._prev_hash = digest
        return digest

    def register_episode(self, episode) -> None:
        # __post_init__ only guards construction; re-check at the ledger gate so
        # a mutated episode can never be persisted with outcomes open.
        if getattr(episode, "outcomes_inspected", False):
            raise ValueError("outcomes_inspected must be False to enter the ledger")
        self._append("episode_registered", episode)
        self.memory.register_episode(episode)

    def record_step(self, step) -> None:
        self._append("step_recorded", step)
        self.memory.record_step(step)

    def record_expectation(self, expectation) -> None:
        self._append("expectation_recorded", expectation)
        self.memory.record_expectation(expectation)

    def record_failure(self, failure) -> None:
        self._append("failure_recorded", failure)
        self.memory.record_failure(failure)

    def record_success(self, success) -> None:
        self._append("success_recorded", success)
        self.memory.record_success(success)

    def record_lesson(self, lesson) -> None:
        self._append("lesson_recorded", lesson)
        self.memory.record_lesson(lesson)

    def record_counterexample(self, counterexample) -> None:
        self._append("counterexample_recorded", counterexample)
        self.memory.record_counterexample(counterexample)

    def record_repair(self, repair, episode_id: str) -> None:
        payload = _payload_dict(repair)
        payload["episode_id"] = episode_id
        self._append("repair_recorded", payload)
        self.memory.record_repair(repair, episode_id)

    def record_invalidation(self, artifact_id: str, status: str) -> None:
        """Persist an artifact invalidation status so restarts cannot forget it."""
        if not artifact_id.strip() or not status.strip():
            raise ValueError("artifact_id and status must be non-empty")
        self._append("invalidation_recorded",
                     {"artifact_id": artifact_id, "status": status})
        self.invalidations[artifact_id] = status

    def reuse_artifact(self, artifact_id: str, context: str = "") -> dict[str, Any]:
        """Gate artifact reuse against the *persisted* invalidation map."""
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
            "lesson_recorded": lambda: memory.record_lesson(h.LessonCandidate(**payload)),
            "counterexample_recorded": lambda: memory.record_counterexample(h.Counterexample(**payload)),
            "repair_recorded": lambda: memory.record_repair(
                h.RepairAction(**{k: v for k, v in payload.items() if k != "episode_id"}),
                str(payload["episode_id"])),
            "invalidation_recorded": lambda: self.invalidations.__setitem__(
                str(payload["artifact_id"]), str(payload["status"])),
        }
        builders[rtype]()

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

    def verify(self) -> str:
        """Re-verify the whole chain without mutating anything; returns tip."""
        probe = HippocampusMemory()
        saved = self.invalidations
        self.invalidations = {}
        try:
            return self._replay_into(probe)
        finally:
            self.invalidations = saved
