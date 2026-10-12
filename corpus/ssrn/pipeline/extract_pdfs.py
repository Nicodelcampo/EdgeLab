#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 0 del CerebroSSRN: PDFs -> texto plano normalizado + manifest.

Clon del patron de normalize_transcripts.py del CerebroJLP, adaptado a
papers academicos en PDF:
  - PyMuPDF extrae el texto por pagina (100% local, $0).
  - Se cruza cada PDF con ssrn_papers_master.csv via el SSRN id que viene
    entre corchetes en el nombre del archivo ([2848281].pdf) y en la URL
    del CSV (doi.org/10.2139/ssrn.2848281).
  - Se detectan PDFs escaneados/vacios (pocas letras por pagina) y se
    marcan en el manifest con calidad='sospechosa'|'vacia' — NO se
    descartan en silencio (principio: sin truncamientos silenciosos).
  - Deduplicacion por ssrn_id (el mismo paper bajado dos veces).

Salida:
  Normalizado/documentos/NNNN_<slug>.txt
  Normalizado/manifest.json / manifest.csv

Ejecutar:  python pipeline/extract_pdfs.py
"""
import csv
import json
import os
import re
import sys
import unicodedata

import fitz  # PyMuPDF

PDF_DIR = r"C:\$ASSRNdownloader\PDFs"
MASTER_CSV = r"C:\$ASSRNdownloader\ssrn_papers_master.csv"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE, "Normalizado", "documentos")
MANIFEST_JSON = os.path.join(BASE, "Normalizado", "manifest.json")
MANIFEST_CSV = os.path.join(BASE, "Normalizado", "manifest.csv")

SSRN_ID_RE = re.compile(r"\[(\d{5,8})\]\.pdf$", re.IGNORECASE)
CSV_ID_RE = re.compile(r"ssrn\.(\d{5,8})")

MIN_CHARS_PER_PAGE = 200   # debajo de esto por promedio -> escaneado probable
MIN_TOTAL_WORDS = 500      # debajo -> vacia/rota


def slugify(title, max_len=60):
    t = unicodedata.normalize("NFKD", title)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s-]", "", t).strip().lower()
    t = re.sub(r"[\s_-]+", "_", t)
    return t[:max_len].rstrip("_") or "sin_titulo"


def clean_page_text(text):
    # normaliza espacios sin romper parrafos; PyMuPDF ya separa bloques con \n
    text = text.replace("\x00", " ")
    # des-hifenado de fin de linea: "micro-\nstructure" -> "microstructure"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return text


def extract_pdf(path):
    doc = fitz.open(path)
    pages = []
    for page in doc:
        pages.append(clean_page_text(page.get_text("text")))
    n_pages = len(doc)
    doc.close()
    full = "\n\n".join(pages)
    # colapsa saltos multiples pero conserva separacion de parrafo
    full = re.sub(r"\n{3,}", "\n\n", full)
    return full, n_pages


def load_master():
    """ssrn_id -> metadata del CSV maestro."""
    meta = {}
    with open(MASTER_CSV, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            m = CSV_ID_RE.search(row.get("URL", "") or "")
            if not m:
                continue
            sid = m.group(1)
            if sid not in meta:  # primera aparicion gana
                meta[sid] = {
                    "titulo_csv": (row.get("Title") or "").strip(),
                    "autores": (row.get("Authors") or "").strip(),
                    "keyword_source": (row.get("Keyword_Source") or "").strip(),
                    "abstract": (row.get("Abstract") or "").strip(),
                    "url": (row.get("URL") or "").strip(),
                }
    return meta


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    master = load_master()
    print(f"Metadata del CSV maestro: {len(master)} papers con ssrn_id")

    pdfs = sorted(p for p in os.listdir(PDF_DIR) if p.lower().endswith(".pdf"))
    print(f"PDFs en disco: {len(pdfs)}")

    manifest = []
    seen_ids = {}
    doc_id = 0
    errors = []

    for fname in pdfs:
        path = os.path.join(PDF_DIR, fname)
        m = SSRN_ID_RE.search(fname)
        sid = m.group(1) if m else None

        try:
            text, n_pages = extract_pdf(path)
        except Exception as e:
            errors.append((fname, str(e)))
            manifest.append({
                "id": None, "ssrn_id": sid, "archivo_pdf": fname,
                "archivo_normalizado": None, "titulo": fname[:-4],
                "autores": "", "keyword_source": "", "url": "",
                "paginas": 0, "palabras": 0, "chars_por_pagina": 0,
                "calidad": "error", "es_duplicado": False,
                "error": str(e)[:200],
            })
            continue

        words = len(text.split())
        cpp = len(text) / max(n_pages, 1)

        if words < MIN_TOTAL_WORDS:
            calidad = "vacia"
        elif cpp < MIN_CHARS_PER_PAGE:
            calidad = "sospechosa"
        else:
            calidad = "ok"

        dup = sid is not None and sid in seen_ids
        info = master.get(sid, {})
        titulo = info.get("titulo_csv") or re.sub(r"\s*\[\d+\]\.pdf$", "", fname, flags=re.I)
        # limpia restos de html en titulos del CSV ("<b>...</b>")
        titulo = re.sub(r"<[^>]+>|&[a-z]+;", "", titulo).strip() or fname[:-4]

        entry = {
            "id": None,
            "ssrn_id": sid,
            "archivo_pdf": fname,
            "archivo_normalizado": None,
            "titulo": titulo,
            "autores": info.get("autores", ""),
            "keyword_source": info.get("keyword_source", ""),
            "url": info.get("url", ""),
            "paginas": n_pages,
            "palabras": words,
            "chars_por_pagina": round(cpp),
            "calidad": calidad,
            "es_duplicado": dup,
        }

        if not dup and calidad in ("ok", "sospechosa"):
            doc_id += 1
            entry["id"] = doc_id
            fname_out = f"{doc_id:04d}_{slugify(titulo)}.txt"
            entry["archivo_normalizado"] = fname_out
            with open(os.path.join(DOCS_DIR, fname_out), "w", encoding="utf-8") as f:
                f.write(text)
            if sid:
                seen_ids[sid] = doc_id

        manifest.append(entry)

    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    cols = ["id", "ssrn_id", "archivo_pdf", "archivo_normalizado", "titulo",
            "autores", "keyword_source", "paginas", "palabras",
            "chars_por_pagina", "calidad", "es_duplicado"]
    with open(MANIFEST_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(manifest)

    ok = sum(1 for e in manifest if e["calidad"] == "ok" and not e["es_duplicado"])
    sosp = sum(1 for e in manifest if e["calidad"] == "sospechosa" and not e["es_duplicado"])
    vac = sum(1 for e in manifest if e["calidad"] == "vacia")
    dups = sum(1 for e in manifest if e["es_duplicado"])
    sin_meta = sum(1 for e in manifest if e["id"] and not e["autores"])
    total_words = sum(e["palabras"] for e in manifest if e["id"])
    print(f"\nDocumentos utiles: {doc_id}  (ok={ok}, sospechosos={sosp})")
    print(f"Descartados: vacios={vac}, duplicados={dups}, errores={len(errors)}")
    print(f"Sin metadata del CSV: {sin_meta}")
    print(f"Palabras totales del corpus util: {total_words:,}")
    for fname, err in errors[:10]:
        print(f"  ERROR {fname}: {err}")
    print(f"\nManifest -> {MANIFEST_JSON}")


if __name__ == "__main__":
    main()
