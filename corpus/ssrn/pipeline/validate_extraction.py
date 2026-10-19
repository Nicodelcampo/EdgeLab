#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de la Fase 2: chequea cada extraccion/completo/NNNN.json contra
su fuente. 100% local. Reporta:
  - JSON invalido o schema roto (sin conceptos, sin doc_id)
  - citas no textuales (proxy de alucinacion): % de citas que NO aparecen
    verbatim en el .txt fuente (normalizando espacios/ligaduras)
  - docs del manifest SIN extraccion

Salida: extraccion/validacion.json + resumen por stdout.
Uso:  python pipeline/validate_extraction.py [--umbral 0.7]
"""
import argparse
import glob
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPLETO = os.path.join(BASE, "extraccion", "completo")
DOCS = os.path.join(BASE, "Normalizado", "documentos")
MANIFEST = os.path.join(BASE, "Normalizado", "manifest.json")
OUT = os.path.join(BASE, "extraccion", "validacion.json")

LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
             "ﬄ": "ffl", "’": "'", "‘": "'", "“": '"',
             "”": '"', "–": "-", "—": "-"}


def norm(s):
    for k, v in LIGATURES.items():
        s = s.replace(k, v)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--umbral", type=float, default=0.7,
                    help="fraccion minima de citas exactas para aprobar")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    manifest = {e["id"]: e for e in json.load(open(MANIFEST, encoding="utf-8"))
                if e.get("id")}
    src_cache = {}

    resultados = {}
    for fp in sorted(glob.glob(os.path.join(COMPLETO, "*.json"))):
        name = os.path.basename(fp)
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            resultados[name] = {"estado": "json_invalido", "detalle": str(e)[:150]}
            continue
        doc_id = d.get("doc_id")
        if not doc_id or not isinstance(d.get("conceptos"), list):
            resultados[name] = {"estado": "schema_roto"}
            continue
        if not d["conceptos"]:
            resultados[name] = {"estado": "sin_conceptos"}
            continue
        entry = manifest.get(doc_id)
        if entry is None:
            resultados[name] = {"estado": "doc_id_desconocido"}
            continue
        if doc_id not in src_cache:
            path = os.path.join(DOCS, entry["archivo_normalizado"])
            src_cache[doc_id] = norm(open(path, encoding="utf-8").read())
        src = src_cache[doc_id]
        total, ok = 0, 0
        for c in d.get("conceptos", []) + d.get("hallazgos", []):
            cita = (c.get("cita_textual") or "").strip()
            if not cita:
                total += 1  # cita faltante cuenta como fallo
                continue
            total += 1
            if norm(cita) in src:
                ok += 1
        frac = ok / total if total else 0.0
        estado = "ok" if frac >= args.umbral else "citas_sospechosas"
        resultados[name] = {"estado": estado, "citas_exactas": ok,
                            "citas_total": total, "fraccion": round(frac, 3),
                            "n_conceptos": len(d["conceptos"]),
                            "n_hallazgos": len(d.get("hallazgos", []))}

    extraidos = {int(re.match(r"(\d+)", n).group(1)) for n in resultados
                 if re.match(r"\d+\.json$", n)}
    faltantes = sorted(set(manifest) - extraidos)

    report = {"resultados": resultados, "faltantes": faltantes}
    json.dump(report, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n_ok = sum(1 for r in resultados.values() if r["estado"] == "ok")
    problemas = {n: r for n, r in resultados.items() if r["estado"] != "ok"}
    print(f"Extracciones: {len(resultados)} | ok: {n_ok} | "
          f"problemas: {len(problemas)} | faltantes: {len(faltantes)}")
    for n, r in list(problemas.items())[:20]:
        print(f"   {n}: {r['estado']} {r.get('fraccion','')}")
    if faltantes:
        print(f"   doc_ids faltantes: {faltantes[:40]}{'...' if len(faltantes)>40 else ''}")
    print(f"Reporte -> {OUT}")


if __name__ == "__main__":
    main()
