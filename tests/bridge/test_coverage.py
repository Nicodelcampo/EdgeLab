"""Contabilidad de cobertura de ramas (F7)."""
from edgelab.bridge import coverage


def test_branches_of_all_kernels():
    for ind in ("Gaps2", "VolTicksPOC2", "BigTrap2", "HFTZones2", "aVolCellPOI2"):
        br = coverage.branches_of(ind)
        assert br and all(isinstance(ps, list) and ps for ps in br.values())


def test_config_branches_includes_gated_branch():
    br = coverage.config_branches("BigTrap2", {"imbalance_ratio": 2.0})
    assert "imbalance_detection" in br and "row_anchor" in br


def test_is_covered_rule():
    # config default de Gaps2; cubierta solo si TODAS sus ramas están cubiertas
    all_br = set(coverage.branches_of("Gaps2"))
    assert coverage.is_covered("Gaps2", {}, all_br)
    assert not coverage.is_covered("Gaps2", {}, all_br - {"gap_detection"})


def test_config_branches_rejects_invalid():
    import pytest
    with pytest.raises((KeyError, ValueError)):
        coverage.config_branches("Gaps2", {"nope": 1})
