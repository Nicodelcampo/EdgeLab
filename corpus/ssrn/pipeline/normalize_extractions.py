#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 2.5 del CerebroSSRN: normaliza extraccion/completo/*.json al esquema
canonico ANTES de consolidar. Necesario porque el corpus se extrajo con dos
motores (Sonnet via Workflow + Google Gemini a mano) y Gemini produjo
variantes de formato que hay que armonizar sin perder informacion:

  1. BOM UTF-8 al inicio del archivo (Windows) -> re-leer con utf-8-sig y
     reescribir limpio.
  2. `hallazgos` como lista de strings en vez de lista de objetos ->
     envolver cada string en {afirmacion: <str>, mercado: "no especificado",
     ...campos vacios...} con robustez "baja" (no sabemos las condiciones,
     asi que el default conservador es tratarlo como evidencia debil).
  3. Sin `doc_id` -> inferir del nombre de archivo (NNNN.json).
  4. Stubs sin `conceptos` (solo metadata title/authors/abstract): NO son
     extracciones reales -> se MUEVEN a extraccion/descartadas/ y se listan
     en extraccion/pendientes_reextraccion.json (principio: sin descartes
     silenciosos; estos docs necesitan re-extraccion real).

Idempotente: correr de nuevo sobre archivos ya canonicos no los cambia.
Uso:  python pipeline/normalize_extractions.py
"""
import json
import os
import re
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPLETO = os.path.join(BASE, "extraccion", "completo")
DESCARTADAS = os.path.join(BASE, "extraccion", "descartadas")
PENDIENTES = os.path.join(BASE, "extraccion", "pendientes_reextraccion.json")

ID_RE = re.compile(r"(\d{3,4})\.json$")


def load_any(fp):
    """Lee JSON tolerando BOM. Devuelve (obj, tenia_bom)."""
    raw = open(fp, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    return json.loads(text), bom


def coerce_hallazgo(h):
    if isinstance(h, dict):
        return h
    return {"afirmacion": str(h), "mercado": "no especificado",
            "periodo": "no especificado", "magnitud": "",
            "condiciones": "extraido por Gemini sin desglose de condiciones",
            "robustez": "baja", "cita_textual": ""}


def main():
    os.makedirs(DESCARTADAS, exist_ok=True)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    reparados_bom = reparados_hall = reparados_docid = 0
    descartados = []
    canonicos = 0

    for fname in sorted(os.listdir(COMPLETO)):
        if not fname.endswith(".json"):
            continue
        fp = os.path.join(COMPLETO, fname)
        m = ID_RE.search(fname)
        doc_id_fname = int(m.group(1)) if m else None

        try:
            d, had_bom = load_any(fp)
        except Exception as e:
            descartados.append({"archivo": fname, "motivo": f"json invalido: {e}"[:150]})
            shutil.move(fp, os.path.join(DESCARTADAS, fname))
            continue

        conc = d.get("conceptos")
        if not isinstance(conc, list) or len(conc) == 0 or \
                not all(isinstance(c, dict) for c in conc):
            descartados.append({"archivo": fname, "doc_id": doc_id_fname,
                                "motivo": "sin conceptos validos (stub de metadata o schema roto)",
                                "titulo": d.get("title") or d.get("titulo", "")})
            shutil.move(fp, os.path.join(DESCARTADAS, fname))
            continue

        changed = had_bom

        if "doc_id" not in d or not isinstance(d.get("doc_id"), int):
            d["doc_id"] = doc_id_fname
            reparados_docid += 1
            changed = True

        hall = d.get("hallazgos", [])
        if isinstance(hall, list) and any(not isinstance(h, dict) for h in hall):
            d["hallazgos"] = [coerce_hallazgo(h) for h in hall]
            reparados_hall += 1
            changed = True
        elif not isinstance(hall, list):
            d["hallazgos"] = []
            changed = True

        if had_bom:
            reparados_bom += 1

        if changed:
            json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        canonicos += 1

    if descartados:
        json.dump(descartados, open(PENDIENTES, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    print(f"Extracciones canonicas listas: {canonicos}")
    print(f"  reparado BOM: {reparados_bom} | hallazgos-strings: {reparados_hall} | "
          f"doc_id inferido: {reparados_docid}")
    print(f"Descartadas (movidas a descartadas/, necesitan re-extraccion): {len(descartados)}")
    if descartados:
        print(f"  -> {PENDIENTES}")
        for x in descartados[:25]:
            print(f"     {x['archivo']}: {x['motivo']}")


if __name__ == "__main__":
    main()
