#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 3a del CerebroSSRN: consolida las extracciones de extraccion/completo/
en nodos candidatos. Clon de consolidate_concepts.py del CerebroJLP con
adaptaciones al corpus en ingles:

  - norm_key: articulos ingleses (the/a/an) + de-pluralizacion suave
    (word-final 's' salvo 'ss') para agrupar "limit order books" con
    "limit order book" sin fusionar "process"/"proces".
  - Tipos de relacion del schema quant (12 cerrados).
  - Ademas de conceptos, agrega los HALLAZGOS empiricos de todos los docs
    en grafo/hallazgos.json (el "barro empirico" del cerebro, analogo de
    los casos_aplicados del JLP).

100% local, $0, idempotente (re-correr regenera todo desde extraccion/).
"""
import glob
import json
import os
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPLETO_DIR = os.path.join(BASE, "extraccion", "completo")
OUT_DIR = os.path.join(BASE, "grafo")

FUZZY_THRESHOLD = 0.88

KNOWN_RELATION_TYPES = {
    "EQUIVALE_A", "PARTE_DE", "USA", "MIDE", "PREDICE", "CAUSA",
    "SE_OPONE_A", "MEJORA_A", "CONTRADICE_A", "MITIGA", "APLICA_A", "REQUIERE",
}
RELATION_SAFE_MAP = {
    "OPUESTO_A": "SE_OPONE_A",
    "MEJORA": "MEJORA_A",
    "CONTRADICE": "CONTRADICE_A",
    "EQUIVALENTE_A": "EQUIVALE_A",
    "COMPONENTE_DE": "PARTE_DE",
    "USADO_POR": None,  # direccion invertida: no mapear a ciegas
}

TIPOS_NODO = {"concepto", "estrategia", "metodo", "metrica", "fenomeno",
              "riesgo_metodologico", "dato"}

ARTICLES_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def depluralize(word):
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def norm_key(name):
    n = strip_accents(str(name)).lower().strip()
    n = ARTICLES_RE.sub("", n)
    n = re.sub(r"[^\w\s-]", " ", n)
    n = re.sub(r"[\s_-]+", " ", n).strip()
    return " ".join(depluralize(w) for w in n.split())


def normalize_relation_type(tipo):
    tipo = (tipo or "").strip().upper()
    if tipo in KNOWN_RELATION_TYPES:
        return tipo, False
    mapped = RELATION_SAFE_MAP.get(tipo, "__NONE__")
    if mapped is None or mapped == "__NONE__":
        return tipo, True
    return mapped, False


def load_all():
    items, hallazgos, docs_meta = [], [], {}
    bad_files = []
    for fp in sorted(glob.glob(os.path.join(COMPLETO_DIR, "*.json"))):
        try:
            data = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            bad_files.append((os.path.basename(fp), str(e)[:120]))
            continue
        doc_id = data.get("doc_id")
        titulo = data.get("titulo", "")
        docs_meta[doc_id] = {
            "titulo": titulo,
            "resumen_operativo": data.get("resumen_operativo", ""),
            "calidad_paper": data.get("calidad_paper", ""),
            "aplicabilidad_es_intradia": data.get("aplicabilidad_es_intradia", {}),
        }
        for c in data.get("conceptos", []):
            if not c.get("nombre"):
                continue
            rels = []
            for r in c.get("relaciones", []) or []:
                tipo_norm, review = normalize_relation_type(r.get("tipo", ""))
                rels.append({"tipo": tipo_norm, "tipo_original": r.get("tipo", ""),
                             "objeto": str(r.get("objeto", "")), "revisar": review})
            items.append({
                "nombre": str(c["nombre"]).strip(),
                "tipo": c.get("tipo", "concepto"),
                "definicion": c.get("definicion_en_contexto", ""),
                "relaciones": rels,
                "cita": (c.get("cita_textual") or "").strip(),
                "doc_id": doc_id, "doc_titulo": titulo,
            })
        for h in data.get("hallazgos", []) or []:
            h2 = dict(h)
            h2["doc_id"] = doc_id
            h2["doc_titulo"] = titulo
            hallazgos.append(h2)
    return items, hallazgos, docs_meta, bad_files


def cluster_concepts(items):
    by_key = defaultdict(list)
    for it in items:
        by_key[norm_key(it["nombre"])].append(it)

    keys = [k for k in by_key if k]
    parent = {k: k for k in keys}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    def word_jaccard(a, b):
        wa, wb = set(a.split()), set(b.split())
        return len(wa & wb) / len(wa | wb) if wa and wb else 0.0

    ambiguous = []
    keys_sorted = sorted(keys, key=len)
    for i, k1 in enumerate(keys_sorted):
        for k2 in keys_sorted[i + 1:]:
            if abs(len(k1) - len(k2)) > max(4, len(k1) * 0.3):
                continue
            if SequenceMatcher(None, k1, k2).ratio() < FUZZY_THRESHOLD:
                continue
            if len(k1.split()) > 1 or len(k2.split()) > 1:
                if word_jaccard(k1, k2) < 0.75:
                    continue
                d1 = set(k1.split()) - set(k2.split())
                d2 = set(k2.split()) - set(k1.split())
                if len(d1) == 1 and len(d2) == 1:
                    wa, wb = next(iter(d1)), next(iter(d2))
                    if SequenceMatcher(None, wa, wb).ratio() < 0.6:
                        # palabra distinta y no-parecida: puede ser dominio
                        # real (mean reversion vs mean aversion) -> juez LLM
                        ambiguous.append((k1, k2))
                        continue
            union(k1, k2)

    clusters = defaultdict(list)
    for k in keys:
        clusters[find(k)].extend(by_key[k])
    return clusters, ambiguous


def pick_canonical(members):
    counts = defaultdict(int)
    for m in members:
        counts[m["nombre"].lower()] += 1
    best = sorted(counts.items(), key=lambda kv: (-kv[1], len(kv[0])))[0][0]
    # respetar la capitalizacion mas comun del nombre elegido
    variants = defaultdict(int)
    for m in members:
        if m["nombre"].lower() == best:
            variants[m["nombre"]] += 1
    return sorted(variants.items(), key=lambda kv: -kv[1])[0][0]


def majority_tipo(members):
    counts = defaultdict(int)
    for m in members:
        t = m["tipo"] if m["tipo"] in TIPOS_NODO else "concepto"
        counts[t] += 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[0][0]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    items, hallazgos, docs_meta, bad_files = load_all()
    print(f"Docs extraidos: {len(docs_meta)} | menciones: {len(items)} | "
          f"hallazgos: {len(hallazgos)} | archivos rotos: {len(bad_files)}")
    for bf, err in bad_files:
        print(f"   ROTO: {bf}: {err}")

    clusters, ambiguous = cluster_concepts(items)
    clusters = {k: v for k, v in clusters.items() if v}
    print(f"Nodos candidatos: {len(clusters)} | pares ambiguos p/juez: {len(ambiguous)}")

    nodes = []
    for key, members in clusters.items():
        doc_ids = sorted({m["doc_id"] for m in members})
        citas, seen = [], set()
        for m in members:
            if m["cita"] and m["cita"] not in seen:
                seen.add(m["cita"])
                citas.append({"texto": m["cita"], "doc_id": m["doc_id"]})
        definiciones = [{"texto": m["definicion"], "doc_id": m["doc_id"]}
                        for m in members if m["definicion"]]
        rels = []
        for m in members:
            for r in m["relaciones"]:
                rels.append({"tipo": r["tipo"], "tipo_original": r["tipo_original"],
                             "objeto_texto": r["objeto"], "doc_id": m["doc_id"],
                             "revisar": r["revisar"]})
        nodes.append({
            "id": key,
            "nombre_canonico": pick_canonical(members),
            "tipo": majority_tipo(members),
            "nombres_vistos": sorted({m["nombre"] for m in members}),
            "menciones": len(members),
            "doc_frecuencia": len(doc_ids),
            "doc_ids": doc_ids,
            "definiciones": definiciones,
            "citas": citas,
            "relaciones_crudas": rels,
        })

    nodes.sort(key=lambda n: (-n["doc_frecuencia"], -n["menciones"]))

    json.dump(nodes, open(os.path.join(OUT_DIR, "nodos_dryrun.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump([{"clave_1": a, "clave_2": b} for a, b in ambiguous],
              open(os.path.join(OUT_DIR, "fusiones_dudosas.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(hallazgos, open(os.path.join(OUT_DIR, "hallazgos.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(docs_meta, open(os.path.join(OUT_DIR, "docs_meta.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)

    with open(os.path.join(OUT_DIR, "nodos_dryrun_resumen.txt"), "w",
              encoding="utf-8") as f:
        multi = [n for n in nodes if len(n["nombres_vistos"]) > 1]
        f.write(f"Total nodos: {len(nodes)}\n")
        f.write(f"Nodos con variantes fusionadas: {len(multi)}\n\n")
        f.write("=== Top 60 por doc_frecuencia ===\n")
        for n in nodes[:60]:
            f.write(f"[{n['doc_frecuencia']:3d} docs] ({n['tipo']:20s}) "
                    f"{n['nombre_canonico']}\n")
        f.write("\n=== Fusiones de nombres distintos (auditar) ===\n")
        for n in multi[:80]:
            f.write(f"{n['nombre_canonico']}  <-  {n['nombres_vistos']}\n")

    print(f"Salida en {OUT_DIR}: nodos_dryrun.json, fusiones_dudosas.json, "
          f"hallazgos.json, docs_meta.json, nodos_dryrun_resumen.txt")


if __name__ == "__main__":
    main()
