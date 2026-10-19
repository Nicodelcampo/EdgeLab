# -*- coding: utf-8 -*-
"""Validador fail-closed del contrato estructural ZAMR-1.

No requiere ni acepta targets. Inspecciona identidad, schema, causalidad,
firewall y geometría sin calcular outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_SCHEMA_VERSION = "zamr1_structural_contract_v0"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    offenders: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": bool(self.passed),
            "detail": self.detail,
            "offenders": self.offenders[:20],
            "offender_count": len(self.offenders),
        }


@dataclass
class ValidationReport:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> "ValidationReport":
        self.checks.append(result)
        return self

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(item.passed for item in self.checks)

    @property
    def failures(self) -> list[CheckResult]:
        return [item for item in self.checks if not item.passed]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_schema_version": CONTRACT_SCHEMA_VERSION,
            "passed": self.passed,
            "n_checks": len(self.checks),
            "n_failures": len(self.failures),
            "checks": [item.to_dict() for item in self.checks],
        }


def _columns(df: Any) -> list[str]:
    try:
        return list(df.columns)
    except Exception as exc:  # pragma: no cover - defensa
        raise TypeError("se esperaba un DataFrame") from exc


def check_required_columns(df: Any, required: Sequence[str], table: str) -> CheckResult:
    missing = [name for name in required if name not in set(_columns(df))]
    return CheckResult(
        "required_columns[%s]" % table,
        not missing,
        "faltan %d columnas" % len(missing),
        missing,
    )


def check_primary_key(df: Any, key: Sequence[str], table: str) -> CheckResult:
    missing = [name for name in key if name not in set(_columns(df))]
    if missing:
        return CheckResult("primary_key[%s]" % table, False, "clave no verificable", missing)
    dup = df.duplicated(subset=list(key), keep=False)
    count = int(dup.sum())
    offenders = df.loc[dup, list(key)].head(20).to_dict("records") if count else []
    return CheckResult("primary_key[%s]" % table, count == 0, "%d duplicados" % count, offenders)


def check_manifest(manifest: Mapping[str, Any], contract: Mapping[str, Any]) -> CheckResult:
    identity = contract.get("identity", {})
    required = identity.get("required_manifest_fields", [])
    missing = [name for name in required if name not in manifest]
    bad: list[Any] = list(missing)
    for flag in ("code_dirty", "outcomes_accessed", "pnl_accessed", "holdout_included"):
        if manifest.get(flag, True):
            bad.append({flag: manifest.get(flag)})
    allowed_licenses = set(identity.get("allowed_license_decisions", []))
    if manifest.get("license_decision") not in allowed_licenses:
        bad.append({"license_decision": manifest.get("license_decision")})
    expected_cutoff = contract.get("firewall", {}).get("research_cutoff_utc")
    if manifest.get("research_cutoff_utc") != expected_cutoff:
        bad.append({"research_cutoff_utc": manifest.get("research_cutoff_utc")})
    return CheckResult("manifest_identity", not bad, "%d violaciones" % len(bad), bad)


def check_forbidden_columns(df: Any, prefixes: Iterable[str], table: str) -> CheckResult:
    bad = [name for name in _columns(df) if any(name.startswith(p) for p in prefixes)]
    return CheckResult("forbidden_columns[%s]" % table, not bad, "%d columnas" % len(bad), bad)


def check_firewall(df: Any, columns: Sequence[str], cutoff_ns: int, table: str) -> CheckResult:
    missing = [name for name in columns if name not in set(_columns(df))]
    if missing:
        return CheckResult("firewall[%s]" % table, False, "no verificable", missing)
    bad: list[Any] = []
    for name in columns:
        series = df[name].dropna()
        count = int((series >= cutoff_ns).sum())
        if count:
            bad.append({"column": name, "rows": count})
    return CheckResult("firewall[%s]" % table, not bad, "%d columnas violadas" % len(bad), bad)


def check_event_clock(events: Any) -> CheckResult:
    needed = {"event_time_ns", "bar_end_ns", "available_at_ns"}
    missing = sorted(needed - set(_columns(events)))
    if missing:
        return CheckResult("event_clock_order", False, "no verificable", missing)
    bad_event = int((events["event_time_ns"] > events["bar_end_ns"]).sum())
    bad_available = int((events["bar_end_ns"] > events["available_at_ns"]).sum())
    total = bad_event + bad_available
    return CheckResult(
        "event_clock_order", total == 0,
        "event>bar_end=%d, bar_end>available=%d" % (bad_event, bad_available),
    )


def check_zone_invariants(zones: Any) -> CheckResult:
    needed = {"created_at_ns", "available_at_ns", "ended_at_ns", "zone_lo_tick", "zone_hi_tick"}
    missing = sorted(needed - set(_columns(zones)))
    if missing:
        return CheckResult("zone_invariants", False, "no verificable", missing)
    bad_available = int((zones["available_at_ns"] < zones["created_at_ns"]).sum())
    ended = zones["ended_at_ns"].notna()
    bad_end = int((zones.loc[ended, "ended_at_ns"] < zones.loc[ended, "created_at_ns"]).sum())
    bad_geometry = int((zones["zone_lo_tick"] > zones["zone_hi_tick"]).sum())
    total = bad_available + bad_end + bad_geometry
    return CheckResult(
        "zone_invariants", total == 0,
        "available<created=%d, ended<created=%d, lo>hi=%d" % (
            bad_available, bad_end, bad_geometry,
        ),
    )


def check_pilot_scope(events: Any, zones: Any, contract: Mapping[str, Any]) -> CheckResult:
    pilot = contract.get("pilot", {})
    allowed_indicators = set(pilot.get("allowed_indicators", []))
    allowed_specs = set(pilot.get("allowed_bar_specs", []))
    bad: list[Any] = []
    for table_name, df in (("events_long", events), ("zones_long", zones)):
        cols = set(_columns(df))
        if not {"indicator_id", "bar_spec", "session_key"}.issubset(cols):
            bad.append({"table": table_name, "reason": "scope columns missing"})
            continue
        unknown_indicators = sorted(set(df["indicator_id"].dropna()) - allowed_indicators)
        unknown_specs = sorted(set(df["bar_spec"].dropna()) - allowed_specs)
        if unknown_indicators:
            bad.append({"table": table_name, "indicators": unknown_indicators})
        if unknown_specs:
            bad.append({"table": table_name, "bar_specs": unknown_specs})
    sessions = set(events.get("session_key", [])) | set(zones.get("session_key", []))
    n_sessions = len(sessions)
    if n_sessions < int(pilot.get("min_sessions", 0)) or n_sessions > int(pilot.get("max_sessions", 10**9)):
        bad.append({"session_count": n_sessions})
    return CheckResult("pilot_scope", not bad, "%d violaciones" % len(bad), bad)


def validate_structural_dataset(
    *,
    manifest: Mapping[str, Any],
    events: Any,
    zones: Any,
    contract: Mapping[str, Any],
) -> ValidationReport:
    report = ValidationReport()
    if contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        report.add(CheckResult(
            "contract_schema_version", False,
            "esperado %s" % CONTRACT_SCHEMA_VERSION,
            [contract.get("schema_version")],
        ))
    else:
        report.add(CheckResult("contract_schema_version", True, CONTRACT_SCHEMA_VERSION))
    report.add(check_manifest(manifest, contract))
    prefixes = contract.get("forbidden_column_prefixes", [])
    for table_name, df in (("events_long", events), ("zones_long", zones)):
        spec = contract.get("tables", {}).get(table_name, {})
        report.add(check_required_columns(df, spec.get("required_columns", []), table_name))
        report.add(check_primary_key(df, spec.get("primary_key", []), table_name))
        report.add(check_forbidden_columns(df, prefixes, table_name))
    cutoff = int(contract.get("firewall", {}).get("max_allowed_timestamp_ns_exclusive", 0))
    if cutoff <= 0:
        report.add(CheckResult("firewall_configured", False, "cutoff ausente/inválido"))
    else:
        report.add(check_firewall(events, ["event_time_ns", "bar_end_ns", "available_at_ns"], cutoff, "events_long"))
        report.add(check_firewall(zones, ["created_at_ns", "available_at_ns", "ended_at_ns"], cutoff, "zones_long"))
    report.add(check_event_clock(events))
    report.add(check_zone_invariants(zones))
    report.add(check_pilot_scope(events, zones, contract))
    return report
