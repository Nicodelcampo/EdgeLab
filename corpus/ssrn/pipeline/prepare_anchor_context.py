#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 5 (prep) del CerebroSSRN: el analogo de "anclaje topologico" del
CerebroJLP, pero en vez de anclar el grafo a 11 diagramas de una escuela,
lo ancla al ECOSISTEMA REAL de trading del usuario (quantlab/VectorBT sobre
ES futures). Esta es la pieza que cierra el circuito memoria-cerebro que
pidio el usuario: no un grafo que se admira a si mismo, sino un puente
accionable hacia el codigo y los resultados que ya existen.

Esta parte es 100% local y determinista: arma el PAQUETE DE CONTEXTO que
despues un agente (juicio, no mecanica) usa para escribir el cruce real
en grafo/anclaje_ecosistema.json + cerebro/PUENTE_ECOSISTEMA.md.

Reune:
  1. Los conceptos del NUCLEO del grafo con mayor relevancia declarada a
     "ES intradia" (aplicabilidad_es_intradia.nivel alta/media en los docs
     que lo mencionan) + los de tipo estrategia/riesgo_metodologico.
  2. Los hallazgos de robustez alta/media cuyo mercado matchea futuros de
     indice / HFT / order flow (el dominio mas cercano al ES).
  3. Un resumen del ESTADO ACTUAL del ecosistema propio: schema del logger
     hft_zones, la regla de mitigacion (strict_touch), y los resultados
     reales de runs/excursion_study (el estudio de zonas corrido el
     2026-07-12) -- para que el cruce sea contra evidencia propia, no
     contra suposiciones.

Salida: grafo/contexto_anclaje.json (paquete listo para el agente).
"""
import glob
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAFO = os.path.join(BASE, "grafo", "grafo_final.json")
DOCS_META = os.path.join(BASE, "grafo", "docs_meta.json")
HALLAZGOS = os.path.join(BASE, "grafo", "hallazgos.json")
OUT = os.path.join(BASE, "grafo", "contexto_anclaje.json")

VECTORBT_DIR = r"C:\$AVectorBTecosistema"
MITIGATION_PY = os.path.join(VECTORBT_DIR, "quantlab", "core", "mitigation.py")
LOGGERS_PY = os.path.join(VECTORBT_DIR, "quantlab", "data", "loggers.py")
BRUTE_EXCURSIONS_PY = os.path.join(VECTORBT_DIR, "scripts", "brute_excursions.py")

RELEVANT_TIPOS = {"estrategia", "riesgo_metodologico", "metodo", "metrica"}
MICROSTRUCTURE_MARKET_HINTS = (
    "es", "e-mini", "s&p", "futures", "futuro", "hft", "high-frequency",
    "high frequency", "order book", "limit order", "index"
)


def latest_run_dir():
    candidates = sorted(glob.glob(os.path.join(VECTORBT_DIR, "runs", "excursion_study", "*")))
    return candidates[-1] if candidates else None


def main():
    graph = json.load(open(GRAFO, encoding="utf-8"))
    docs_meta = json.load(open(DOCS_META, encoding="utf-8")) if os.path.exists(DOCS_META) else {}
    hallazgos = json.load(open(HALLAZGOS, encoding="utf-8")) if os.path.exists(HALLAZGOS) else []

    nodes = graph["nodos"]
    degree = {}
    for e in graph["aristas"]:
        degree[e["origen"]] = degree.get(e["origen"], 0) + 1
        degree[e["destino"]] = degree.get(e["destino"], 0) + 1

    # docs con alta/media aplicabilidad a ES intradia
    docs_aplicables = {int(k) for k, v in docs_meta.items()
                       if (v.get("aplicabilidad_es_intradia") or {}).get("nivel") in ("alta", "media")}

    candidatos = []
    for n in nodes:
        relevante_tipo = n["tipo"] in RELEVANT_TIPOS
        relevante_doc = bool(set(n["doc_ids"]) & docs_aplicables)
        troncal = n["doc_frecuencia"] >= 3 or degree.get(n["id"], 0) >= 4
        if (relevante_tipo or relevante_doc) and troncal:
            defin = n["definiciones"][0]["texto"] if n["definiciones"] else ""
            candidatos.append({
                "id": n["id"], "nombre": n["nombre_canonico"], "tipo": n["tipo"],
                "doc_frecuencia": n["doc_frecuencia"], "definicion": defin[:400],
            })
    candidatos.sort(key=lambda c: -c["doc_frecuencia"])

    hallazgos_relevantes = []
    for h in hallazgos:
        mercado = (h.get("mercado") or "").lower()
        if h.get("robustez") in ("alta", "media") and any(
                hint in mercado for hint in MICROSTRUCTURE_MARKET_HINTS):
            hallazgos_relevantes.append(h)

    ecosistema = {
        "mitigation_py": open(MITIGATION_PY, encoding="utf-8").read()
                         if os.path.exists(MITIGATION_PY) else None,
        "loggers_hft_zones_schema": None,
        "brute_excursions_setup_docstring": None,
        "ultimo_estudio": None,
    }
    if os.path.exists(LOGGERS_PY):
        text = open(LOGGERS_PY, encoding="utf-8").read()
        i = text.find("class HftZonesLogger")
        ecosistema["loggers_hft_zones_schema"] = text[i:i + 1500] if i >= 0 else None
    if os.path.exists(BRUTE_EXCURSIONS_PY):
        text = open(BRUTE_EXCURSIONS_PY, encoding="utf-8").read()
        ecosistema["brute_excursions_setup_docstring"] = text[:text.find('"""', 4) + 3]

    run_dir = latest_run_dir()
    if run_dir:
        manifest_fp = os.path.join(run_dir, "manifest.json")
        robust_fp = os.path.join(run_dir, "robust_is_oos.csv")
        ecosistema["ultimo_estudio"] = {
            "run_dir": run_dir,
            "manifest": json.load(open(manifest_fp, encoding="utf-8")) if os.path.exists(manifest_fp) else None,
            "robust_top_lines": (open(robust_fp, encoding="utf-8").read().splitlines()[:20]
                                 if os.path.exists(robust_fp) else None),
        }

    out = {
        "conceptos_candidatos": candidatos,
        "hallazgos_relevantes": hallazgos_relevantes,
        "ecosistema": ecosistema,
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Conceptos candidatos para anclaje: {len(candidatos)}")
    print(f"Hallazgos relevantes (microestructura/futuros, robustez media+): {len(hallazgos_relevantes)}")
    print(f"Ultimo estudio del ecosistema: {run_dir or 'NO ENCONTRADO'}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
