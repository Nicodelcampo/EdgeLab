"""Contrato de entorno: versiones núcleo + consistencia base⊂full de los locks.
Fixtures sintéticos, sin rutas locales de máquina, sin red."""
import re
from pathlib import Path
import importlib.metadata as md
import pytest
from packaging.version import Version

REPO = Path(__file__).resolve().parents[2]
CONTRACT = {"numpy": "2.4.6", "pandas": "3.0.3", "numba": "0.66", "pyarrow": "25", "pydantic": "2.13"}


def test_core_versions_satisfy_contract():
    for pkg, floor in CONTRACT.items():
        v = Version(md.version(pkg))
        assert v >= Version(floor), f"{pkg} {v} < {floor}"


def test_bridge_importable():
    import duckdb  # noqa: F401
    import polars  # noqa: F401


def _lock_versions(path: Path):
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^ \\;]+)", line)
        if m:
            out[m.group(1).lower()] = m.group(2)
    return out


def test_lock_consistency_base_subset_of_full():
    base = REPO / "requirements" / "core-bridge-dev.lock"
    full = REPO / "requirements" / "full-research.lock"
    if not (base.exists() and full.exists()):
        pytest.skip("locks ausentes")
    b, f = _lock_versions(base), _lock_versions(full)
    shared = set(b) & set(f)
    diffs = {k: (b[k], f[k]) for k in shared if b[k] != f[k]}
    assert not diffs, f"divergencia de versiones base/full: {diffs}"
    assert set(b).issubset(set(f)), f"paquetes del base no presentes en full: {set(b) - set(f)}"
