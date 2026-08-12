# -*- coding: utf-8 -*-
"""DAG fail-closed de parámetros para ZAMR-1.

Canonicaliza sólo configuraciones semánticamente activas. Una combinación
inválida no recibe ``param_set_id`` y por lo tanto no puede entrar al ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Dict, Mapping

from edgelab.bridge.indicators import avolcellpoi2, bigtrap2


@dataclass(frozen=True)
class ParamIssue:
    code: str
    parameter: str
    detail: str


_MODULES = {
    "BigTrap2": bigtrap2,
    "aVolCellPOI2": avolcellpoi2,
}

_FAMILIES = {
    "BigTrap2": {
        "footprint": {"ticks_per_row"},
        "detection": {
            "imbalance_mode", "trap_volume_source", "imbalance_ratio",
            "use_wick_filter", "wick_zone_pct", "min_delta_filter",
        },
        "selection": {"min_export_volume", "min_trap_volume"},
        "lifecycle": {"invalidation_mode", "max_age_bars", "max_touches"},
    },
    "aVolCellPOI2": {
        "profile": {
            "bucket_anchor", "time_bucket_minutes", "lookback_sessions",
            "profile_weighting", "min_sessions", "min_cell_samples",
        },
        "source": {"detection_source"},
        "threshold": {
            "detection_method", "export_floor_percentile",
            "detection_percentile", "robust_z_threshold", "min_absolute_volume",
        },
        "geometry": {"merge_gap_ticks", "min_zone_cells"},
        "lifecycle": {"invalidation_mode", "max_age_bars", "max_touches"},
    },
}


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "bool":
        return type(value) is bool
    if expected == "int":
        return type(value) is int
    if expected == "float":
        return type(value) in (int, float) and type(value) is not bool
    if expected == "str":
        return type(value) is str
    return False


def _generic_issues(indicator: str, overrides: Mapping[str, Any]) -> list[ParamIssue]:
    if indicator not in _MODULES:
        return [ParamIssue("UNKNOWN_INDICATOR", "indicator", indicator)]
    spec = _MODULES[indicator].PARAM_SPEC
    issues: list[ParamIssue] = []
    for name, value in overrides.items():
        if name not in spec:
            issues.append(ParamIssue("UNKNOWN_PARAMETER", name, "no existe en PARAM_SPEC"))
            continue
        rule = spec[name]
        if rule.get("class") == "forbidden" or rule.get("optimizable") is False:
            issues.append(ParamIssue("FORBIDDEN_PARAMETER", name, str(rule.get("reason", "prohibido"))))
            continue
        expected = rule.get("type")
        if expected and not _type_matches(value, expected):
            issues.append(ParamIssue("INVALID_TYPE", name, "esperado %s" % expected))
            continue
        if "choices" in rule and value not in rule["choices"]:
            issues.append(ParamIssue("INVALID_CHOICE", name, "fuera de %r" % rule["choices"]))
        if "min" in rule and value < rule["min"]:
            issues.append(ParamIssue("BELOW_MIN", name, "%r < %r" % (value, rule["min"])))
        if "max" in rule and value > rule["max"]:
            issues.append(ParamIssue("ABOVE_MAX", name, "%r > %r" % (value, rule["max"])))
    return issues


def validate_param_set(indicator: str, overrides: Mapping[str, Any]) -> list[ParamIssue]:
    """Devuelve todas las violaciones conocidas; lista vacía significa PASS."""
    issues = _generic_issues(indicator, overrides)
    if indicator not in _MODULES:
        return issues
    # Las restricciones cruzadas hacen operaciones numéricas. Si un tipo es
    # inválido, no intentamos continuar y convertir un FAIL esperado en crash.
    if any(item.code == "INVALID_TYPE" for item in issues):
        return issues

    merged: Dict[str, Any] = dict(_MODULES[indicator].DEFAULTS)
    merged.update(overrides)

    if indicator == "BigTrap2":
        if merged["min_export_volume"] > merged["min_trap_volume"]:
            issues.append(ParamIssue(
                "EXPORT_FLOOR_TOO_HIGH", "min_export_volume",
                "debe ser <= min_trap_volume para permitir el barrido offline",
            ))
        if not merged["use_wick_filter"] and "wick_zone_pct" in overrides:
            if overrides["wick_zone_pct"] != _MODULES[indicator].DEFAULTS["wick_zone_pct"]:
                issues.append(ParamIssue(
                    "INACTIVE_PARAMETER_VARIED", "wick_zone_pct",
                    "use_wick_filter=False vuelve inactivo wick_zone_pct",
                ))

    if indicator == "aVolCellPOI2":
        method = merged["detection_method"]
        if merged["min_sessions"] > merged["lookback_sessions"]:
            issues.append(ParamIssue(
                "IMPOSSIBLE_PROFILE_GATE", "min_sessions",
                "min_sessions no puede superar lookback_sessions",
            ))
        if method == "Quantile":
            if "robust_z_threshold" in overrides and overrides["robust_z_threshold"] != _MODULES[indicator].DEFAULTS["robust_z_threshold"]:
                issues.append(ParamIssue(
                    "INACTIVE_PARAMETER_VARIED", "robust_z_threshold",
                    "RobustZ está inactivo cuando detection_method=Quantile",
                ))
            p = float(merged["detection_percentile"])
            if merged["export_floor_percentile"] > p:
                issues.append(ParamIssue(
                    "EXPORT_FLOOR_ABOVE_DETECTION", "export_floor_percentile",
                    "debe ser <= detection_percentile",
                ))
            # Forma algebraicamente equivalente pero estable para percentiles
            # decimales registrados: 10/(1-p/100) = 1000/(100-p).
            required = math.ceil(1000.0 / (100.0 - p)) if p < 100.0 else math.inf
            if merged["min_cell_samples"] < required:
                issues.append(ParamIssue(
                    "INSUFFICIENT_TAIL_SUPPORT", "min_cell_samples",
                    "requiere >= %s para ~10 observaciones sobre p=%s" % (required, p),
                ))
        elif method == "RobustZ":
            if "detection_percentile" in overrides and overrides["detection_percentile"] != _MODULES[indicator].DEFAULTS["detection_percentile"]:
                issues.append(ParamIssue(
                    "INACTIVE_PARAMETER_VARIED", "detection_percentile",
                    "Quantile está inactivo cuando detection_method=RobustZ",
                ))
        else:  # también queda cubierto por choices; se conserva fail-closed
            issues.append(ParamIssue("UNKNOWN_METHOD", "detection_method", str(method)))
    return issues


def canonical_param_set(indicator: str, overrides: Mapping[str, Any]) -> Dict[str, Any]:
    issues = validate_param_set(indicator, overrides)
    if issues:
        detail = "; ".join("%s:%s" % (x.code, x.parameter) for x in issues)
        raise ValueError("param set inválido: " + detail)
    merged = dict(_MODULES[indicator].DEFAULTS)
    merged.update(overrides)
    return {
        "indicator": indicator,
        "params": {key: merged[key] for key in sorted(merged)},
    }


def param_set_id(indicator: str, overrides: Mapping[str, Any]) -> str:
    canonical = canonical_param_set(indicator, overrides)
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_single_family(
    indicator: str,
    overrides: Mapping[str, Any],
    allowed_family: str,
) -> list[ParamIssue]:
    """Impide cruzar familias en una etapa declarada de barrido unifamiliar."""
    issues = validate_param_set(indicator, overrides)
    if indicator not in _MODULES:
        return issues
    families = _FAMILIES[indicator]
    if allowed_family not in families:
        issues.append(ParamIssue("UNKNOWN_FAMILY", "family", allowed_family))
        return issues
    defaults = _MODULES[indicator].DEFAULTS
    changed = {key for key, value in overrides.items() if key in defaults and value != defaults[key]}
    outside = sorted(changed - families[allowed_family])
    for name in outside:
        issues.append(ParamIssue(
            "CROSS_FAMILY_VARIATION", name,
            "no pertenece a la familia %s" % allowed_family,
        ))
    return issues
