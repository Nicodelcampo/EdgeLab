#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 3b del CerebroSSRN: construye el grafo final desde los nodos candidatos
(nodos_dryrun.json) + las decisiones de los jueces LLM aplicadas como CAPA
DECLARATIVA (grafo/decisiones_jueces.json).

Lección heredada del CerebroJLP (defecto #2 de su revisión lógica): el
pipeline debe ser IDEMPOTENTE y reconstruible desde cero — las decisiones de
fusión nunca se aplican como parches encadenados sino que viven en un archivo
declarativo que este script consume. Re-correr consolidate + build_graph
regenera exactamente el mismo grafo.

decisiones_jueces.json (opcional; si no existe, no se aplica nada):
[
  {"accion": "fusionar", "claves": ["k1", "k2", ...], "canonico": "nombre",
   "motivo": "..."},
  {"accion": "no_fusionar", "claves": ["k1", "k2"], "motivo": "..."}   # documental
]

Resolución de aristas: cada relación cruda (objeto_texto) se resuelve contra
los nodos vía norm_key + variantes. Las no resueltas quedan contadas en
grafo/relaciones_sin_destino.json (no se inventan nodos destino).

Salida: grafo/grafo_final.json  {"nodos": [...], "aristas": [...]}
        grafo/grafo_final.graphml (para NetworkX/Gephi)
        grafo/grafo_final_stats.txt
"""
import json
import os
from collections import defaultdict

import networkx as nx

from consolidate_concepts import norm_key  # misma normalizacion SIEMPRE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAFO_DIR = os.path.join(BASE, "grafo")
DRYRUN = os.path.join(GRAFO_DIR, "nodos_dryrun.json")
DECISIONES = os.path.join(GRAFO_DIR, "decisiones_jueces.json")
# Sin versionado v1/v2/v3 a proposito (correccion preventiva del defecto #2
# documentado en el PLAN.md del CerebroJLP): este script es la UNICA fuente
# de verdad, siempre reconstruible desde nodos_dryrun.json + decisiones
# declarativas. grafo_final.json ES el grafo, no un checkpoint intermedio.
OUT_JSON = os.path.join(GRAFO_DIR, "grafo_final.json")
OUT_GRAPHML = os.path.join(GRAFO_DIR, "grafo_final.graphml")
OUT_STATS = os.path.join(GRAFO_DIR, "grafo_final_stats.txt")
OUT_SIN_DESTINO = os.path.join(GRAFO_DIR, "relaciones_sin_destino.json")

MIN_DOC_FREC_ARISTA_DEBIL = 1  # aristas con 1 solo doc: se conservan pero marcadas


def merge_nodes(a, b):
    """Fusiona b dentro de a (agregando evidencia, sin perder nada)."""
    a["nombres_vistos"] = sorted(set(a["nombres_vistos"]) | set(b["nombres_vistos"]))
    a["menciones"] += b["menciones"]
    a["doc_ids"] = sorted(set(a["doc_ids"]) | set(b["doc_ids"]))
    a["doc_frecuencia"] = len(a["doc_ids"])
    a["definiciones"].extend(b["definiciones"])
    seen = {c["texto"] for c in a["citas"]}
    a["citas"].extend(c for c in b["citas"] if c["texto"] not in seen)
    a["relaciones_crudas"].extend(b["relaciones_crudas"])
    return a


def main():
    nodes = json.load(open(DRYRUN, encoding="utf-8"))
    by_id = {n["id"]: n for n in nodes}
    alias = {}  # clave fusionada -> clave canonica
    relation_overrides = {}  # tipo_original -> (tipo_destino, invertir)

    n_fusiones = 0
    if os.path.exists(DECISIONES):
        decisiones = json.load(open(DECISIONES, encoding="utf-8"))
        for d in decisiones:
            if d.get("accion") == "mapear_relacion":
                relation_overrides[d["tipo_original"]] = (d["tipo_destino"], bool(d.get("invertir")))
                continue
            if d.get("accion") == "tipo_relacion_nuevo":
                relation_overrides[d["tipo_original"]] = (d["tipo_propuesto"], False)
                continue
            if d.get("accion") != "fusionar":
                continue
            claves = [k for k in d["claves"] if k in by_id or k in alias]
            claves = [alias.get(k, k) for k in claves]
            claves = sorted(set(k for k in claves if k in by_id))
            if len(claves) < 2:
                continue
            target = claves[0]
            for k in claves[1:]:
                merge_nodes(by_id[target], by_id[k])
                del by_id[k]
                alias[k] = target
                # re-apuntar aliases previos que apuntaban a k
                for kk, vv in list(alias.items()):
                    if vv == k:
                        alias[kk] = target
                n_fusiones += 1
            if d.get("canonico"):
                by_id[target]["nombre_canonico"] = d["canonico"]
        print(f"Decisiones de jueces aplicadas: {n_fusiones} fusiones")
    else:
        print("(sin decisiones_jueces.json — grafo sin fusiones semanticas)")

    nodes = sorted(by_id.values(),
                   key=lambda n: (-n["doc_frecuencia"], -n["menciones"]))

    # indice de resolucion: norm_key de cada nombre visto -> id de nodo
    resolver = {}
    for n in nodes:
        for name in [n["nombre_canonico"]] + n["nombres_vistos"]:
            k = norm_key(name)
            if k and k not in resolver:
                resolver[k] = n["id"]
        resolver[n["id"]] = n["id"]
    for k_alias, k_target in alias.items():
        resolver.setdefault(k_alias, k_target)

    # aristas agregadas
    edge_acc = defaultdict(lambda: {"doc_ids": set(), "tipos_originales": set()})
    sin_destino = defaultdict(lambda: {"n": 0, "docs": set(), "tipos": set()})
    n_overrides_aplicados = 0
    for n in nodes:
        for r in n["relaciones_crudas"]:
            k_obj = norm_key(r["objeto_texto"])
            dest = resolver.get(k_obj)
            if dest is None or dest == n["id"]:
                if dest is None:
                    s = sin_destino[k_obj]
                    s["n"] += 1
                    s["docs"].add(r["doc_id"])
                    s["tipos"].add(r["tipo"])
                continue

            tipo, origen, destino = r["tipo"], n["id"], dest
            if r.get("revisar") and r["tipo_original"] in relation_overrides:
                tipo, invertir = relation_overrides[r["tipo_original"]]
                n_overrides_aplicados += 1
                if invertir:
                    origen, destino = destino, origen
            elif r.get("revisar"):
                continue  # tipo sin mapear y sin decision de juez: no se materializa como arista

            key = (origen, destino, tipo)
            edge_acc[key]["doc_ids"].add(r["doc_id"])
            edge_acc[key]["tipos_originales"].add(r["tipo_original"])

    aristas = []
    for (origen, destino, tipo), info in edge_acc.items():
        aristas.append({
            "origen": origen, "destino": destino, "tipo": tipo,
            "n_docs": len(info["doc_ids"]),
            "doc_ids": sorted(info["doc_ids"]),
            "confianza": "alta" if len(info["doc_ids"]) >= 3 else
                         ("media" if len(info["doc_ids"]) == 2 else "baja"),
        })
    aristas.sort(key=lambda e: -e["n_docs"])

    graph = {"nodos": nodes, "aristas": aristas}
    json.dump(graph, open(OUT_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    sd = [{"objeto": k, "menciones": v["n"], "n_docs": len(v["docs"]),
           "tipos": sorted(v["tipos"])} for k, v in sin_destino.items()]
    sd.sort(key=lambda x: -x["menciones"])
    json.dump(sd, open(OUT_SIN_DESTINO, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # GraphML
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"], nombre=n["nombre_canonico"], tipo=n["tipo"],
                   doc_frecuencia=n["doc_frecuencia"])
    for e in aristas:
        G.add_edge(e["origen"], e["destino"], tipo=e["tipo"], n_docs=e["n_docs"])
    nx.write_graphml(G, OUT_GRAPHML)

    tipos_nodo = defaultdict(int)
    for n in nodes:
        tipos_nodo[n["tipo"]] += 1
    tipos_arista = defaultdict(int)
    for e in aristas:
        tipos_arista[e["tipo"]] += 1
    with open(OUT_STATS, "w", encoding="utf-8") as f:
        f.write(f"Nodos: {len(nodes)}\nAristas: {len(aristas)}\n")
        f.write(f"Fusiones de jueces aplicadas: {n_fusiones}\n")
        f.write(f"Overrides de tipo de relacion aplicados: {n_overrides_aplicados}\n")
        f.write(f"Relaciones sin destino (objetos no resueltos): {len(sd)}\n\n")
        f.write("Nodos por tipo:\n")
        for t, c in sorted(tipos_nodo.items(), key=lambda kv: -kv[1]):
            f.write(f"  {t}: {c}\n")
        f.write("\nAristas por tipo:\n")
        for t, c in sorted(tipos_arista.items(), key=lambda kv: -kv[1]):
            f.write(f"  {t}: {c}\n")
        f.write("\nTop 30 nodos por doc_frecuencia:\n")
        for n in nodes[:30]:
            f.write(f"  [{n['doc_frecuencia']:3d}] {n['nombre_canonico']} ({n['tipo']})\n")

    print(f"Grafo: {len(nodes)} nodos, {len(aristas)} aristas")
    print(f"Relaciones sin destino: {len(sd)} objetos distintos")
    print(f"-> {OUT_JSON}\n-> {OUT_GRAPHML}\n-> {OUT_STATS}")


if __name__ == "__main__":
    main()
