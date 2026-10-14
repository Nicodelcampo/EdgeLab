# -*- coding: utf-8 -*-
"""ZAMR-1 Notebook 01 — runner dormido hasta que M0 permita ticks en terceros.

Con la decisión vigente NO_UPLOAD este notebook debe fallar antes de buscar o
leer Parquet. Z1 se construye localmente; un override de riesgo no es licencia.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WORKING = Path(os.environ.get("EDGELAB_KAGGLE_WORKING", "/kaggle/working"))
SEARCH_ROOTS = [
    Path(os.environ["EDGELAB_REPO_ROOT"]) if os.environ.get("EDGELAB_REPO_ROOT") else None,
    Path("/kaggle/input"),
    Path("/kaggle/working"),
    Path("."),
]


def find_repo_root() -> Path:
    roots = [path for path in SEARCH_ROOTS if path and path.exists()]
    for root in roots:
        matches = list(root.rglob("edgelab/research/zamr1/z1_builder.py"))
        if len(matches) == 1:
            return matches[0].parents[3]
        if len(matches) > 1:
            raise RuntimeError("múltiples checkouts EdgeLab: %s" % matches)
    raise RuntimeError("no se encontró edgelab/research/zamr1/z1_builder.py")


def find_data_root(repo_root: Path) -> Path:
    explicit = os.environ.get("EDGELAB_DATA_ROOT")
    if explicit:
        path = Path(explicit)
        if not path.is_dir():
            raise RuntimeError("EDGELAB_DATA_ROOT no existe: %s" % path)
        return path
    names = {"6E_06-26_ticks.parquet", "6E_09-26_ticks.parquet"}
    hits = []
    for root in (Path("/kaggle/input"), repo_root / "data" / "nt8" / "6E"):
        if not root.exists():
            continue
        found = {path.name: path.parent for path in root.rglob("*.parquet") if path.name in names}
        if names <= set(found):
            parents = {found[name] for name in names}
            if len(parents) != 1:
                raise RuntimeError("los Parquet Z1 no están en el mismo directorio")
            hits.append(parents.pop())
    if len(hits) != 1:
        raise RuntimeError("se esperaba un data-root con ambos Parquet Z1; hallados=%s" % hits)
    return hits[0]


def main() -> int:
    repo = find_repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    plan_path = repo / "specs/zamr1_z1_pilot_plan_2026-08-12.json"
    plan = json.loads(plan_path.read_text("utf-8"))

    # Debe ejecutarse antes de buscar los archivos de mercado.
    from edgelab.research.zamr1.upload_gate import require_raw_third_party_upload
    require_raw_third_party_upload(plan)

    os.environ.setdefault(
        "EDGELAB_CODE_COMMIT",
        (repo / "CODE_COMMIT").read_text("utf-8").strip() if (repo / "CODE_COMMIT").is_file() else "",
    )
    os.environ.setdefault("EDGELAB_CODE_DIRTY", "false")
    from edgelab.research.zamr1.z1_builder import build

    data_root = find_data_root(repo)
    result = build(plan_path, data_root, WORKING / "z1", repo)
    print(json.dumps(result, indent=2))
    if not result.get("passed"):
        print("FAIL — no continuar")
        return 1
    print("PASS — Z1 estructural construido; no interpreta alpha ni P&L")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
