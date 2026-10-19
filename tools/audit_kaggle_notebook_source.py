#!/usr/bin/env python3
"""Inspect a saved Kaggle get_notebook_info JSON; NEVER execute its source.

Static hints are not proof of a completed run, consumed data or economic bias.
Outputs contain hashes/line references, not private source or signed URLs.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path


def inspect_source(info):
    source = info["blob"]["source"]
    if not isinstance(source, str):
        raise ValueError("blob.source must be text")
    tree = ast.parse(source)
    env, constants, hints = {}, {}, {}

    def hint(label, node):
        hints.setdefault(label, []).append(node.lineno)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    if target.id in ("SPEC", "TICKS_BAR"):
                        constants[target.id] = node.value.value
                if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Attribute):
                    if ast.unparse(target.value) == "os.environ":
                        try:
                            key, value = ast.literal_eval(target.slice), ast.literal_eval(node.value)
                        except (ValueError, TypeError):
                            continue
                        if key in ("AVCL_INST", "AVCL_CONTRACTS", "EDGELAB_CODE_COMMIT", "EDGELAB_TREE", "PYTHONHASHSEED"):
                            env[key] = value
        if isinstance(node, ast.Call):
            func = ast.unparse(node.func)
            if func == "hash":
                hint("PROCESS_DEPENDENT_BUILTIN_HASH", node)
            if func == "ed.sessions":
                hint("CATALOG_SESSION_SELECTION_REQUIRES_VERSION_AND_POLICY_REVIEW", node)
            if func.endswith(".idxmax"):
                hint("SOURCE_CHOICE_BY_MAXIMUM_REQUIRES_LINEAGE_REVIEW", node)
            if func.endswith(".nan_to_num"):
                hint("MISSING_VALUE_SUBSTITUTION_REQUIRES_TRANSFORMATION_REVIEW", node)
            if func.endswith(".sort_values"):
                hint("SORTING_REQUIRES_TRANSFORMATION_REVIEW", node)
    meta = info.get("metadata", {})
    return {
        "schema": "edgelab_static_notebook_review_v1",
        "notebook_ref": meta.get("ref"), "observed_notebook_version": meta.get("current_version_number"),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "declared_environment": env, "declared_constants": constants,
        "static_hints": {k: sorted(set(v)) for k, v in sorted(hints.items())},
        "attached_datasets_are_not_consumed_inputs": True,
        "output_run_binding_verified": False,
        "status": "REQUIRES_RUN_LINEAGE_REVIEW",
        "research_authorized": False, "bias_adjudicated": False,
        "scope": "current_source_static_inspection_only",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("info", type=Path)
    args = parser.parse_args(argv)
    try:
        result = inspect_source(json.loads(args.info.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as exc:
        print(json.dumps({"status": "REQUIRES_RUN_LINEAGE_REVIEW", "error_type": type(exc).__name__,
                          "research_authorized": False}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0  # Static inspection succeeded, NOT research permission.


if __name__ == "__main__":
    raise SystemExit(main())