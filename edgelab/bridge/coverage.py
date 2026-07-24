"""Cobertura de paridad por ramas (F7).

Cada parámetro de PARAM_SPEC declara las `branches` (ramas de código) que activa.
Un oráculo NT8 PASS "cubre" las ramas que su config ejercita. Una config recibe
el eje de paridad `parity_covered` SOLO cuando TODAS las ramas que activa están
cubiertas por oráculos PASS (aunque esa config exacta no tenga oráculo propio);
`parity_exact` exige el oráculo propio de esa config.

Este módulo es la contabilidad de ramas; el pre-registro de los oráculos y las
matrices viven en docs/parity_coverage/ y docs/nt8_indicator_parity_contract.md.
"""
from __future__ import annotations

from .identity import ANALYTIC_CLASSES, canonicalize_params


def _spec(indicator):
    from .indicators import REGISTRY
    if indicator not in REGISTRY:
        raise KeyError("indicador desconocido: %s" % indicator)
    return getattr(REGISTRY[indicator], "PARAM_SPEC")


def branches_of(indicator: str) -> dict:
    """{rama: [params que la activan]} para las clases analíticas del kernel."""
    out = {}
    for p, meta in _spec(indicator).items():
        if meta.get("class") not in ANALYTIC_CLASSES:
            continue
        for b in meta.get("branches", []):
            out.setdefault(b, []).append(p)
    return {b: sorted(ps) for b, ps in out.items()}


def config_branches(indicator: str, params: dict) -> set:
    """Ramas que una config activa. Toda config ejercita las ramas de todos sus
    parámetros analíticos (materializados): recorrer una config con defaults ya
    ejercita cada rama. Las variantes discretas (p.ej. imbalance_mode=SameLevel)
    activan la MISMA rama con otro camino; la cobertura fina por variante se
    documenta en la matriz, no se infiere acá."""
    canon = canonicalize_params(indicator, params)     # valida + materializa
    br = set()
    spec = _spec(indicator)
    for p in canon:
        for b in spec[p].get("branches", []):
            br.add(b)
    return br


def is_covered(indicator: str, params: dict, covered_branches) -> bool:
    """True si TODAS las ramas que la config activa están en `covered_branches`
    (el conjunto de ramas cubiertas por oráculos PASS). Base de parity_covered."""
    return config_branches(indicator, params).issubset(set(covered_branches))
