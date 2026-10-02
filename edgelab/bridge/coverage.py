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


# --------------------------------------------------------------------------- #
# Propagación de parity_covered (F7c)
# Semántica pre-declarada en docs/nt8_indicator_parity_contract.md §8.
# --------------------------------------------------------------------------- #
COVERAGE_RULE_VERSION = "1.0"

# Lista blanca FAIL-CLOSED (§8.3): lo que no está acá bloquea la cobertura.
# Cada entrada exige justificación con código del matcher en el contrato §8.3.1.
COVERAGE_NEUTRAL = {
    "Gaps2": {
        # solo alimenta g["display"], que el matcher nunca lee (§8.3.1)
        "params": frozenset({"min_gap_ticks"}),
        # el matching usa unix_ms absoluto; chart_tz solo formatea `ts` (§8.3.1)
        "axes": frozenset({"chart_tz"}),
    },
}

# Campos de identidad que NUNCA se cruzan (§8.2 puntos 3-6).
_HARD_IDENTITY = ("indicator", "kernel_id", "instrument", "bar_key")


def _neutral(indicator):
    e = COVERAGE_NEUTRAL.get(indicator, {})
    return e.get("params", frozenset()), e.get("axes", frozenset())


def coverage_blockers(source, target):
    """Razones por las que `source` NO cubre a `target` (listas de strings).
    Vacía ⇒ source cubre a target bajo §8.2. `source`/`target` son manifests
    (dicts) del store. Fail-closed: ante cualquier campo ausente, bloquea."""
    b = []
    if source.get("parity_state") != "parity_exact":
        b.append("source no es parity_exact (es %s)" % source.get("parity_state"))
    if source.get("run_id") == target.get("run_id"):
        b.append("autootorgamiento: source y target son la misma partición")
    for k in _HARD_IDENTITY:
        sv, tv = source.get(k), target.get(k)
        if sv is None or tv is None or sv != tv:
            b.append("%s difiere (source=%s target=%s)" % (k, sv, tv))
    ind = target.get("indicator")
    neutral_params, neutral_axes = _neutral(ind)
    if "chart_tz" not in neutral_axes and source.get("chart_tz") != target.get("chart_tz"):
        b.append("chart_tz difiere (source=%s target=%s) y no es eje neutral para %s"
                 % (source.get("chart_tz"), target.get("chart_tz"), ind))
    sp, tp = source.get("params") or {}, target.get("params") or {}
    for key in sorted(set(sp) | set(tp)):
        if sp.get(key) == tp.get(key):
            continue
        if key in neutral_params:
            continue
        b.append("param '%s' difiere (source=%r target=%r) y no es coverage-neutral"
                 % (key, sp.get(key), tp.get(key)))
    return b


def _neutral_params_used(source, target):
    sp, tp = source.get("params") or {}, target.get("params") or {}
    np_, _ = _neutral(target.get("indicator"))
    return sorted(k for k in (set(sp) | set(tp))
                  if sp.get(k) != tp.get(k) and k in np_)


def _coverage_block(source, target, now_utc):
    """Bloque de evidencia auditable (§8.6)."""
    par = source.get("parity") or {}
    return dict(
        source_config_id=source.get("config_id"), source_run_id=source.get("run_id"),
        source_contract=source.get("contract"),
        oracle_path=par.get("oracle_path"), oracle_sha256=par.get("oracle_sha256"),
        rule_version=COVERAGE_RULE_VERSION,
        neutral_params_used=_neutral_params_used(source, target),
        granted_utc=now_utc)


def propagate_coverage(root, *, dry_run=False, now_utc=None):
    """Propaga parity_covered en el store (IDEMPOTENTE, §8).

    - Degradación (§8.5): si algún run con el mismo kernel_id que la fuente está
      parity_failed, las coberturas que otorgó pasan a parity_under_review.
    - Otorga parity_covered a las particiones parity_pending que tengan una
      fuente parity_exact elegible (§8.2). No transitiva: la fuente debe ser
      parity_exact, nunca parity_covered.
    - Re-ejecutar sin cambios en el store no produce escrituras (idempotencia).

    Devuelve dict(granted=[...], under_review=[...], unchanged=[...], skipped=n).
    """
    import json as _json
    from datetime import datetime, timezone
    from . import store

    stamp = now_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = store.catalog_df(root)
    mans = {r["run_id"]: _json.loads(r["manifest_json"]) for r in rows}
    sources = [m for m in mans.values() if m.get("parity_state") == "parity_exact"]
    tainted = {m.get("kernel_id") for m in mans.values()
               if m.get("parity_state") == "parity_failed"}

    granted, under_review, unchanged = [], [], []
    skipped = 0
    for rid, man in sorted(mans.items()):
        state = man.get("parity_state")

        # 1) degradación de coberturas ya otorgadas por un kernel_id contaminado
        if state == "parity_covered":
            cov = man.get("coverage") or {}
            src = mans.get(cov.get("source_run_id"))
            src_kid = (src or {}).get("kernel_id", man.get("kernel_id"))
            if src_kid in tainted:
                if not dry_run:
                    store.set_state(root, rid, parity_state="parity_under_review")
                under_review.append(rid)
            else:
                unchanged.append(rid)
            continue

        if state != "parity_pending":
            skipped += 1                    # exact / failed / under_review: no se tocan
            continue

        # 2) otorgar cobertura si existe una fuente elegible
        elegible = None
        for s in sources:
            if s.get("kernel_id") in tainted:
                continue                    # no se otorga desde un kernel contaminado
            if not coverage_blockers(s, man):
                elegible = s
                break
        if elegible is None:
            unchanged.append(rid)
            continue
        if not dry_run:
            store.set_state(root, rid, parity_state="parity_covered",
                            coverage=_coverage_block(elegible, man, stamp))
        granted.append(rid)

    return dict(granted=granted, under_review=under_review,
                unchanged=unchanged, skipped=skipped)
