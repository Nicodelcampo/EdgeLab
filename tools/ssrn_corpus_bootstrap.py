#!/usr/bin/env python3
"""Materialize the in-repo CerebroSSRN corpus (Edge Brain bibliographic hippocampus).

Git stores only text: papers, extractions, graph, historical ledger and pipeline.
This tool, 100% local and deterministic (no LLM, no network):
  1. reassembles files split into ``*.partNN`` (GitHub API size limit), checking sha256;
  2. rebuilds ``Normalizado/chunks.sqlite`` (chunks + passages) with the original
     CerebroSSRN pipeline logic;
  3. verifies row-level hashes of chunks/passages and the per-paper custody hashes
     against ``config/edge_brain/ssrn_corpus_repo_v1.json``;
  4. runs the Bibliographic Cortex audit (must be VERIFIED_COMPLETE).

Usage:  python tools/ssrn_corpus_bootstrap.py [--root corpus/ssrn] [--force]
Then:   EDGELAB_SSRN_CORPUS_ROOT=corpus/ssrn python tools/ssrn_brain_cli.py search corpus/ssrn "query"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
CONFIG = REPO / "config" / "edge_brain" / "ssrn_corpus_repo_v1.json"

PASSAGE_WORDS = 300
PASSAGE_OVERLAP = 60


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def make_passages(text: str) -> list[str]:
    """Verbatim copy of CerebroSSRN pipeline/embed_chunks.make_passages (no model needed)."""
    words = text.split()
    if len(words) <= PASSAGE_WORDS:
        return [text]
    step = PASSAGE_WORDS - PASSAGE_OVERLAP
    out = []
    for i in range(0, len(words), step):
        piece = words[i: i + PASSAGE_WORDS]
        if len(piece) < 40 and out:
            break
        out.append(" ".join(piece))
        if i + PASSAGE_WORDS >= len(words):
            break
    return out


def table_digest(db: Path, table: str, cols: str) -> tuple[int, str]:
    h = hashlib.sha256()
    n = 0
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
        for row in con.execute(f"SELECT {cols} FROM {table} ORDER BY id"):
            h.update(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            n += 1
    return n, h.hexdigest()


def reassemble(root: Path, parts: dict) -> None:
    for rel, spec in parts.items():
        target = root / rel
        if target.is_file() and sha256_file(target) == spec["sha256"]:
            continue
        data = b"".join((root / f"{rel}.part{i:02d}").read_bytes() for i in range(spec["parts"]))
        if hashlib.sha256(data).hexdigest() != spec["sha256"]:
            raise SystemExit(f"Reassembled hash mismatch: {rel}")
        target.write_bytes(data)
        print(f"reassembled {rel} ({len(data):,} bytes)")


def build_index(root: Path) -> Path:
    db = root / "Normalizado" / "chunks.sqlite"
    subprocess.run([sys.executable, str(root / "pipeline" / "chunk_docs.py")], check=True,
                   stdout=subprocess.DEVNULL)
    con = sqlite3.connect(db)
    con.execute("DROP TABLE IF EXISTS passages")
    con.execute("""CREATE TABLE passages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id INTEGER NOT NULL,
            doc_id INTEGER NOT NULL,
            passage_index INTEGER NOT NULL,
            texto TEXT NOT NULL
        )""")
    con.execute("CREATE INDEX idx_passages_chunk ON passages(chunk_id)")
    con.execute("CREATE INDEX idx_passages_doc ON passages(doc_id)")
    rows = con.execute("SELECT id, doc_id, texto FROM chunks ORDER BY id").fetchall()
    for chunk_id, doc_id, texto in rows:
        for i, passage in enumerate(make_passages(texto)):
            con.execute("INSERT INTO passages (chunk_id, doc_id, passage_index, texto) VALUES (?,?,?,?)",
                        (chunk_id, doc_id, i, passage))
    con.commit()
    con.close()
    return db


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(REPO / "corpus" / "ssrn"))
    ap.add_argument("--force", action="store_true", help="rebuild the index even if it exists")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    reassemble(root, cfg["split_files"])
    db = root / "Normalizado" / "chunks.sqlite"
    if args.force or not db.is_file():
        build_index(root)
        print(f"built {db.relative_to(REPO) if db.is_relative_to(REPO) else db}")

    errors = []
    for table, cols in (("chunks", "id, doc_id, doc_titulo, archivo_fuente, chunk_index, n_chunks_doc, texto, n_palabras"),
                        ("passages", "id, chunk_id, doc_id, passage_index, texto")):
        n, digest = table_digest(db, table, cols)
        exp = cfg["index_digests"][table]
        if (n, digest) != (exp["rows"], exp["sha256"]):
            errors.append(f"{table}: got {n}/{digest[:12]} expected {exp['rows']}/{exp['sha256'][:12]}")
    for item in cfg["papers"]:
        p = root / "Normalizado" / "documentos" / item["normalized_file"]
        if not p.is_file() or sha256_file(p) != item["normalized_sha256"]:
            errors.append(f"paper hash mismatch: {item['normalized_file']}")
        e = root / "extraccion" / "completo" / f"{item['doc_id']:04d}.json"
        if not e.is_file() or sha256_file(e) != item["extraction_sha256"]:
            errors.append(f"extraction hash mismatch: {e.name}")

    from edgelab.edge_brain.bibliographic_cortex import SSRNBibliographicCortex
    audit = SSRNBibliographicCortex(root).audit(cfg["expected"])
    if audit.status != "VERIFIED_COMPLETE":
        errors.append(f"cortex audit: {audit.status}")
    if errors:
        print("FAIL\n  " + "\n  ".join(errors[:20]))
        return 1
    fts = SSRNBibliographicCortex(root)
    if args.force or fts.fts_status() != "READY":
        info = fts.build_fts_index()
        print(f"built search index: {info['passages_indexed']} passages | {info['findings_indexed']} findings | "
              f"{info['papers_indexed']} paper cards")
    print(f"OK  {audit.usable_papers} papers | {audit.chunks} chunks | {audit.passages} passages | "
          f"{audit.findings} findings | graph {audit.graph_nodes}/{audit.graph_edges} | {audit.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
