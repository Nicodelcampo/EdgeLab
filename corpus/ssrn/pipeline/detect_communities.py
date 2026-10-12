#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 4 del CerebroSSRN: deteccion de comunidades (Louvain, 100% local) sobre
grafo_final.json. Clon de detect_communities.py del CerebroJLP con los pesos de
arista adaptados al schema de 12 tipos del dominio quant.

USA/PARTE_DE son el "pegamento" generico (composicion tecnica) -> peso bajo,
para que no dominen la deteccion y todo colapse alrededor de hubs como
"limit order book" o "transaction costs". Las relaciones de contenido fuerte
(PREDICE, CAUSA, MEJORA_A, CONTRADICE_A, MITIGA) pesan mas.
"""
import json
import os

import networkx as nx

from consolidate_concepts import norm_key

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAFO_DIR = os.path.join(BASE, "grafo")
GRAFO_IN = os.path.join(GRAFO_DIR, "grafo_final.json")

EDGE_WEIGHTS = {
    "PREDICE": 1.2, "CAUSA": 1.2, "MEJORA_A": 1.1, "CONTRADICE_A": 1.1,
    "MITIGA": 1.0, "EQUIVALE_A": 1.2, "SE_OPONE_A": 1.0, "MIDE": 0.8,
    "APLICA_A": 0.7, "REQUIERE": 0.6,
    "USA": 0.3, "PARTE_DE": 0.3,
}


def main():
    d = json.load(open(GRAFO_IN, encoding="utf-8"))
    nodes = d["nodos"]
    node_by_id = {n["id"]: n for n in nodes}

    G = nx.Graph()
    for n in nodes:
        G.add_node(n["id"])
    for e in d["aristas"]:
        w = EDGE_WEIGHTS.get(e["tipo"], 0.5) * (1 + 0.15 * min(e["n_docs"], 4))
        if G.has_edge(e["origen"], e["destino"]):
            G[e["origen"]][e["destino"]]["weight"] += w
        else:
            G.add_edge(e["origen"], e["destino"], weight=w)

    communities = nx.community.louvain_communities(G, weight="weight", seed=42, resolution=1.0)
    communities = sorted(communities, key=len, reverse=True)

    print(f"Comunidades detectadas: {len(communities)}")
    sizes = [len(c) for c in communities]
    print(f"Tamanos: max={max(sizes)}, min={min(sizes)}, promedio={sum(sizes)/len(sizes):.1f}")
    print(f"Comunidades con >=5 nodos: {sum(1 for s in sizes if s >= 5)}")
    print(f"Nodos aislados (comunidad unitaria): {sum(1 for s in sizes if s == 1)}")

    out = []
    for i, comm in enumerate(communities):
        members = [node_by_id[nid] for nid in comm]
        members.sort(key=lambda m: -m["doc_frecuencia"])
        out.append({
            "id": i,
            "tamano": len(comm),
            "miembros_top": [
                {"nombre": m["nombre_canonico"], "tipo": m["tipo"],
                 "doc_frecuencia": m["doc_frecuencia"], "id": m["id"]}
                for m in members[:15]
            ],
            "miembros_todos_ids": list(comm),
        })

    out_path = os.path.join(GRAFO_DIR, "comunidades.json")
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"\nSalida: {out_path}")
    print("\nTop 25 comunidades (tamano, miembros mas centrales):")
    for c in out[:25]:
        nombres = ", ".join(m["nombre"] for m in c["miembros_top"][:6])
        print(f"  [{c['tamano']:3}] {nombres}")


if __name__ == "__main__":
    main()
