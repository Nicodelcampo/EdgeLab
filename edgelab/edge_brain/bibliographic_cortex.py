from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .registry import verify_registry
from .typed_registry import append_typed_record


class BibliographicCortexError(ValueError):
    """The corpus is incomplete, inconsistent, or unsafe to ingest."""


@dataclass(frozen=True)
class PassageHit:
    doc_id: int
    title: str
    source_file: str
    passage: str
    score: int


@dataclass(frozen=True)
class CorpusAudit:
    corpus_id: str
    manifest_rows: int
    usable_papers: int
    normalized_documents: int
    complete_extractions: int
    chunks: int
    passages: int
    findings: int
    graph_nodes: int
    graph_edges: int
    unresolved_graph_relations: int
    missing_document_ids: tuple[int, ...]
    missing_extraction_ids: tuple[int, ...]
    duplicate_version_groups: tuple[tuple[int, ...], ...]
    status: str


class SSRNBibliographicCortex:
    """Deterministic adapter for the complete CerebroSSRN corpus.

    Raw texts stay in a hash-addressed external artifact. The Brain stores
    verified source identities, unverified claims, provenance, and bounded
    context. Literature and the old experiment ledger never promote themselves.
    """

    REQUIRED = (
        "Normalizado/manifest.json",
        "Normalizado/chunks.sqlite",
        "extraccion/docs_list.json",
        "extraccion/completo",
        "grafo/docs_meta.json",
        "grafo/hallazgos.json",
        "grafo/grafo_final.json",
        "cerebro/LEDGER_EXPERIMENTOS.md",
    )

    def __init__(self, root: str | Path, corpus_id: str = "CORPUS-SSRN-001") -> None:
        self.root = Path(root).expanduser().resolve()
        self.corpus_id = corpus_id
        missing = [rel for rel in self.REQUIRED if not (self.root / rel).exists()]
        if missing:
            raise BibliographicCortexError(f"Incomplete CerebroSSRN root; missing: {missing}")
        self.manifest = self._json("Normalizado/manifest.json")
        self.docs_list = self._json("extraccion/docs_list.json")
        self.docs_meta = self._json("grafo/docs_meta.json")
        self.findings = self._json("grafo/hallazgos.json")
        self.graph = self._json("grafo/grafo_final.json")
        if not isinstance(self.manifest, list) or not isinstance(self.docs_list, list):
            raise BibliographicCortexError("Manifest and docs_list must be arrays")
        self._manifest_by_id = {
            int(row["id"]): row
            for row in self.manifest
            if isinstance(row, dict) and row.get("id") is not None
        }
        self._doc_by_id = {int(row["id"]): row for row in self.docs_list}

    def _json(self, rel: str) -> Any:
        return json.loads((self.root / rel).read_text(encoding="utf-8-sig"))

    @staticmethod
    def sha256_file(path: str | Path) -> str:
        h = hashlib.sha256()
        with Path(path).open("rb") as fh:
            for block in iter(lambda: fh.read(8 << 20), b""):
                h.update(block)
        return h.hexdigest()

    @staticmethod
    def _text(value: Any) -> str:
        return " ".join(str(value or "").split())

    def _document_path_unchecked(self, doc_id: int) -> Path:
        row = self._doc_by_id[int(doc_id)]
        return self.root / "Normalizado" / "documentos" / row["file"]

    def document_path(self, doc_id: int) -> Path:
        if int(doc_id) not in self._doc_by_id:
            raise KeyError(f"Unknown SSRN doc_id: {doc_id}")
        path = self._document_path_unchecked(int(doc_id))
        if not path.is_file():
            raise BibliographicCortexError(f"Missing normalized document: {path}")
        return path

    def extraction_path(self, doc_id: int, require: bool = True) -> Path:
        path = self.root / "extraccion" / "completo" / f"{int(doc_id):04d}.json"
        if require and not path.is_file():
            raise BibliographicCortexError(f"Missing complete extraction: {path}")
        return path

    def paper(self, doc_id: int) -> dict[str, Any]:
        doc_id = int(doc_id)
        path = self.document_path(doc_id)
        return {
            "doc_id": doc_id,
            "source_id": f"SRC-SSRN-{doc_id:04d}",
            "manifest": self._manifest_by_id.get(doc_id, {}),
            "metadata": self.docs_meta.get(str(doc_id), {}),
            "extraction": json.loads(self.extraction_path(doc_id).read_text(encoding="utf-8-sig")),
            "normalized_text_path": str(path),
            "normalized_text_sha256": self.sha256_file(path),
        }

    def _version_groups(self) -> tuple[tuple[int, ...], ...]:
        buckets: dict[str, list[int]] = {}
        for doc_id, row in self._manifest_by_id.items():
            ssrn_id = self._text(row.get("ssrn_id"))
            title = re.sub(r"\W+", " ", self._text(row.get("titulo")).lower()).strip()
            key = f"ssrn:{ssrn_id}" if ssrn_id else f"title:{title}"
            buckets.setdefault(key, []).append(doc_id)
        return tuple(tuple(sorted(ids)) for ids in buckets.values() if len(ids) > 1)

    def audit(self, expected: dict[str, int] | None = None) -> CorpusAudit:
        ids = sorted(self._doc_by_id)
        normalized_ids = {i for i in ids if self._document_path_unchecked(i).is_file()}
        extraction_ids = {i for i in ids if self.extraction_path(i, require=False).is_file()}
        db_uri = f"file:{self.root / 'Normalizado/chunks.sqlite'}?mode=ro"
        with sqlite3.connect(db_uri, uri=True) as con:
            chunks = int(con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
            passages = int(con.execute("SELECT COUNT(*) FROM passages").fetchone()[0])
        nodes = self.graph.get("nodos", []) if isinstance(self.graph, dict) else []
        edges = self.graph.get("aristas", []) if isinstance(self.graph, dict) else []
        unresolved_path = self.root / "grafo" / "relaciones_sin_destino.json"
        unresolved = 0
        if unresolved_path.is_file():
            value = json.loads(unresolved_path.read_text(encoding="utf-8-sig"))
            unresolved = len(value) if hasattr(value, "__len__") else 0
        observed = {
            "usable_papers": len(ids),
            "normalized_documents": len(normalized_ids),
            "complete_extractions": len(extraction_ids),
            "chunks": chunks,
            "passages": passages,
            "findings": len(self.findings),
            "graph_nodes": len(nodes),
            "graph_edges": len(edges),
        }
        mismatches = {k: (observed.get(k), v) for k, v in (expected or {}).items() if observed.get(k) != v}
        missing_docs = tuple(sorted(set(ids) - normalized_ids))
        missing_ext = tuple(sorted(set(ids) - extraction_ids))
        status = "VERIFIED_COMPLETE" if not mismatches and not missing_docs and not missing_ext else "INCOMPLETE"
        return CorpusAudit(
            corpus_id=self.corpus_id,
            manifest_rows=len(self.manifest),
            usable_papers=len(ids),
            normalized_documents=len(normalized_ids),
            complete_extractions=len(extraction_ids),
            chunks=chunks,
            passages=passages,
            findings=len(self.findings),
            graph_nodes=len(nodes),
            graph_edges=len(edges),
            unresolved_graph_relations=unresolved,
            missing_document_ids=missing_docs,
            missing_extraction_ids=missing_ext,
            duplicate_version_groups=self._version_groups(),
            status=status,
        )

    def search_passages(self, query: str, limit: int = 6) -> list[PassageHit]:
        terms = [x.lower() for x in re.findall(r"[\w-]{3,}", query, flags=re.UNICODE)]
        if not terms:
            raise BibliographicCortexError("Query needs at least one term with 3+ characters")
        where = " OR ".join("lower(p.texto) LIKE ?" for _ in terms)
        params = [f"%{term}%" for term in terms]
        sql = f"""SELECT p.doc_id, c.doc_titulo, c.archivo_fuente, p.texto
                  FROM passages p JOIN chunks c ON c.id = p.chunk_id
                  WHERE {where} LIMIT 1000"""
        db_uri = f"file:{self.root / 'Normalizado/chunks.sqlite'}?mode=ro"
        with sqlite3.connect(db_uri, uri=True) as con:
            rows = con.execute(sql, params).fetchall()
        hits = []
        for doc_id, title, source_file, passage in rows:
            low = str(passage).lower()
            score = sum(low.count(term) for term in terms)
            hits.append(PassageHit(int(doc_id), str(title), str(source_file), str(passage), score))
        hits.sort(key=lambda item: (-item.score, item.doc_id, item.source_file))
        return hits[: max(1, int(limit))]

    def custody_manifest(self, archive_sha256: str, created_at_utc: str) -> dict[str, Any]:
        papers = []
        aggregate = hashlib.sha256()
        for doc_id in sorted(self._doc_by_id):
            text_path = self.document_path(doc_id)
            extraction_path = self.extraction_path(doc_id)
            row = self._manifest_by_id.get(doc_id, {})
            item = {
                "doc_id": doc_id,
                "source_id": f"SRC-SSRN-{doc_id:04d}",
                "ssrn_id": self._text(row.get("ssrn_id")) or None,
                "title": self._text(row.get("titulo")) or self._text(self.docs_meta.get(str(doc_id), {}).get("titulo")),
                "url": self._text(row.get("url")) or None,
                "normalized_file": self._doc_by_id[doc_id]["file"],
                "normalized_bytes": text_path.stat().st_size,
                "normalized_sha256": self.sha256_file(text_path),
                "extraction_sha256": self.sha256_file(extraction_path),
                "authority_status": "LITERATURE_CLAIM_UNVERIFIED",
            }
            aggregate.update(json.dumps(item, sort_keys=True, separators=(",", ":")).encode())
            papers.append(item)
        audit = asdict(self.audit())
        audit["missing_document_ids"] = list(audit["missing_document_ids"])
        audit["missing_extraction_ids"] = list(audit["missing_extraction_ids"])
        audit["duplicate_version_groups"] = [list(x) for x in audit["duplicate_version_groups"]]
        return {
            "schema": "edgelab_ssrn_corpus_custody_v1",
            "corpus_id": self.corpus_id,
            "archive_sha256": archive_sha256,
            "created_at_utc": created_at_utc,
            "audit": audit,
            "papers": papers,
            "papers_aggregate_sha256": aggregate.hexdigest(),
            "claims_are_evidence": False,
        }

    def ingest_ledger(
        self,
        ledger_path: str | Path,
        *,
        created_at_utc: str,
        include_findings: bool = True,
        include_historical_experiments: bool = True,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        target = Path(ledger_path)
        if target.exists() and not overwrite:
            raise BibliographicCortexError(f"Ledger already exists: {target}")
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.unlink(missing_ok=True)
        counts = {"sources": 0, "claims": 0, "edges": 0, "historical_experiments": 0}
        for doc_id in sorted(self._doc_by_id):
            row = self._manifest_by_id.get(doc_id, {})
            path = self.document_path(doc_id)
            source_id = f"SRC-SSRN-{doc_id:04d}"
            append_typed_record(tmp, record_type="source_artifact", record_id=source_id, payload={
                "source_id": source_id,
                "source_type": "PAPER",
                "title_or_uri": self._text(row.get("url")) or self._text(row.get("titulo")) or path.name,
                "sha256": self.sha256_file(path),
                "is_primary_source": True,
                "status": "VERIFIED",
                "created_at_utc": created_at_utc,
            }, recorded_at_utc=created_at_utc)
            counts["sources"] += 1
        if include_findings:
            for index, finding in enumerate(self.findings, start=1):
                try:
                    doc_id = int(finding.get("doc_id"))
                except (TypeError, ValueError):
                    continue
                if doc_id not in self._doc_by_id:
                    continue
                claim_id = f"CLAIM-SSRN-FINDING-{index:04d}"
                source_id = f"SRC-SSRN-{doc_id:04d}"
                scope = json.dumps({k: finding.get(k) for k in ("mercado", "periodo", "magnitud", "condiciones", "robustez")}, ensure_ascii=False, sort_keys=True)
                append_typed_record(tmp, record_type="claim", record_id=claim_id, payload={
                    "claim_id": claim_id,
                    "statement": self._text(finding.get("afirmacion")) or "Author-reported finding",
                    "claim_type": "LITERATURE",
                    "status": "AUTHOR_REPORTED_RESULT",
                    "scope": scope,
                    "dependency_ids": [],
                    "evidence_ids": [],
                    "source_ids": [source_id],
                }, recorded_at_utc=created_at_utc)
                edge_id = f"EDGE-SSRN-FINDING-{index:04d}"
                append_typed_record(tmp, record_type="dependency_edge", record_id=edge_id, payload={
                    "edge_id": edge_id,
                    "source_id": claim_id,
                    "target_id": source_id,
                    "relation": "SUPPORTED_BY",
                    "source_record_id": claim_id,
                    "status": "PROPOSED",
                }, recorded_at_utc=created_at_utc)
                counts["claims"] += 1
                counts["edges"] += 1
        if include_historical_experiments:
            ledger_source = "SRC-SSRN-HISTORICAL-LEDGER"
            ledger_doc = self.root / "cerebro" / "LEDGER_EXPERIMENTOS.md"
            append_typed_record(tmp, record_type="source_artifact", record_id=ledger_source, payload={
                "source_id": ledger_source,
                "source_type": "MANUAL",
                "title_or_uri": "CerebroSSRN historical experiment ledger",
                "sha256": self.sha256_file(ledger_doc),
                "is_primary_source": False,
                "status": "VERIFIED",
                "created_at_utc": created_at_utc,
            }, recorded_at_utc=created_at_utc)
            counts["sources"] += 1
            headings = re.findall(r"^##\s+(EXP-[^\n]+)$", ledger_doc.read_text(encoding="utf-8-sig"), flags=re.MULTILINE)
            for index, heading in enumerate(headings, start=1):
                claim_id = f"CLAIM-SSRN-HISTEXP-{index:03d}"
                append_typed_record(tmp, record_type="claim", record_id=claim_id, payload={
                    "claim_id": claim_id,
                    "statement": self._text(heading),
                    "claim_type": "METHODOLOGICAL",
                    "status": "HISTORICAL_EXPERIMENT_PENDING_REAUDIT",
                    "scope": "Imported from CerebroSSRN; not promoted or reproduced in EdgeLab",
                    "dependency_ids": [],
                    "evidence_ids": [],
                    "source_ids": [ledger_source],
                }, recorded_at_utc=created_at_utc)
                counts["claims"] += 1
                counts["historical_experiments"] += 1
        verification = verify_registry(tmp)
        if not verification.get("valid"):
            raise BibliographicCortexError(f"Generated ledger failed verification: {verification}")
        tmp.replace(target)
        return {**counts, "records": verification["records"], "head_hash": verification["head_hash"], "ledger_sha256": self.sha256_file(target)}

    def context_pack(self, query: str, limit: int = 6, max_chars: int = 12000) -> dict[str, Any]:
        items = []
        used = 0
        for hit in self.search_passages(query, limit=limit):
            remaining = max_chars - used
            if remaining <= 0:
                break
            passage = hit.passage[:remaining]
            used += len(passage)
            items.append({
                "record_id": f"PASSAGE-SSRN-{hit.doc_id:04d}-{len(items)+1:02d}",
                "source_id": f"SRC-SSRN-{hit.doc_id:04d}",
                "doc_id": hit.doc_id,
                "title": hit.title,
                "source_file": hit.source_file,
                "passage": passage,
                "score": hit.score,
                "authority_status": "LITERATURE_CLAIM_UNVERIFIED",
                "reason_for_inclusion": f"Matched target-free query terms: {query}",
            })
        canonical = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return {"query": query, "items": items, "char_budget": max_chars, "used_chars": used, "context_sha256": hashlib.sha256(canonical).hexdigest(), "claims_are_evidence": False}
