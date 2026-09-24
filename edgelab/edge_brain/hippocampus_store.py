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
import re
import os
import sys
from contextlib import contextmanager
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
    "dependency_recorded",
    "campaign_approved",
    "trial_recorded",
    "spec_confirmed",
}


class CampaignBudgetError(ValueError):
    """Prueba fuera de una campana aprobada o por encima de su presupuesto (regla STOP ejecutable)."""


def ledger_record_hashes(ledger_path: str | Path) -> list[str]:
    """Hash de cada registro en orden (sin replay semantico: solo lee la cadena ya escrita)."""
    out = []
    with Path(ledger_path).open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if raw:
                out.append(json.loads(raw)["hash"])
    return out


def verify_anchors(ledger_path: str | Path, anchors: list[dict[str, Any]]) -> None:
    """APPEND-ONLY ENTRE COMMITS. Cada ancla {"records": n, "tip": h} dice que el registro n-esimo tenia hash h.
    Si alguna deja de valer, el ledger reescribio su pasado (o se trunco) y se levanta LedgerIntegrityError.
    Las anclas se agregan, nunca se editan: el archivo de anclas es append-only por la misma regla."""
    DurableHippocampus(ledger_path)                      # la cadena completa verifica
    hashes = ledger_record_hashes(ledger_path)
    last = 0
    for a in anchors:
        n, tip = int(a["records"]), str(a["tip"])
        if n < last:
            raise LedgerIntegrityError("anchors must be non-decreasing in record count")
        last = n
        if n > len(hashes) or hashes[n - 1] != tip:
            raise LedgerIntegrityError(
                f"anchor at record {n} no longer holds: ledger history was rewritten or truncated")


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


INVALIDATION_STATUSES = frozenset({
    "INVALIDATED_BY_MEASUREMENT_ERROR", "STALE_BY_DEPENDENCY", "REQUIRES_REAUDIT"})


