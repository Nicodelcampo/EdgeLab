"""Puente Edge Brain <-> hipocampo bibliografico (CerebroSSRN), 2026-10-09.

El brain tenia dos memorias que no se hablaban:

- ``DurableHippocampus``: lo que EdgeLab vivio (episodios, fallas, exitos, lecciones, contraejemplos).
- ``SSRNBibliographicCortex``: lo que la literatura dice (401 papers, 24.340 pasajes, 771 hallazgos).

Este modulo las une sin debilitar ninguna regla:

1. ``EdgeBrainMemory.recall(query)``: una sola consulta devuelve memoria propia + hallazgos SSRN + pasajes,
   cada resultado con su techo de autoridad explicito. Solo lectura.
2. ``EdgeBrainMemory.consult(...)``: lo mismo, pero deja asentado en el ledger del brain QUE literatura vio,
   para que episodio y con que proposito (registro ``literature_consulted``, hash de cada texto visto).
3. ``EdgeBrainMemory.cite(artifact_id, consultation_id)``: una hipotesis/diseno/leccion declara que se apoyo
   en esa consulta. Si un paper se invalida, la cascada existente marca consulta y artefacto REQUIRES_REAUDIT.

Nada de esto promueve: la literatura entra siempre como ``LITERATURE_CLAIM_UNVERIFIED`` /
``AUTHOR_REPORTED_RESULT`` y ``claims_are_evidence=False``. Busqueda lexica (BM25 + LIKE), determinista y sin
modelos: los hallazgos estan en castellano y los pasajes en ingles, asi que conviene consultar con terminos
en ambos idiomas (p. ej. "order flow imbalance desbalance").
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .bibliographic_cortex import BibliographicCortexError, SSRNBibliographicCortex
from .context_memory import ContextItem, ContextPack, build_deterministic_context_pack
from .hippocampus_store import LITERATURE_AUTHORITY, DurableHippocampus
from .retrieval import LedgerIndex

FINDING_AUTHORITY = "AUTHOR_REPORTED_RESULT"
_FINDING_FIELDS = ("afirmacion", "mercado", "periodo", "magnitud", "condiciones", "robustez")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryHit:
    origin: str            # OWN | FINDING | PASSAGE
    record_id: str
    record_type: str
    score: float
    text: str
    authority_status: str
    source_id: str = ""
    title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Recall:
    query: str
    own: list[MemoryHit] = field(default_factory=list)
    findings: list[MemoryHit] = field(default_factory=list)
    passages: list[MemoryHit] = field(default_factory=list)

    @property
    def literature(self) -> list[MemoryHit]:
        return self.findings + self.passages

    def to_dict(self) -> dict[str, Any]:
        return {"query": self.query, "claims_are_evidence": False,
                "own": [h.to_dict() for h in self.own],
                "findings": [h.to_dict() for h in self.findings],
                "passages": [h.to_dict() for h in self.passages]}

    def context_items(self) -> list[ContextItem]:
        """Items para ``build_deterministic_context_pack`` (presupuesto ~4 caracteres por token)."""
        out = []
        for h in self.own + self.findings + self.passages:
            out.append(ContextItem(record_id=h.record_id, item_type=f"{h.origin}:{h.record_type}",
                                   reason_for_inclusion=f"recall({self.query!r}) score={h.score:.3f} "
                                                        f"authority={h.authority_status}",
                                   estimated_tokens=max(1, len(h.text) // 4)))
        return out


@dataclass(frozen=True)
class Consultation:
    consultation_id: str
    recall: Recall
    ledger_hash: str

    def context_pack(self, context_pack_id: str, episode_id: str, token_budget: int,
                     created_at_utc: str) -> ContextPack:
        return build_deterministic_context_pack(
            context_pack_id=context_pack_id, episode_id=episode_id, token_budget=token_budget,
            provenance=f"literature_consulted:{self.consultation_id}@{self.ledger_hash}",
            candidates=self.recall.context_items(), created_at_utc=created_at_utc)


class EdgeBrainMemory:
    """Memoria unificada del brain: experiencia propia (ledger) + literatura (corpus SSRN)."""

    def __init__(self, store: DurableHippocampus, cortex: SSRNBibliographicCortex) -> None:
        self.store = store
        self.cortex = cortex
        self._titles = {int(k): (v.get("titulo") or "") for k, v in cortex.docs_meta.items()} \
            if isinstance(cortex.docs_meta, dict) else {}
        records = []
        for index, f in enumerate(cortex.findings, start=1):
            try:
                doc_id = int(f.get("doc_id"))
            except (TypeError, ValueError):
                continue
            payload = {"claim_id": f"CLAIM-SSRN-FINDING-{index:04d}", "doc_id": doc_id}
            payload.update({k: str(f.get(k) or "") for k in _FINDING_FIELDS})
            records.append(("finding", payload))
        self._finding_doc = {p["claim_id"]: p["doc_id"] for _, p in records}
        self._findings_index = LedgerIndex(records)

    # -- lectura -----------------------------------------------------------------

    def recall(self, query: str, *, k_own: int = 5, k_findings: int = 5, k_passages: int = 4,
               passage_chars: int = 1500) -> Recall:
        out = Recall(query=query)
        for r in LedgerIndex.from_store(self.store).query(query, k=k_own):
            out.own.append(MemoryHit("OWN", r.record_id, r.record_type, round(r.score, 6), r.text,
                                     authority_status="OWN_LEDGER_RECORD"))
        for r in self._findings_index.query(query, k=k_findings):
            doc_id = self._finding_doc[r.record_id]
            out.findings.append(MemoryHit("FINDING", r.record_id, "finding", round(r.score, 6), r.text,
                                          authority_status=FINDING_AUTHORITY, source_id=f"SRC-SSRN-{doc_id:04d}",
                                          title=self._titles.get(doc_id, "")))
        if k_passages > 0:
            try:
                hits = self.cortex.search_passages(query, limit=k_passages)
            except BibliographicCortexError:
                hits = []
            for i, h in enumerate(hits, start=1):
                out.passages.append(MemoryHit("PASSAGE", f"PASSAGE-SSRN-{h.doc_id:04d}-{i:02d}", "passage",
                                              float(h.score), h.passage[:passage_chars],
                                              authority_status=LITERATURE_AUTHORITY,
                                              source_id=f"SRC-SSRN-{h.doc_id:04d}", title=h.title))
        return out

    # -- escritura (deja rastro en el ledger del brain) ---------------------------

    def consult(self, *, consultation_id: str, episode_id: str, query: str, purpose: str, recorded_by: str,
                created_at_utc: str, **recall_kwargs) -> Consultation:
        rec = self.recall(query, **recall_kwargs)
        if not rec.literature:
            raise BibliographicCortexError(f"no literature matched {query!r}; nothing to record")
        row = {
            "consultation_id": consultation_id,
            "episode_id": episode_id,
            "query": query,
            "purpose": purpose,
            "recorded_by": recorded_by,
            "created_at_utc": created_at_utc,
            "corpus_id": self.cortex.corpus_id,
            "authority_status": LITERATURE_AUTHORITY,
            "claims_are_evidence": False,
            "own_record_ids": [h.record_id for h in rec.own],
            "items": [{"kind": h.origin, "record_id": h.record_id, "source_id": h.source_id, "title": h.title,
                       "score": h.score, "text_sha256": _sha(h.text)} for h in rec.literature],
        }
        row["recall_sha256"] = _sha(json.dumps(rec.to_dict(), ensure_ascii=False, sort_keys=True))
        digest = self.store.record_literature_consultation(row)
        return Consultation(consultation_id, rec, digest)

    def cite(self, artifact_id: str, consultation_id: str) -> None:
        """``artifact_id`` (hipotesis, diseno, leccion...) se apoyo en esa consulta: dependencia blanda."""
        if consultation_id not in self.store.literature:
            raise ValueError(f"unknown consultation {consultation_id!r}")
        self.store.record_dependency(artifact_id, consultation_id, "SUPPORTED_BY")

    def invalidate_source(self, source_id: str) -> dict[str, str]:
        """Un paper resulta invalido (retractado, error de datos, duplicado): propaga REQUIRES_REAUDIT."""
        return self.store.invalidate_with_cascade(source_id)
