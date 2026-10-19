from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SemanticDebtResolutionError(ValueError):
    """The graph cannot be resolved without losing or fabricating provenance."""


CANONICAL_RELATIONS = {
    "EQUIVALE_A", "PARTE_DE", "USA", "MIDE", "PREDICE", "CAUSA",
    "SE_OPONE_A", "MEJORA_A", "CONTRADICE_A", "MITIGA", "APLICA_A", "REQUIERE",
}

ADJUDICATED_TYPE_OVERRIDES: dict[str, tuple[str, bool]] = {
    "CAUSADO_POR": ("CAUSA", True),
    "AUMENTA": ("CAUSA", False),
    "AFECTA": ("CAUSA", False),
    "EXCITA": ("CAUSA", False),
    "INFLUENCIADO_POR": ("CAUSA", True),
    "DISMINUYE": ("SE_OPONE_A", False),
    "LIMITA": ("SE_OPONE_A", False),
    "APROXIMA": ("EQUIVALE_A", False),
    "ES_UN": ("PARTE_DE", False),
    "EVALUA": ("MIDE", False),
    "EVALUADO_POR": ("MIDE", True),
    "MEJORADO_POR": ("MEJORA_A", True),
}


@dataclass(frozen=True)
class ResolutionSummary:
    original_nodes: int
    original_edges: int
    unresolved_targets_input: int
    target_nodes_created: int
    relation_mentions_recovered: int
    resolved_edges_added: int
    unadjudicated_types_preserved: int
    unresolved_targets_output: int
    final_nodes: int
    final_edges: int
    graph_sha256: str
    decisions_sha256: str


