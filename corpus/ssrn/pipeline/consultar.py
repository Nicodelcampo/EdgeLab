#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
El "cuerpo calloso" del CerebroSSRN: dado una consulta, recupera
  1. HIPOCAMPO (memoria episodica): pasajes crudos de los papers mas
     relevantes (busqueda semantica local, e5-small multilingue)
  2. CORTEZA (memoria semantica): nodos del grafo cuyo nombre matchea
  3. BARRO EMPIRICO: hallazgos (backtests/resultados) cuyo texto matchea

Cross-lingual a proposito: el corpus esta en ingles, las consultas del
usuario llegan en castellano. e5 multilingue resuelve el matching sin
traducir nada.

Uso:
    python consultar.py "order flow imbalance en futuros" [-k 6]
    python consultar.py --interactivo
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "Normalizado", "chunks.sqlite")
EMB = os.path.join(BASE, "Normalizado", "embeddings.npy")
IDS = os.path.join(BASE, "Normalizado", "embeddings_ids.npy")
GRAFO = os.path.join(BASE, "grafo", "grafo_final.json")
HALLAZGOS = os.path.join(BASE, "grafo", "hallazgos.json")

ARTICLES_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)


def sa(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def nk(name):
    n = sa(str(name)).lower().strip()
    n = ARTICLES_RE.sub("", n)
    n = re.sub(r"[^\w\s-]", " ", n)
    n = re.sub(r"[\s_-]+", " ", n).strip()
    return " ".join(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
                    for w in n.split())


_MODEL = None
_EMB = None
_IDS = None


def _ensure_loaded():
    global _MODEL, _EMB, _IDS
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        print("[cargando modelo de embeddings local...]", file=sys.stderr)
        _MODEL = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu")
        _EMB = np.load(EMB)
        _IDS = np.load(IDS)
    return _MODEL, _EMB, _IDS


def retrieve_passages(query, k):
    model, emb, ids = _ensure_loaded()
    qv = model.encode(["query: " + query], normalize_embeddings=True, convert_to_numpy=True)[0]
    sims = emb @ qv
    top = np.argsort(-sims)[: k * 3]

    conn = sqlite3.connect(DB)
    results, seen_chunks = [], set()
    for i in top:
        pid = int(ids[i])
        row = conn.execute(
            "SELECT p.texto, p.chunk_id, c.doc_titulo, c.doc_id FROM passages p "
            "JOIN chunks c ON c.id = p.chunk_id WHERE p.id = ?", (pid,)
        ).fetchone()
        if row is None:
            continue
        texto, chunk_id, doc_titulo, doc_id = row
        if chunk_id in seen_chunks:
            continue
        seen_chunks.add(chunk_id)
        results.append({"score": float(sims[i]), "texto": texto,
                        "doc_titulo": doc_titulo, "doc_id": doc_id})
        if len(results) >= k:
            break
    conn.close()
    return results


def retrieve_nodes(query):
    d = json.load(open(GRAFO, encoding="utf-8"))
    qk = nk(query)
    qwords = set(qk.split())
    hits = []
    for n in d["nodos"]:
        names = [n["nombre_canonico"]] + n.get("nombres_vistos", [])
        for name in names:
            key = nk(name)
            if not key or len(key) < 4:
                continue
            if key in qk or (len(key.split()) >= 2 and len(set(key.split()) & qwords) >= 2):
                hits.append(n)
                break
    seen, uniq = set(), []
    for n in sorted(hits, key=lambda x: -x.get("doc_frecuencia", 0)):
        if n["id"] not in seen:
            seen.add(n["id"])
            uniq.append(n)
    return uniq[:8]


def retrieve_hallazgos(query, max_n=6):
    if not os.path.exists(HALLAZGOS):
        return []
    hallazgos = json.load(open(HALLAZGOS, encoding="utf-8"))
    qk = nk(query)
    qwords = set(qk.split())
    scored = []
    for h in hallazgos:
        text = nk(f"{h.get('afirmacion','')} {h.get('mercado','')}")
        overlap = len(set(text.split()) & qwords)
        if overlap > 0:
            scored.append((overlap, h))
    scored.sort(key=lambda x: -x[0])
    return [h for _, h in scored[:max_n]]


def run_query(query, k):
    out = []
    out.append("=" * 70)
    out.append(f"MEMORIA RECUPERADA PARA: {query!r}")
    out.append("=" * 70)

    nodes = retrieve_nodes(query)
    if nodes:
        out.append("\n--- CORTEZA (nodos del grafo que matchean la consulta) ---")
        for n in nodes:
            defin = n["definiciones"][0]["texto"] if n.get("definiciones") else ""
            out.append(f"\n* {n['nombre_canonico']} [{n.get('tipo','')}] (docs={n['doc_frecuencia']})")
            if defin:
                out.append(f"  {defin[:300]}")
            rels = n.get("relaciones_crudas", [])[:5]
            if rels:
                out.append("  Rel: " + "; ".join(f"{r['tipo']}->{r['objeto_texto']}" for r in rels))

    hallazgos = retrieve_hallazgos(query)
    if hallazgos:
        out.append("\n--- BARRO EMPÍRICO (hallazgos de backtests que matchean) ---")
        for h in hallazgos:
            out.append(f"\n[{h.get('robustez','?')}] doc {h['doc_id']} ({h.get('mercado','')}, {h.get('periodo','')})")
            out.append(f"  {h.get('afirmacion','')} — {h.get('magnitud','')}")
            out.append(f"  Condiciones: {h.get('condiciones','')}")

    passages = retrieve_passages(query, k)
    out.append("\n--- HIPOCAMPO (pasajes crudos de los papers, por relevancia) ---")
    for p in passages:
        out.append(f"\n[{p['score']:.3f}] {p['doc_titulo']} (doc {p['doc_id']})")
        out.append(f"  \"{p['texto'][:600]}\"")

    out.append("\n" + "=" * 70)
    out.append("Instruccion para el Cerebro: usa estos pasajes como evidencia")
    out.append("citable (con su doc_id). El grafo da la estructura; los")
    out.append("hallazgos dan la evidencia empirica; los pasajes dan el texto")
    out.append("fuente exacto para citar.")

    text = "\n".join(out)
    print(text)

    os.makedirs(os.path.join(BASE, "cerebro"), exist_ok=True)
    with open(os.path.join(BASE, "cerebro", "ultima_recuperacion.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default=None)
    ap.add_argument("-k", type=int, default=6)
    ap.add_argument("--interactivo", action="store_true")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")

    if args.interactivo:
        _ensure_loaded()
        print("[modo interactivo: una consulta por linea; vacio o 'salir' termina]", file=sys.stderr)
        for line in sys.stdin:
            q = line.strip()
            if not q or q.lower() in ("salir", "exit", "quit"):
                break
            run_query(q, args.k)
            print("\n[lista para la proxima consulta]", file=sys.stderr)
        return

    if not args.query:
        ap.error("falta la consulta (o usa --interactivo)")
    run_query(args.query, args.k)


if __name__ == "__main__":
    main()