@contextmanager
def _exclusive_lock(ledger_path: Path):
    """Lock de SO sobre `<ledger>.lock` (un solo escritor por ledger, tambien entre procesos)."""
    lock_path = ledger_path.with_name(ledger_path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+b")
    try:
        if sys.platform == "win32":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if sys.platform == "win32":
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


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
        self._offset = 0          # bytes del ledger que esta instancia verifico (fin de su vista)
        self.invalidations: dict[str, str] = {}
        self.dependencies: list[dict[str, str]] = []
        self.campaigns: dict[str, dict[str, Any]] = {}
        self.trials: dict[str, dict[str, Any]] = {}
        self.specs: dict[str, dict[str, Any]] = {}
        if self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
            self._prev_hash = self._replay_into(self.memory)
            self._offset = self._checked_size()
        if expected_tip_hash is not None and self._prev_hash != expected_tip_hash:
            raise LedgerIntegrityError(
                "ledger tip does not match externally trusted expected_tip_hash")
        if supplied_memory is not None:
            supplied_memory.__dict__.clear()
            supplied_memory.__dict__.update(self.memory.__dict__)
            self.memory = supplied_memory

    # -- write path -------------------------------------------------------

    def _checked_size(self) -> int:
        """Tamano del ledger en disco; exige que termine en salto de linea (una cola cortada no se acepta)."""
        size = self.ledger_path.stat().st_size if self.ledger_path.exists() else 0
        if size:
            with self.ledger_path.open("rb") as fh:
                fh.seek(size - 1)
                if fh.read(1) != b"\n":
                    raise LedgerIntegrityError("ledger tail is torn (missing final newline); refuse to append")
        return size

    def _ensure_current(self) -> None:
        """La vista de esta instancia debe coincidir con el disco: otro escritor o un truncado la invalidan."""
        size = self.ledger_path.stat().st_size if self.ledger_path.exists() else 0
        if size != self._offset:
            self._poisoned = True
            raise LedgerIntegrityError(
                f"ledger changed on disk since this store read it ({self._offset} -> {size} bytes); reopen")

    def _append(self, record_type: str, payload: Any) -> tuple[str, dict[str, Any]]:
        """Escribe un registro bajo lock exclusivo. Devuelve (hash, payload tal como quedo en disco)."""
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
        raw = (line + "\n").encode("utf-8")
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.ledger_path):
            self._ensure_current()
            try:
                with self.ledger_path.open("ab") as fh:
                    fh.write(raw)
                    fh.flush()
                    os.fsync(fh.fileno())
            except BaseException:
                # Cualquier interrupcion (OSError, Ctrl-C, SystemExit) puede dejar una linea a medias: se trunca de
                # vuelta al ultimo byte verificado para que el ledger siga siendo reproducible, y el store queda
                # envenenado hasta reabrir.
                self._poisoned = True
                try:
                    with open(self.ledger_path, "r+b") as fh:
                        fh.truncate(self._offset)
                except Exception:
                    pass
                raise
            self._offset += len(raw)
        self._prev_hash = digest
        return digest, json.loads(line)["payload"]

    @staticmethod
    def _validate_lesson_authority(lesson) -> None:
        """Enforce the current durable-store ceiling: proposed, low confidence."""
        if lesson.status != "PROPOSED" or lesson.confidence != "LOW":
            raise ValueError(
                "durable ledger accepts only PROPOSED/LOW lessons; adjudication is separate")

    def _record(self, record_type: str, payload: Any, apply_to_memory) -> str:
        """Valida contra una copia del estado, escribe, y recien ahi publica en memoria.

        Lo que se publica NO es el objeto del llamador sino el payload decodificado desde la linea escrita, por el
        mismo camino que el replay (`_apply`). Asi memoria == replay(ledger) por construccion y un objeto que el
        llamador modifique despues no altera la memoria (antes una leccion podia quedar ADOPTED/HIGH en memoria
        mientras el ledger decia PROPOSED/LOW)."""
        candidate = deepcopy(self.memory)
        apply_to_memory(candidate)
        digest, written = self._append(record_type, payload)
        self._apply(self.memory, record_type, written)
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
        """Persiste una invalidacion. Estados cerrados: un error de tipeo o un 'ELIGIBLE' no pueden rehabilitar un
        artefacto por esta via (la rehabilitacion requiere un registro de adjudicacion aparte, no implementado)."""
        if not artifact_id or artifact_id != artifact_id.strip():
            raise ValueError("artifact_id must be non-empty and without surrounding whitespace")
        if status not in INVALIDATION_STATUSES:
            raise ValueError(f"status must be one of {sorted(INVALIDATION_STATUSES)}, got {status!r}")
        self._append("invalidation_recorded", {"artifact_id": artifact_id, "status": status})
        self.invalidations[artifact_id] = status

    # -- dependencias e invalidacion en cascada ------------------------------

    def record_dependency(self, source_id: str, target_id: str, relation: str) -> None:
        """`source_id` depende de `target_id` (misma semantica que `invalidation.DependencyEdge`)."""
        from .invalidation import DependencyEdge
        DependencyEdge(source_id, target_id, relation)          # valida relacion y auto-dependencia
        row = {"source_id": source_id, "target_id": target_id, "relation": relation}
        if row in self.dependencies:
            return
        self._append("dependency_recorded", row)
        self.dependencies.append(row)

    def invalidate_with_cascade(self, artifact_id: str, status: str = "INVALIDATED_BY_MEASUREMENT_ERROR") -> dict[str, str]:
        """Invalida un artefacto y propaga por las dependencias PERSISTIDAS (duras -> STALE_BY_DEPENDENCY,
        evidenciales -> REQUIRES_REAUDIT). Cada nodo afectado queda como fila propia del ledger."""
        from .invalidation import DependencyEdge, propagate_invalidation, _STATUS_PRIORITY
        edges = [DependencyEdge(d["source_id"], d["target_id"], d["relation"]) for d in self.dependencies]
        statuses = propagate_invalidation([artifact_id], edges)
        statuses[artifact_id] = status
        for node, st in sorted(statuses.items()):
            cur = self.invalidations.get(node)
            if cur is None or _STATUS_PRIORITY[st] > _STATUS_PRIORITY[cur]:
                self.record_invalidation(node, st)
        return statuses

    # -- campanas pre-aprobadas y contabilidad de pruebas ---------------------

    def record_spec_confirmation(self, spec_id: str, spec_sha256: str, preview_sha256: str,
                                 confirmed_by: str, recorded_by: str) -> None:
        """Nico confirmo VISUALMENTE (revision ciega en `spec_review.html`) que la especificacion con este hash es lo
        que quiere probar. Solo un humano distinto de quien registra (NO_SELF_APPROVAL)."""
        if not confirmed_by.startswith("human:") or confirmed_by == recorded_by:
            raise ValueError("spec must be confirmed by a human ('human:<name>') other than the recorder")
        if not re.fullmatch(r"[0-9a-f]{64}", spec_sha256 or "") or not re.fullmatch(r"[0-9a-f]{64}", preview_sha256 or ""):
            raise ValueError("spec_sha256 and preview_sha256 must be full sha256 hex digests")
        row = dict(spec_id=spec_id, spec_sha256=spec_sha256, preview_sha256=preview_sha256,
                   confirmed_by=confirmed_by, recorded_by=recorded_by)
        self._append("spec_confirmed", row)
        self.specs[spec_sha256] = row

    def record_campaign(self, campaign_id: str, family: str, approved_by: str, recorded_by: str,
                        max_trials: int, prereg_ref: str, data_scope: str, spec_sha256: str | None = None) -> None:
        """Campana aprobada por un HUMANO (`approved_by` = "human:<nombre>"), distinta de quien la registra
        (NO_SELF_APPROVAL). Fija el presupuesto de pruebas: el agente corre solo adentro, se detiene afuera.
        Desde 2026-09-24 exige `spec_sha256` de una especificacion CONFIRMADA en revision ciega: sin eso no hay
        campana (las campanas anteriores, sin ese campo, siguen reproduciendose en el replay)."""
        if not approved_by.startswith("human:") or approved_by == recorded_by:
            raise ValueError("campaign must be approved by a human ('human:<name>') other than the recorder")
        if campaign_id in self.campaigns or max_trials < 1 or not prereg_ref or not family or not data_scope:
            raise ValueError("duplicate campaign or missing family/prereg/data_scope/budget")
        if spec_sha256 is None or spec_sha256 not in self.specs:
            raise CampaignBudgetError("campaign requires a spec confirmed in blind visual review (record_spec_confirmation)")
        row = dict(campaign_id=campaign_id, family=family, approved_by=approved_by, recorded_by=recorded_by,
                   max_trials=int(max_trials), prereg_ref=prereg_ref, data_scope=data_scope, spec_sha256=spec_sha256)
        self._append("campaign_approved", row)
        self.campaigns[campaign_id] = row

    def _check_trial(self, row: dict[str, Any]) -> None:
        camp = self.campaigns.get(row["campaign_id"])
        if camp is None:
            raise CampaignBudgetError(f"no approved campaign {row['campaign_id']!r}: trial requires approval (STOP)")
        if row["trial_id"] in self.trials:
            raise CampaignBudgetError(f"duplicate trial_id {row['trial_id']!r}")
        used = sum(1 for t in self.trials.values() if t["campaign_id"] == row["campaign_id"])
        if used >= camp["max_trials"]:
            raise CampaignBudgetError(
                f"campaign {row['campaign_id']!r} exhausted its budget ({camp['max_trials']} trials): stop and ask")

    def record_trial(self, campaign_id: str, trial_id: str, hypothesis: str, variant: str,
                     metric: str, result: str) -> None:
        """Cada prueba sobre retornos cuenta, gane o pierda: es el N que entra a DSR/PBO/Bonferroni."""
        row = dict(campaign_id=campaign_id, trial_id=trial_id, hypothesis=hypothesis, variant=variant,
                   metric=metric, result=result)
        self._check_trial(row)
        self._append("trial_recorded", row)
        self.trials[trial_id] = row

    def trials_by_family(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self.trials.values():
            fam = self.campaigns[t["campaign_id"]]["family"]
            out[fam] = out.get(fam, 0) + 1
        return out

    def reuse_artifact(self, artifact_id: str, context: str = "") -> dict[str, Any]:
        """Gate artifact reuse against the *persisted* invalidation map (y exige que la vista este al dia)."""
        if self._poisoned:
            raise LedgerIntegrityError(
                "store disabled after a failed append; reopen and verify the ledger")
        self._ensure_current()
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
            "invalidation_recorded": lambda: self._replay_invalidation(payload),
            "dependency_recorded": lambda: self.dependencies.append(dict(payload)),
            "campaign_approved": lambda: self._replay_campaign(payload),
            "trial_recorded": lambda: self._replay_trial(payload),
            "spec_confirmed": lambda: self._replay_spec(payload),
        }
        builders[rtype]()

    def _replay_spec(self, payload: dict[str, Any]) -> None:
        if not str(payload.get("confirmed_by", "")).startswith("human:") or payload.get("confirmed_by") == payload.get("recorded_by"):
            raise LedgerIntegrityError("ledger contains a self-confirmed or non-human spec confirmation")
        self.specs[str(payload["spec_sha256"])] = dict(payload)

    def _replay_campaign(self, payload: dict[str, Any]) -> None:
        if not str(payload.get("approved_by", "")).startswith("human:") or payload.get("approved_by") == payload.get("recorded_by"):
            raise LedgerIntegrityError("ledger contains a self-approved or non-human campaign")
        if "spec_sha256" in payload and payload["spec_sha256"] not in self.specs:
            raise LedgerIntegrityError("ledger contains a campaign citing an unconfirmed spec")
        self.campaigns[str(payload["campaign_id"])] = dict(payload)

    def _replay_trial(self, payload: dict[str, Any]) -> None:
        try:
            self._check_trial(dict(payload))
        except CampaignBudgetError as exc:
            raise LedgerIntegrityError(f"ledger contains a trial outside an approved budget: {exc}") from exc
        self.trials[str(payload["trial_id"])] = dict(payload)

    def _replay_invalidation(self, payload: dict[str, Any]) -> None:
        status = str(payload["status"])
        if status not in INVALIDATION_STATUSES:
            raise LedgerIntegrityError(f"ledger contains an invalidation with unknown status {status!r}")
        self.invalidations[str(payload["artifact_id"])] = status

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
        saved = (self.invalidations, self.dependencies, self.campaigns, self.trials, self.specs)
        self.invalidations, self.dependencies, self.campaigns, self.trials, self.specs = {}, [], {}, {}, {}
        try:
            tip = self._replay_into(probe)
            if expected_tip_hash is not None and tip != expected_tip_hash:
                raise LedgerIntegrityError(
                    "ledger tip does not match externally trusted expected_tip_hash")
            return tip
        finally:
            self.invalidations, self.dependencies, self.campaigns, self.trials, self.specs = saved
