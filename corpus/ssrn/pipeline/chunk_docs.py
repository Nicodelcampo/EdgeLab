#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 1a del CerebroSSRN: parte los papers normalizados en chunks (~1800
palabras) para embeddings y consulta. Clon de chunk_docs.py del CerebroJLP
con dos adaptaciones al dominio academico:

  1. Split de oraciones para ingles academico (mayusculas, digitos,
     parentesis de ecuaciones).
  2. La BIBLIOGRAFIA se recorta para el indice semantico: si aparece una
     linea "References"/"Bibliography" en el ultimo 40% del documento, los
     chunks se generan solo hasta ahi (las referencias contaminan la
     recuperacion). El .txt fuente conserva el paper completo.

100% local, no llama a ningun LLM.
"""
import json
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NORM_DIR = os.path.join(BASE, "Normalizado")
DOCS_DIR = os.path.join(NORM_DIR, "documentos")
MANIFEST = os.path.join(NORM_DIR, "manifest.json")
DB_PATH = os.path.join(NORM_DIR, "chunks.sqlite")

TARGET_WORDS = 1800
OVERLAP_WORDS = 150
MIN_CHUNK_WORDS = 200
HARD_SPLIT_WORDS = 300

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])")
REFS_RE = re.compile(r"^\s*(references|bibliography|works cited)\s*$", re.IGNORECASE)


def strip_bibliography(text):
    """Corta en la linea 'References' si esta en el ultimo 40% del doc."""
    lines = text.split("\n")
    cut_at = None
    threshold = int(len(lines) * 0.60)
    for i in range(len(lines) - 1, threshold, -1):
        if REFS_RE.match(lines[i]):
            cut_at = i
            break
    if cut_at is None:
        return text, False
    return "\n".join(lines[:cut_at]), True


def hard_split(text, size=HARD_SPLIT_WORDS):
    words = text.split()
    return [" ".join(words[i: i + size]) for i in range(0, len(words), size)]


def split_units(text):
    blocks = [p for p in text.split("\n\n") if p.strip()]
    units = []
    for block in blocks:
        block = re.sub(r"\s+", " ", block).strip()
        for s in SENTENCE_SPLIT_RE.split(block):
            s = s.strip()
            if not s:
                continue
            if len(s.split()) > HARD_SPLIT_WORDS * 2:
                units.extend(hard_split(s))
            else:
                units.append(s)
    return units


def make_chunks_for_doc(units):
    chunks = []
    current = []
    current_words = 0
    for unit in units:
        unit_words = len(unit.split())
        if current_words + unit_words > TARGET_WORDS and current:
            chunks.append(current)
            overlap = []
            ow = 0
            for u in reversed(current):
                overlap.insert(0, u)
                ow += len(u.split())
                if ow >= OVERLAP_WORDS:
                    break
            current = list(overlap)
            current_words = ow
        current.append(unit)
        current_words += unit_words
    if current:
        if chunks and current_words < MIN_CHUNK_WORDS:
            chunks[-1].extend(current)
        else:
            chunks.append(current)
    return [" ".join(c) for c in chunks]


def main():
    manifest = json.load(open(MANIFEST, encoding="utf-8"))

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL,
            doc_titulo TEXT NOT NULL,
            archivo_fuente TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            n_chunks_doc INTEGER NOT NULL,
            texto TEXT NOT NULL,
            n_palabras INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX idx_chunks_doc ON chunks(doc_id)")

    total_chunks = 0
    docs_con_refs = 0
    for entry in manifest:
        if not entry.get("id") or not entry.get("archivo_normalizado"):
            continue
        path = os.path.join(DOCS_DIR, entry["archivo_normalizado"])
        with open(path, encoding="utf-8") as f:
            text = f.read()
        text, refs_cut = strip_bibliography(text)
        docs_con_refs += refs_cut
        units = split_units(text)
        chunk_texts = make_chunks_for_doc(units)
        for i, ctext in enumerate(chunk_texts):
            conn.execute(
                "INSERT INTO chunks (doc_id, doc_titulo, archivo_fuente, "
                "chunk_index, n_chunks_doc, texto, n_palabras) VALUES (?,?,?,?,?,?,?)",
                (entry["id"], entry["titulo"], entry["archivo_pdf"],
                 i, len(chunk_texts), ctext, len(ctext.split())),
            )
            total_chunks += 1

    conn.commit()
    row = conn.execute(
        "SELECT COUNT(*), AVG(n_palabras), MIN(n_palabras), MAX(n_palabras) FROM chunks"
    ).fetchone()
    conn.close()

    print(f"Docs con bibliografia recortada del indice: {docs_con_refs}")
    print(f"Total chunks: {row[0]}")
    print(f"Palabras por chunk -> promedio: {row[1]:.0f}  min: {row[2]}  max: {row[3]}")
    print(f"DB: {DB_PATH}")


if __name__ == "__main__":
    main()
