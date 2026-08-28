# -*- coding: utf-8 -*-
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LOCAL_PARQUET = REPO / "data" / "nt8" / "6E" / "6E_09-26_ticks.parquet"


def pytest_collection_modifyitems(config, items):
    if LOCAL_PARQUET.exists():
        return
    skip = pytest.mark.skip(reason="requires local gitignored 6E parquet; not present in CI")
    for item in items:
        if item.name == "test_data_root_resuelve_data_gitignoreado_desde_una_worktree":
            item.add_marker(skip)
