#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 1b del CerebroSSRN: embeddings locales (CPU, $0, sin API).

Clon de embed_chunks.py del CerebroJLP. Mismo modelo
(intfloat/multilingual-e5-small) A PROPOSITO: el corpus es ingles pero las
consultas del usuario llegan en castellano — e5 multilingue resuelve la
recuperacion cross-lingual (query es-AR -> passage en-US) sin traducir nada.

Los chunks grandes (~1800 palabras) se re-parten en pasajes de ~300 palabras
solo para el indice semantico (e5 trunca a ~512 tokens); cada pasaje guarda
su chunk_id de origen para recuperar el contexto completo.
"""
import os
import sqlite3
import time

import numpy as np
from sentence_transformers import SentenceTransformer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NORM_DIR = os.path.join(BASE, "Normalizado")
DB_PATH = os.path.join(NORM_DIR, "chunks.sqlite")
EMB_PATH = os.path.join(NORM_DIR, "embeddings.npy")
IDS_PATH = os.path.join(NORM_DIR, "embeddings_ids.npy")

MODEL_NAME = "intfloat/multilingual-e5-small"
BATCH_SIZE = 64
PASSAGE_WORDS = 300
PASSAGE_OVERLAP = 60


def make_passages(text):
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


def ensure_passages_table(conn):
    conn.execute("DROP TABLE IF EXISTS passages")
    conn.execute(
        """
        CREATE TABLE passages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id INTEGER NOT NULL,
            doc_id INTEGER NOT NULL,
            passage_index INTEGER NOT NULL,
            texto TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX idx_passages_chunk ON passages(chunk_id)")
    conn.execute("CREATE INDEX idx_passages_doc ON passages(doc_id)")


def main():
    conn = sqlite3.connect(DB_PATH)
    chunk_rows = conn.execute("SELECT id, doc_id, texto FROM chunks ORDER BY id").fetchall()
    print(f"Chunks fuente: {len(chunk_rows)}")

    ensure_passages_table(conn)
    for chunk_id, doc_id, texto in chunk_rows:
        for i, passage in enumerate(make_passages(texto)):
            conn.execute(
                "INSERT INTO passages (chunk_id, doc_id, passage_index, texto) VALUES (?,?,?,?)",
                (chunk_id, doc_id, i, passage),
            )
    conn.commit()

    rows = conn.execute("SELECT id, texto FROM passages ORDER BY id").fetchall()
    conn.close()
    print(f"Pasajes generados para embeddings: {len(rows)}")

    ids = np.array([r[0] for r in rows], dtype=np.int64)
    texts = ["passage: " + r[1] for r in rows]

    print(f"Cargando modelo {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    t0 = time.time()
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    dt = time.time() - t0
    print(f"Listo en {dt/60:.1f} min. Shape: {embeddings.shape}")

    np.save(EMB_PATH, embeddings.astype(np.float32))
    np.save(IDS_PATH, ids)
    print(f"Embeddings: {EMB_PATH}")
    print(f"IDs alineados: {IDS_PATH}")


if __name__ == "__main__":
    main()
