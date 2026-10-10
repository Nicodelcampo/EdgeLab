#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 6 del CerebroSSRN: genera el paquete de contexto.

Diseno de dos niveles (heredado del CerebroJLP):
  - NUCLEO (cerebro/nucleo_grafo.md): nodos con doc_frecuencia>=2 O grado>=4
    -- SIEMPRE va al contexto del modelo.
  - INDICE (cerebro/indice_cola_larga.md): una linea por nodo restante.

Adaptacion propia del dominio quant: ademas del grafo, vuelca
grafo/hallazgos.json en cerebro/hallazgos_por_mercado.md agrupado por
mercado -- es el analogo de los "casos_aplicados" del JLP: el barro
empirico (backtests, numeros, condiciones) organizado para consulta rapida
por instrumento, no solo por concepto.
"""
import json
import os
import re
from collections import defaultdict

from consolidate_concepts import norm_key

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAFO = os.path.join(BASE, "grafo", "grafo_final.json")
HALLAZGOS = os.path.join(BASE, "grafo", "hallazgos.json")
OUT_DIR = os.path.join(BASE, "cerebro")


def best_definition(n):
    defs = n.get("definiciones", [])
    if not defs:
        return ""
    return max(defs, key=lambda d: len(d["texto"]))["texto"]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    d = json.load(open(GRAFO, encoding="utf-8"))
    nodes = d["nodos"]
    by_id = {n["id"]: n for n in nodes}

    degree = defaultdict(int)
    edges_out = defaultdict(list)
    for e in d["aristas"]:
        degree[e["origen"]] += 1
        degree[e["destino"]] += 1
        edges_out[e["origen"]].append((e["tipo"], e["destino"], e["n_docs"]))

    core_ids = {n["id"] for n in nodes
                if n["doc_frecuencia"] >= 2 or degree[n["id"]] >= 4}
    core = [n for n in nodes if n["id"] in core_ids]
    tail = [n for n in nodes if n["id"] not in core_ids]
    core.sort(key=lambda n: (-n["doc_frecuencia"], -degree[n["id"]]))
    tail.sort(key=lambda n: n["nombre_canonico"].lower())

    # ---------------------------------------------------------------- NUCLEO
    lines = [
        "# Núcleo del grafo — CerebroSSRN (trading cuantitativo)",
        "",
        f"{len(core)} conceptos centrales (de {len(nodes)} totales; el resto en el índice de cola larga).",
        "Formato: **Nombre** [tipo] (docs=N) — definición. Relaciones: TIPO → Objeto (n_docs).",
        "",
    ]
    for n in core:
        defin = best_definition(n).replace("\n", " ").strip()
        if len(defin) > 280:
            defin = defin[:277] + "..."
        rels, seen = [], set()
        for tipo, tgt, ndocs in sorted(edges_out[n["id"]], key=lambda x: -x[2]):
            key = (tipo, tgt)
            if key in seen:
                continue
            seen.add(key)
            rels.append(f"{tipo} → {by_id[tgt]['nombre_canonico']} ({ndocs})")
        rel_str = ("  \n  Relaciones: " + "; ".join(rels[:8])) if rels else ""
        variantes = [v for v in n["nombres_vistos"] if v != n["nombre_canonico"]][:4]
        var_str = f" [también: {', '.join(variantes)}]" if variantes else ""
        lines.append(f"**{n['nombre_canonico']}** [{n['tipo']}] (docs={n['doc_frecuencia']}){var_str} — {defin}{rel_str}")
        lines.append("")

    nucleo_path = os.path.join(OUT_DIR, "nucleo_grafo.md")
    open(nucleo_path, "w", encoding="utf-8").write("\n".join(lines))

    # ---------------------------------------------------------------- INDICE
    ilines = [
        "# Índice de cola larga — conceptos de mención única o baja conectividad",
        "",
        f"{len(tail)} conceptos. El Cerebro puede pedir la expansión completa "
        "(citas + relaciones) buscando el id en grafo/grafo_final.json.",
        "",
    ]
    for n in tail:
        defin = best_definition(n).replace("\n", " ").strip()
        if len(defin) > 140:
            defin = defin[:137] + "..."
        ilines.append(f"- **{n['nombre_canonico']}** [{n['tipo']}] (id={n['id']}): {defin}")

    indice_path = os.path.join(OUT_DIR, "indice_cola_larga.md")
    open(indice_path, "w", encoding="utf-8").write("\n".join(ilines))

    # ---------------------------------------------------------- HALLAZGOS
    hallazgos = json.load(open(HALLAZGOS, encoding="utf-8")) if os.path.exists(HALLAZGOS) else []
    by_mercado = defaultdict(list)
    for h in hallazgos:
        mercado = (h.get("mercado") or "no especificado").strip()
        by_mercado[mercado].append(h)

    def mercado_bucket(m):
        ml = m.lower()
        if re.search(r"\bes\b|e-mini|s&p|sp500|s&p 500|spx", ml):
            return "ES / S&P 500 futures"
        if re.search(r"futures|futuro", ml) and not re.search(r"crypto|btc|bitcoin", ml):
            return "otros futuros"
        if re.search(r"crypto|btc|bitcoin|eth|ether", ml):
            return "cripto"
        if re.search(r"fx|forex|currency|eurusd|exchange rate", ml):
            return "FX"
        if re.search(r"equit|stock|nasdaq|nyse", ml):
            return "equities"
        if re.search(r"no especificado|not specified|n/a|^-$|^$", ml):
            return "no especificado / sintético"
        return "otros"

    grouped = defaultdict(list)
    for m, hs in by_mercado.items():
        grouped[mercado_bucket(m)].extend(hs)

    hlines = [
        "# Hallazgos empíricos por mercado — CerebroSSRN",
        "",
        f"{len(hallazgos)} hallazgos extraídos de {len(set(h['doc_id'] for h in hallazgos))} papers. "
        "Es el barro empírico: resultados de backtests/experimentos con sus condiciones y robustez declarada.",
        "El orden dentro de cada mercado prioriza robustez alta > media > baja.",
        "",
    ]
    orden_robustez = {"alta": 0, "media": 1, "baja": 2}
    for bucket in sorted(grouped, key=lambda b: -len(grouped[b])):
        hs = grouped[bucket]
        hs.sort(key=lambda h: orden_robustez.get(h.get("robustez", "baja"), 3))
        hlines.append(f"## {bucket} ({len(hs)} hallazgos)")
        hlines.append("")
        for h in hs:
            rob = h.get("robustez", "?")
            hlines.append(f"- **[{rob}]** (doc {h['doc_id']}, {h.get('mercado','')}, "
                          f"{h.get('periodo','período no especificado')}) {h.get('afirmacion','')} "
                          f"— *{h.get('magnitud','')}*. Condiciones: {h.get('condiciones','')}")
        hlines.append("")

    hallazgos_path = os.path.join(OUT_DIR, "hallazgos_por_mercado.md")
    open(hallazgos_path, "w", encoding="utf-8").write("\n".join(hlines))

    for p in (nucleo_path, indice_path, hallazgos_path):
        words = len(open(p, encoding="utf-8").read().split())
        print(f"{os.path.basename(p)}: ~{words} palabras (~{int(words*1.4)} tokens aprox), "
              f"{os.path.getsize(p)/1024:.0f} KB")
    print(f"Core: {len(core)} nodos | Cola larga: {len(tail)} nodos | Hallazgos: {len(hallazgos)}")


if __name__ == "__main__":
    main()
