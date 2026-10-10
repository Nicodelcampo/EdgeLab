"""Deterministic lexical retrieval over hippocampus ledgers (BM25, pure stdlib).

Closes EDGE-001 partially: edge_brain could only answer from structured state;
now any ledger (or record list) is queryable. Deliberately BM25 instead of
embeddings: the old CerebroSSRN needed a 118MB model download for e5-small;
this runs in CI with zero dependencies and is fully reproducible. Semantic
embeddings can be added later as a second ranker behind the same interface
(`query(index, text) -> [ScoredRecord]`) — the seed benchmark defines
"better", so any future embedder must beat this baseline on it (EDGE-007).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)
_STOPWORDS = frozenset({
    "a", "al", "de", "del", "el", "en", "la", "las", "los", "the", "of",
    "to", "and", "y", "o", "or", "un", "una", "con", "por", "para", "is",
    "se", "no", "su", "sus", "es", "son", "that", "this", "with",
})


def _tokenize(text: str) -> list[str]:
    return [t for t in (tok.lower() for tok in _TOKEN_RE.findall(text))
            if t not in _STOPWORDS and len(t) > 1]


@dataclass(frozen=True)
class ScoredRecord:
    record_id: str
    record_type: str
    score: float
    text: str


def _record_text(record_type: str, payload: dict[str, Any]) -> tuple[str, str]:
    """(record_id, searchable text) for a ledger payload."""
    id_keys = ("lesson_id", "counterexample_id", "failure_id", "success_id",
               "episode_id", "step_id", "expectation_id", "repair_id",
               "artifact_id")
    record_id = next((str(payload[k]) for k in id_keys if payload.get(k)), "")
    text_parts = [str(v) for v in payload.values()
                  if isinstance(v, (str, int, float)) and v is not None]
    return record_id or repr(sorted(payload.items()))[:64], " ".join(text_parts)


class LedgerIndex:
    """BM25 index over ledger-style records. Deterministic by construction."""

    def __init__(self, records: Iterable[tuple[str, dict[str, Any]]],
                 *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self._docs: list[tuple[str, str, str, list[str]]] = []  # id, type, text, tokens
        df: dict[str, int] = {}
        total_len = 0
        for record_type, payload in records:
            record_id, text = _record_text(record_type, payload)
            tokens = _tokenize(text)
            if not tokens:
                continue
            self._docs.append((record_id, record_type, text, tokens))
            total_len += len(tokens)
            for tok in set(tokens):
                df[tok] = df.get(tok, 0) + 1
        self._df = df
        self._n = len(self._docs)
        self._avgdl = (total_len / self._n) if self._n else 0.0

    @classmethod
    def from_ledger(cls, ledger_path: str | Path, **kwargs) -> "LedgerIndex":
        """Indexa SOLO un ledger cuya cadena y techo de autoridad verifican (antes indexaba el JSONL crudo)."""
        import json
        from .hippocampus_store import DurableHippocampus
        DurableHippocampus(ledger_path)          # replay completo: LedgerIntegrityError si algo no cierra
        records = []
        with Path(ledger_path).open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if raw:
                    record = json.loads(raw)
                    records.append((str(record["type"]), record["payload"]))
        return cls(records, **kwargs)

    @classmethod
    def from_memory(cls, memory, **kwargs) -> "LedgerIndex":
        """Index a live HippocampusMemory (all episodes' records)."""
        from dataclasses import asdict
        records: list[tuple[str, dict[str, Any]]] = []
        for ep in memory.episodes.values():
            records.append(("episode_registered", asdict(ep)))
        for steps in memory.steps.values():
            records += [("step_recorded", asdict(s)) for s in steps]
        for fails in memory.failures.values():
            records += [("failure_recorded", asdict(f)) for f in fails]
        for succs in memory.successes.values():
            records += [("success_recorded", asdict(s)) for s in succs]
        for lessons in memory.lessons.values():
            records += [("lesson_recorded", asdict(l)) for l in lessons]
        for cxs in memory.counterexamples.values():
            records += [("counterexample_recorded", asdict(c)) for c in cxs]
        return cls(records, **kwargs)

    def query(self, text: str, *, k: int = 5) -> list[ScoredRecord]:
        q_tokens = _tokenize(text)
        if not q_tokens or not self._n:
            return []
        scored: list[ScoredRecord] = []
        for record_id, record_type, doctext, tokens in self._docs:
            dl = len(tokens)
            tf: dict[str, int] = {}
            for tok in tokens:
                tf[tok] = tf.get(tok, 0) + 1
            score = 0.0
            for tok in q_tokens:
                if tok not in tf:
                    continue
                df = self._df[tok]
                idf = math.log(1 + (self._n - df + 0.5) / (df + 0.5))
                freq = tf[tok]
                denom = freq + self.k1 * (1 - self.b + self.b * dl / self._avgdl)
                score += idf * (freq * (self.k1 + 1)) / denom
            if score > 0:
                scored.append(ScoredRecord(record_id, record_type, score, doctext))
        scored.sort(key=lambda r: (-r.score, r.record_id))  # deterministic ties
        return scored[:k]

    @property
    def size(self) -> int:
        return self._n
