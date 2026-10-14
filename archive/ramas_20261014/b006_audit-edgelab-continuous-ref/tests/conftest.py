"""Guards de entorno para la suite CI.

El repo declara: los tests que necesitan `data/` (gitignoreado) se skipean
solos. Estos cuatro tests de F1.1 no lo hacian y rompian CI en todo runner sin
el arbol local de datos. Se skipean aca, de forma explicita y enumerada, hasta
que el modulo/tests se hagan hermeticos (ver CYCLE-001 CI common-cause fix).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

_REQUIRES_LOCAL_DATA = {
    "tests/research/test_bigtrap2_distance_matched_null.py::test_data_root_resuelve_data_gitignoreado_desde_una_worktree",
    "tests/research/test_bigtrap2_distance_matched_null.py::test_f0_main_cli_solo_estructural_omite_claves_del_payload_y_del_stdout",
    "tests/research/test_bigtrap2_distance_matched_null.py::test_f22_smoke_archivo_implica_solo_estructural",
    "tests/research/test_bigtrap2_distance_matched_null.py::test_f22_gate_de_procedencia_aborta_si_arbol_sucio_o_head_se_mueve",
}


def _data_tree_available() -> bool:
    candidates = []
    env = os.environ.get("DATA_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(REPO / "data")
    for c in candidates:
        nt8 = c / "nt8"
        if nt8.is_dir() and any(nt8.rglob("*.parquet")):
            return True
    return False


def pytest_collection_modifyitems(items):
    if _data_tree_available():
        return
    skip = pytest.mark.skip(
        reason="requiere arbol data/ local (gitignoreado); ausente en este runner"
    )
    for item in items:
        if item.nodeid in _REQUIRES_LOCAL_DATA:
            item.add_marker(skip)
