#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 3b (prep) del CerebroSSRN: reduce nodos_dryrun.json a un paquete
compacto para que un juez LLM (Sonnet/Opus, pocas llamadas) resuelva SOLO
lo que un script no puede: sinonimia real de dominio (no ortografica) y
tipos de relacion que no se pudieron mapear sin ambiguedad.

Clon de prepare_opus_review.py del CerebroJLP, con una diferencia de
diseno DELIBERADA (correccion preventiva del defecto #2 documentado en el
PLAN.md del JLP: "pipeline no reproducible, decisiones como parches
encadenados"): la salida NO se aplica in-place sobre nodos_dryrun.json.
El juez debe escribir sus decisiones en el formato declarativo que
build_graph.py consume (grafo/decisiones_jueces.json), y build_graph.py
reconstruye el grafo completo desde cero cada vez. Correr este script de
nuevo con nodos_dryrun.json actualizado y decisiones_jueces.json existente
es seguro: build_graph.py es la unica fuente de verdad de la fusion.

Salida: grafo/paquete_revision_jueces.json
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAFO_DIR = os.path.join(BASE, "grafo")

TOP_N_NODES = 260
MAX_VARIANTS_SHOWN = 15
MAX_CITAS_SHOWN = 2

FORMATO_RESPUESTA = """
FORMATO DE SALIDA REQUERIDO — escribir en grafo/decisiones_jueces.json
(lista JSON, cada item es una de las dos formas):

  {"accion": "fusionar", "claves": ["id_nodo_1", "id_nodo_2", ...],
   "canonico": "Nombre Final Elegido", "motivo": "..."}

  {"accion": "no_fusionar", "claves": ["id_nodo_1", "id_nodo_2"],
   "motivo": "..."}   (documental; no cambia el grafo, pero deja constancia
                       de que el par fue revisado y decidido a proposito)

Usar el campo "id" de cada nodo (NO el nombre_propuesto) en "claves".
Para los tipos de relacion sin mapear, agregar ademas items:

  {"accion": "mapear_relacion", "tipo_original": "...",
   "tipo_destino": "UNO_DE_LOS_12_TIPOS_CERRADOS", "invertir": false,
   "motivo": "..."}

  {"accion": "tipo_relacion_nuevo", "tipo_original": "...",
   "tipo_propuesto": "NUEVO_TIPO", "motivo": "..."}
"""


def main():
    nodes = json.load(open(os.path.join(GRAFO_DIR, "nodos_dryrun.json"), encoding="utf-8"))
    nodes.sort(key=lambda n: (-n["doc_frecuencia"], -n["menciones"]))
    top = nodes[:TOP_N_NODES]

    compact = []
    for n in top:
        compact.append({
            "id": n["id"],
            "nombre_propuesto": n["nombre_canonico"],
            "tipo": n["tipo"],
            "doc_frecuencia": n["doc_frecuencia"],
            "variantes_fusionadas": n["nombres_vistos"][:MAX_VARIANTS_SHOWN],
            "variantes_truncadas": len(n["nombres_vistos"]) > MAX_VARIANTS_SHOWN,
            "definiciones_muestra": [d["texto"] for d in n["definiciones"][:2]],
            "citas_muestra": [c["texto"] for c in n["citas"][:MAX_CITAS_SHOWN]],
        })

    ambiguous_path = os.path.join(GRAFO_DIR, "fusiones_dudosas.json")
    ambiguous_raw = json.load(open(ambiguous_path, encoding="utf-8")) if os.path.exists(ambiguous_path) else []
    by_id = {n["id"]: n for n in nodes}
    ambiguous = []
    for pair in ambiguous_raw:
        k1, k2 = pair["clave_1"], pair["clave_2"]
        n1, n2 = by_id.get(k1), by_id.get(k2)
        if not n1 or not n2:
            continue
        ambiguous.append({
            "id_1": k1, "nombre_1": n1["nombre_canonico"],
            "definicion_1": (n1["definiciones"][0]["texto"] if n1["definiciones"] else "")[:250],
            "id_2": k2, "nombre_2": n2["nombre_canonico"],
            "definicion_2": (n2["definiciones"][0]["texto"] if n2["definiciones"] else "")[:250],
        })

    relation_needs_review = {}
    for n in nodes:
        for r in n.get("relaciones_crudas", []):
            if r.get("revisar"):
                t = r["tipo_original"]
                relation_needs_review.setdefault(t, {
                    "tipo_original": t, "sujeto": n["nombre_canonico"],
                    "objeto": r["objeto_texto"], "n_ocurrencias": 0,
                })
                relation_needs_review[t]["n_ocurrencias"] += 1

    out = {
        "instrucciones": (
            "Fase 3 de consolidacion del grafo CerebroSSRN (trading cuantitativo). "
            "Los datos ya pasaron un pre-filtro local (normalizacion + fuzzy match). "
            "Tu trabajo es el juicio semantico que un script no puede hacer.\n\n"
            "TAREA 1 (nodos_top): revisa 'variantes_fusionadas' de cada nodo. La "
            "mayoria son fusiones correctas, pero puede haberse colado una fusion "
            "incorrecta de dos conceptos DISTINTOS agrupados por casualidad de "
            "escritura o pluralizacion. Si detectas una, emiti una decision "
            "'fusionar' que EXCLUYA esa variante (fusionando solo el resto) — "
            "en la practica esto casi nunca pasa con el umbral usado, pero "
            "revisalo.\n\n"
            "TAREA 2 (pares_ambiguos): cada par tiene nombres MUY parecidos por "
            "template (ej. 'mean reversion' vs 'mean version') pero con una "
            "palabra final distinta y no-parecida ortograficamente — el script "
            "los dejo sin fusionar A PROPOSITO porque no puede distinguir typo de "
            "concepto-opuesto-real (ej. 'adverse selection' vs 'favorable "
            "selection' NO son lo mismo). Mira las definiciones y decidi: "
            "'fusionar' (mismo concepto, dar 'canonico') o 'no_fusionar' (conceptos "
            "distintos, con motivo — especialmente ojo con pares antitéticos: "
            "momentum/mean reversion, informed/uninformed, etc.).\n\n"
            "TAREA 3 (tipos_relacion_sin_mapear): tipos que los extractores "
            "generaron fuera del schema cerrado de 12. Para cada uno: "
            "'mapear_relacion' a uno de los 12 (con invertir=true si el sentido "
            "sujeto/objeto queda al reves), o 'tipo_relacion_nuevo' si de verdad "
            "no encaja en ninguno."
        ),
        "schema_cerrado": ["EQUIVALE_A", "PARTE_DE", "USA", "MIDE", "PREDICE",
                           "CAUSA", "SE_OPONE_A", "MEJORA_A", "CONTRADICE_A",
                           "MITIGA", "APLICA_A", "REQUIERE"],
        "nodos_top": compact,
        "pares_ambiguos": ambiguous,
        "tipos_relacion_sin_mapear": list(relation_needs_review.values()),
        "formato_respuesta": FORMATO_RESPUESTA,
    }

    out_path = os.path.join(GRAFO_DIR, "paquete_revision_jueces.json")
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"Nodos top incluidos: {len(compact)} (de {len(nodes)} totales)")
    print(f"Pares ambiguos: {len(ambiguous)}")
    print(f"Tipos de relacion a decidir: {len(relation_needs_review)}")
    print(f"Paquete: {out_path} ({os.path.getsize(out_path)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
