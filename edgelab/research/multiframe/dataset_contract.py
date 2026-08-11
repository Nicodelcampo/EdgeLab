# -*- coding: utf-8 -*-
"""Validador fail-closed del contrato de datos multiframe.

Contrato: specs/bigtrap2_multiframe_ml_dataset_contract_v1.json
Auditoría: docs/research/BIGTRAP2_MULTIFRAME_ML_AUDIT_OPUS_2026-08-11.md

Principios:

1. Fail-closed. Una comprobación que no puede ejecutarse cuenta como FAIL,
   nunca como PASS silencioso.
2. Funciones puras sobre DataFrames, para poder testearlas con datos
   sintéticos de verdad conocida sin tocar el disco ni el dataset real.
3. No se leen outcomes ni P&L. Los targets sólo se inspeccionan para
   verificar causalidad y horizonte, nunca para estimar efecto.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

CONTRACT_SCHEMA_VERSION = "bigtrap2_multiframe_ml_dataset_contract_v1"

FORBIDDEN_FEATURE_PREFIXES = ("target__", "y_", "future_", "outcome_")
ALLOWED_FOLD_ROLES = ("train", "test", "purged", "embargoed", "excluded")


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    offenders: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": bool(self.passed),
            "detail": self.detail,
            "offenders": self.offenders[:20],
            "offender_count": len(self.offenders),
        }


@dataclass
class ValidationReport:
    checks: List[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> "ValidationReport":
        self.checks.append(result)
        return self

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)

    @property
    def failures(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_schema_version": CONTRACT_SCHEMA_VERSION,
            "passed": self.passed,
            "n_checks": len(self.checks),
            "n_failures": len(self.failures),
            "checks": [c.to_dict() for c in self.checks],
        }


def _columns(df: Any) -> List[str]:
    try:
        return list(df.columns)
    except Exception:  # pragma: no cover - defensivo
        raise TypeError("se esperaba un DataFrame con atributo .columns")


def check_required_columns(df: Any, required: Sequence[str], table: str) -> CheckResult:
    """Todas las columnas obligatorias deben existir. Faltar una es FAIL."""
    present = set(_columns(df))
    missing = [c for c in required if c not in present]
    return CheckResult(
        name="required_columns[%s]" % table,
        passed=not missing,
        detail="faltan %d columnas obligatorias" % len(missing),
        offenders=missing,
    )


def check_primary_key_unique(df: Any, key: Sequence[str], table: str) -> CheckResult:
    """La clave primaria declarada debe ser única. Duplicados son FAIL."""
    cols = set(_columns(df))
    missing = [c for c in key if c not in cols]
    if missing:
        return CheckResult(
            name="primary_key_unique[%s]" % table,
            passed=False,
            detail="no se puede verificar: faltan columnas de clave",
            offenders=missing,
        )
    dup_mask = df.duplicated(subset=list(key), keep=False)
    n_dup = int(dup_mask.sum())
    offenders = []
    if n_dup:
        offenders = df.loc[dup_mask, list(key)].head(20).to_dict("records")
    return CheckResult(
        name="primary_key_unique[%s]" % table,
        passed=n_dup == 0,
        detail="%d filas con clave duplicada" % n_dup,
        offenders=offenders,
    )


def check_causality(windows: Any, targets: Any) -> CheckResult:
    """target_start_ns debe ser estrictamente posterior al cutoff.

    No se permite igualdad: una etiqueta que empieza exactamente en el cutoff
    puede incorporar el propio tick de decisión.
    """
    needed_w = {"session_key", "cutoff_ns", "window_spec_id"}
    needed_t = needed_w | {"target_start_ns", "target_end_ns"}
    if not needed_w.issubset(set(_columns(windows))) or not needed_t.issubset(set(_columns(targets))):
        return CheckResult(
            name="causality_target_after_cutoff",
            passed=False,
            detail="no se puede verificar: faltan columnas de cutoff/target",
        )
    merged = targets.merge(
        windows[["session_key", "cutoff_ns", "window_spec_id"]],
        on=["session_key", "cutoff_ns", "window_spec_id"],
        how="left",
        indicator=True,
    )
    orphan = int((merged["_merge"] != "both").sum())
    bad_start = int((merged["target_start_ns"] <= merged["cutoff_ns"]).sum())
    bad_end = int((merged["target_end_ns"] <= merged["target_start_ns"]).sum())
    total = orphan + bad_start + bad_end
    return CheckResult(
        name="causality_target_after_cutoff",
        passed=total == 0,
        detail=(
            "targets huérfanos=%d, target_start<=cutoff=%d, target_end<=target_start=%d"
            % (orphan, bad_start, bad_end)
        ),
    )


def check_event_availability(events: Any, cutoff_ns: int) -> CheckResult:
    """Ningún evento usado en una ventana puede estar disponible después del
    cutoff, ni provenir de una barra que aún no había cerrado."""
    cols = set(_columns(events))
    if not {"available_at_ns", "bar_end_ns"}.issubset(cols):
        return CheckResult(
            name="event_availability",
            passed=False,
            detail="no se puede verificar: faltan available_at_ns/bar_end_ns",
        )
    late_avail = int((events["available_at_ns"] > cutoff_ns).sum())
    open_bar = int((events["bar_end_ns"] > cutoff_ns).sum())
    return CheckResult(
        name="event_availability",
        passed=(late_avail + open_bar) == 0,
        detail="available_at>cutoff=%d, bar_end>cutoff=%d" % (late_avail, open_bar),
    )


def check_firewall(df: Any, time_column: str, max_allowed_ns: int, table: str) -> CheckResult:
    """Ninguna fila puede caer dentro del holdout."""
    if time_column not in set(_columns(df)):
        return CheckResult(
            name="firewall[%s]" % table,
            passed=False,
            detail="no se puede verificar: falta %s" % time_column,
        )
    violations = int((df[time_column] >= max_allowed_ns).sum())
    return CheckResult(
        name="firewall[%s]" % table,
        passed=violations == 0,
        detail="%d filas en o después del inicio del holdout" % violations,
    )


def check_fold_roles(folds: Any, level: str = "outer") -> CheckResult:
    """Una sesión no puede ser train y test en el mismo fold, todo rol debe ser
    válido y cada fold necesita al menos una sesión de test."""
    fold_col = "outer_fold" if level == "outer" else "inner_fold"
    needed = {"fold_plan_id", fold_col, "session_key", "role"}
    if not needed.issubset(set(_columns(folds))):
        return CheckResult(
            name="fold_roles[%s]" % level,
            passed=False,
            detail="no se puede verificar: faltan columnas de fold",
        )
    bad_roles = sorted(set(folds["role"]) - set(ALLOWED_FOLD_ROLES))
    conflicts: List[Any] = []
    empty_folds: List[Any] = []
    for keys, group in folds.groupby(["fold_plan_id", fold_col]):
        roles_by_session = group.groupby("session_key")["role"].apply(set)
        for session_key, roles in roles_by_session.items():
            if "train" in roles and "test" in roles:
                conflicts.append({"fold": keys, "session_key": session_key})
        if "test" not in set(group["role"]):
            empty_folds.append(keys)
    passed = not bad_roles and not conflicts and not empty_folds
    return CheckResult(
        name="fold_roles[%s]" % level,
        passed=passed,
        detail=(
            "roles inválidos=%d, conflictos train/test=%d, folds sin test=%d"
            % (len(bad_roles), len(conflicts), len(empty_folds))
        ),
        offenders=[*bad_roles, *conflicts, *empty_folds],
    )


def check_embargo(folds: Any, targets: Any, embargo_ns: int) -> CheckResult:
    """El embargo declarado debe cubrir el horizonte máximo de etiqueta."""
    if "label_horizon_ns" not in set(_columns(targets)):
        return CheckResult(
            name="embargo_covers_label_horizon",
            passed=False,
            detail="no se puede verificar: falta label_horizon_ns",
        )
    if len(targets) == 0:
        return CheckResult(
            name="embargo_covers_label_horizon",
            passed=False,
            detail="no se puede verificar: targets vacío",
        )
    max_h = int(targets["label_horizon_ns"].max())
    return CheckResult(
        name="embargo_covers_label_horizon",
        passed=embargo_ns >= max_h,
        detail="embargo_ns=%d, max_label_horizon_ns=%d" % (embargo_ns, max_h),
    )


def check_null_window_fraction(windows: Any, minimum: float) -> CheckResult:
    """Debe existir grupo de control: una fracción mínima de ventanas sin
    ningún frame activo. Sin controles el contraste no es estimable."""
    if "active_frame_count" not in set(_columns(windows)):
        return CheckResult(
            name="null_window_fraction",
            passed=False,
            detail="no se puede verificar: falta active_frame_count",
        )
    n = len(windows)
    if n == 0:
        return CheckResult(
            name="null_window_fraction",
            passed=False,
            detail="no se puede verificar: windows vacío",
        )
    frac = float((windows["active_frame_count"] == 0).sum()) / n
    return CheckResult(
        name="null_window_fraction",
        passed=frac >= minimum,
        detail="fracción sin frames=%.4f, mínimo=%.4f" % (frac, minimum),
    )


def check_cutoff_grid_independence(windows: Any) -> CheckResult:
    """Debe existir al menos una fila con `cutoff_origin='grid'`; si todos los
    cutoffs son event-driven, el muestreo está condicionado a la señal."""
    if "cutoff_origin" not in set(_columns(windows)):
        return CheckResult(
            name="cutoff_grid_independence",
            passed=False,
            detail="no se puede verificar: falta cutoff_origin",
        )
    n_grid = int((windows["cutoff_origin"] == "grid").sum())
    return CheckResult(
        name="cutoff_grid_independence",
        passed=n_grid > 0,
        detail="filas con cutoff de grilla=%d" % n_grid,
    )


def check_target_leakage_columns(windows: Any) -> CheckResult:
    """Ninguna columna de features puede tener prefijo de outcome."""
    offenders = [
        c for c in _columns(windows)
        if any(c.startswith(p) for p in FORBIDDEN_FEATURE_PREFIXES)
    ]
    return CheckResult(
        name="no_target_columns_in_features",
        passed=not offenders,
        detail="%d columnas con prefijo prohibido" % len(offenders),
        offenders=offenders,
    )


def check_manifest(manifest: Mapping[str, Any], required_fields: Iterable[str]) -> CheckResult:
    """El manifiesto debe declarar identidad completa y código limpio."""
    missing = [f for f in required_fields if f not in manifest]
    dirty = bool(manifest.get("code_dirty", True))
    passed = not missing and not dirty
    return CheckResult(
        name="manifest_identity",
        passed=passed,
        detail="campos faltantes=%d, code_dirty=%s" % (len(missing), dirty),
        offenders=missing,
    )


def check_sessions_declared_in_folds(windows: Any, folds: Any) -> CheckResult:
    """Toda sesión presente en las ventanas debe existir en el plan de folds."""
    if "session_key" not in set(_columns(windows)) or "session_key" not in set(_columns(folds)):
        return CheckResult(
            name="sessions_declared_in_folds",
            passed=False,
            detail="no se puede verificar: falta session_key",
        )
    missing = sorted(set(windows["session_key"]) - set(folds["session_key"]))
    return CheckResult(
        name="sessions_declared_in_folds",
        passed=not missing,
        detail="%d sesiones sin plan de folds" % len(missing),
        offenders=missing,
    )


def validate_all(
    *,
    manifest: Mapping[str, Any],
    events: Any,
    windows: Any,
    targets: Any,
    folds_outer: Any,
    contract: Mapping[str, Any],
    embargo_ns: Optional[int] = None,
) -> ValidationReport:
    """Ejecuta el contrato completo. Devuelve un reporte; no lanza excepciones
    por incumplimiento, para que el llamador pueda serializar el detalle."""
    report = ValidationReport()
    tables = contract.get("tables", {})
    firewall = contract.get("firewall", {})
    cutoff_policy = contract.get("cutoff_policy", {})
    identity = contract.get("identity", {})

    report.add(check_manifest(manifest, identity.get("required_manifest_fields", [])))

    for table_name, df in (
        ("events_long", events),
        ("windows_ml", windows),
        ("targets_long", targets),
    ):
        spec = tables.get(table_name, {})
        report.add(check_required_columns(df, spec.get("required_columns", []), table_name))
        report.add(check_primary_key_unique(df, spec.get("primary_key", []), table_name))

    report.add(check_target_leakage_columns(windows))
    report.add(check_causality(windows, targets))
    report.add(check_cutoff_grid_independence(windows))
    report.add(
        check_null_window_fraction(
            windows, float(cutoff_policy.get("min_null_window_fraction", 0.0))
        )
    )
    report.add(check_fold_roles(folds_outer, level="outer"))
    report.add(check_sessions_declared_in_folds(windows, folds_outer))

    max_allowed_ns = firewall.get("max_allowed_timestamp_ns")
    if max_allowed_ns is not None:
        report.add(check_firewall(windows, "cutoff_ns", int(max_allowed_ns), "windows_ml"))
        report.add(check_firewall(targets, "target_end_ns", int(max_allowed_ns), "targets_long"))
    else:
        report.add(
            CheckResult(
                name="firewall[configured]",
                passed=False,
                detail="contract.firewall.max_allowed_timestamp_ns ausente",
            )
        )

    if embargo_ns is not None:
        report.add(check_embargo(folds_outer, targets, int(embargo_ns)))
    else:
        report.add(
            CheckResult(
                name="embargo_covers_label_horizon",
                passed=False,
                detail="embargo_ns no fue provisto",
            )
        )

    return report