def normalize_key(value: Any) -> str:
    """Match the original CerebroSSRN norm_key exactly."""
    text = "".join(
        char for char in unicodedata.normalize("NFKD", str(value))
        if not unicodedata.combining(char)
    ).lower().strip()
    text = re.sub(r"^(the|a|an)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"[\s_-]+", " ", text).strip()
    words = []
    for word in text.split():
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        words.append(word)
    return " ".join(words)


def canonical_json_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _confidence(n_docs: int) -> str:
    return "alta" if n_docs >= 3 else ("media" if n_docs == 2 else "baja")


def resolve_semantic_debt(
    graph: dict[str, Any],
    unresolved: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], ResolutionSummary]:
    """Resolve every missing destination without fuzzy-merging distinct concepts."""
    original_nodes = list(graph.get("nodos", []))
    original_edges = list(graph.get("aristas", []))
    if not original_nodes:
        raise SemanticDebtResolutionError("Graph contains no nodes")

    existing_ids = {node["id"] for node in original_nodes}
    unresolved_by_key = {normalize_key(item["objeto"]): item for item in unresolved}
    if "" in unresolved_by_key:
        raise SemanticDebtResolutionError("An unresolved destination normalizes to an empty key")
    collisions = sorted(set(unresolved_by_key) & existing_ids)
    if collisions:
        raise SemanticDebtResolutionError(f"Unresolved keys already exist as nodes: {collisions[:10]}")

    raw_by_target: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for node in original_nodes:
        for relation in node.get("relaciones_crudas", []):
            target = normalize_key(relation.get("objeto_texto", ""))
            if target in unresolved_by_key:
                raw_by_target[target].append((node["id"], relation))

    missing_evidence = sorted(set(unresolved_by_key) - set(raw_by_target))
    if missing_evidence:
        raise SemanticDebtResolutionError(
            f"Unresolved targets without raw relation evidence: {missing_evidence[:10]}"
        )

    decisions: list[dict[str, Any]] = []
    new_nodes: list[dict[str, Any]] = []
    for target in sorted(unresolved_by_key):
        item = unresolved_by_key[target]
        evidence = raw_by_target[target]
        doc_ids = sorted({int(rel["doc_id"]) for _, rel in evidence})
        raw_names = sorted({str(rel.get("objeto_texto", "")).strip() for _, rel in evidence if str(rel.get("objeto_texto", "")).strip()})
        relation_types = sorted({str(rel.get("tipo_original") or rel.get("tipo") or "").strip().upper() for _, rel in evidence})
        new_nodes.append({
            "id": target,
            "nombre_canonico": str(item["objeto"]).strip(),
            "tipo": "concepto",
            "nombres_vistos": raw_names or [str(item["objeto"]).strip()],
            "menciones": len(evidence),
            "doc_frecuencia": len(doc_ids),
            "doc_ids": doc_ids,
            "definiciones": [],
            "citas": [],
            "relaciones_crudas": [],
            "semantic_status": "RESOLVED_AS_DISTINCT_TARGET_NODE",
            "type_status": "TARGET_ONLY_UNCLASSIFIED",
            "authority_status": "LLM_EXTRACTED_CONCEPT",
        })
        decisions.append({
            "object": item["objeto"],
            "target_node_id": target,
            "resolution": "CREATE_EVIDENCE_BACKED_TARGET_NODE",
            "reason": "No adjudicated exact node existed; preserving a distinct concept avoids a fabricated fuzzy merge.",
            "mentions": len(evidence),
            "doc_ids": doc_ids,
            "relation_types": relation_types,
            "authority_status": "LLM_EXTRACTED_CONCEPT",
        })

    edge_acc: dict[tuple[str, str, str], dict[str, Any]] = {}
    for edge in original_edges:
        key = (edge["origen"], edge["destino"], edge["tipo"])
        edge_acc[key] = dict(edge)
        edge_acc[key]["doc_ids"] = sorted(set(edge.get("doc_ids", [])))
        edge_acc[key].setdefault("relation_status", "CANONICAL")
        edge_acc[key].setdefault("authority_status", "LLM_EXTRACTED_CONCEPT")

    relation_mentions = 0
    unadjudicated_types: set[str] = set()
    added_keys: set[tuple[str, str, str]] = set()
    for target in sorted(raw_by_target):
        for origin, relation in raw_by_target[target]:
            relation_mentions += 1
            original_type = str(relation.get("tipo_original") or relation.get("tipo") or "").strip().upper()
            mapped_type = str(relation.get("tipo") or original_type).strip().upper()
            invert = False
            relation_status = "CANONICAL"
            if relation.get("revisar"):
                if original_type in ADJUDICATED_TYPE_OVERRIDES:
                    mapped_type, invert = ADJUDICATED_TYPE_OVERRIDES[original_type]
                    relation_status = "ADJUDICATED_OVERRIDE"
                else:
                    mapped_type = original_type
                    relation_status = "EXTRACTED_TYPE_UNADJUDICATED"
                    unadjudicated_types.add(original_type)
            source, destination = (target, origin) if invert else (origin, target)
            key = (source, destination, mapped_type)
            doc_id = int(relation["doc_id"])
            if key not in edge_acc:
                edge_acc[key] = {
                    "origen": source,
                    "destino": destination,
                    "tipo": mapped_type,
                    "n_docs": 0,
                    "doc_ids": [],
                    "confianza": "baja",
                    "relation_status": relation_status,
                    "authority_status": "LLM_EXTRACTED_CONCEPT",
                    "raw_mentions": 0,
                }
                added_keys.add(key)
            acc = edge_acc[key]
            acc["doc_ids"] = sorted(set(acc.get("doc_ids", [])) | {doc_id})
            acc["n_docs"] = len(acc["doc_ids"])
            acc["confianza"] = _confidence(acc["n_docs"])
            acc["raw_mentions"] = int(acc.get("raw_mentions", 0)) + 1
            if acc.get("relation_status") != relation_status:
                acc["relation_status"] = "MIXED_PROVENANCE"

    nodes = sorted(original_nodes + new_nodes, key=lambda node: (-int(node.get("doc_frecuencia", 0)), -int(node.get("menciones", 0)), node["id"]))
    edges = sorted(edge_acc.values(), key=lambda edge: (-int(edge.get("n_docs", 0)), edge["origen"], edge["destino"], edge["tipo"]))
    all_ids = {node["id"] for node in nodes}
    still_missing = sorted({edge["destino"] for edge in edges if edge["destino"] not in all_ids} | {edge["origen"] for edge in edges if edge["origen"] not in all_ids})
    if still_missing:
        raise SemanticDebtResolutionError(f"Resolved graph still has missing endpoints: {still_missing[:10]}")

    resolved_graph = {
        "nodos": nodes,
        "aristas": edges,
        "semantic_resolution": {
            "policy": "EXACT_OR_DISTINCT_TARGET_ONLY_NO_FUZZY_MERGE",
            "unresolved_targets_input": len(unresolved_by_key),
            "unresolved_targets_output": 0,
            "authority_status": "LLM_EXTRACTED_CONCEPT",
            "promotion_allowed": False,
        },
    }
    decisions_hash = canonical_json_hash(decisions)
    graph_hash = canonical_json_hash(resolved_graph)
    summary = ResolutionSummary(
        original_nodes=len(original_nodes),
        original_edges=len(original_edges),
        unresolved_targets_input=len(unresolved_by_key),
        target_nodes_created=len(new_nodes),
        relation_mentions_recovered=relation_mentions,
        resolved_edges_added=len(added_keys),
        unadjudicated_types_preserved=len(unadjudicated_types),
        unresolved_targets_output=0,
        final_nodes=len(nodes),
        final_edges=len(edges),
        graph_sha256=graph_hash,
        decisions_sha256=decisions_hash,
    )
    return resolved_graph, decisions, summary


def resolve_corpus_graph(corpus_root: str | Path, output_dir: str | Path) -> ResolutionSummary:
    root = Path(corpus_root)
    out = Path(output_dir)
    graph_path = root / "grafo" / "grafo_final.json"
    unresolved_path = root / "grafo" / "relaciones_sin_destino.json"
    if not graph_path.is_file() or not unresolved_path.is_file():
        raise SemanticDebtResolutionError("Missing grafo_final.json or relaciones_sin_destino.json")
    graph = json.loads(graph_path.read_text(encoding="utf-8-sig"))
    unresolved = json.loads(unresolved_path.read_text(encoding="utf-8-sig"))
    resolved, decisions, summary = resolve_semantic_debt(graph, unresolved)
    out.mkdir(parents=True, exist_ok=True)
    (out / "grafo_resuelto.json").write_text(json.dumps(resolved, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "resolucion_deuda_semantica.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "relaciones_sin_destino.json").write_text("[]\n", encoding="utf-8")
    (out / "resumen_resolucion.json").write_text(json.dumps(summary.__dict__, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
