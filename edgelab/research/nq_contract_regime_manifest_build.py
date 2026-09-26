"""Fail-closed inputs for the real NQ contract-regime manifest.

Observed ticks and certified complete sessions are separate objects. A parquet
row proves a trade was observed; it never proves that the source contains the
whole CME session. Missing observations are never silently converted to zero.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

EVIDENCE_SCHEMA = "nq_complete_session_evidence_v1"
OBSERVATIONS_SCHEMA = "nq_contract_session_observations_v2"
_CONTRACT_RE = re.compile(r"^(?P<root>[A-Z0-9]+)[ _](?P<mm>\d{2})-(?P<yy>\d{2})$")


class NQManifestInputError(ValueError):
    pass


def parse_contract_label(label: str) -> dict[str, Any]:
    m = _CONTRACT_RE.match(str(label).strip())
    if not m:
        raise NQManifestInputError(f"contract label no reconocido: {label!r}")
    root, mm, yy = m.group("root"), int(m.group("mm")), int(m.group("yy"))
    if not 1 <= mm <= 12:
        raise NQManifestInputError(f"mes invalido en {label!r}")
    return {"root": root, "contract": f"{root} {mm:02d}-{yy:02d}",
            "expiry_ordinal": (2000 + yy) * 100 + mm}


def canonical_contract_from_columns(instrument: str, contract: str) -> str:
    root, raw = str(instrument).strip().upper(), str(contract).strip()
    if not root or not raw:
        raise NQManifestInputError("instrument/contract internos vacios")
    if re.fullmatch(r"\d{2}-\d{2}", raw):
        raw = f"{root} {raw}"
    parsed = parse_contract_label(raw)
    if parsed["root"] != root:
        raise NQManifestInputError(
            f"instrument/contract internos no coinciden: {root!r}, {contract!r}")
    return str(parsed["contract"])


def _ymd(value: Any, field: str = "trade_date") -> int:
    try:
        ymd, text = int(value), str(int(value))
        if len(text) != 8:
            raise ValueError
        date(int(text[:4]), int(text[4:6]), int(text[6:]))
        return ymd
    except (TypeError, ValueError) as exc:
        raise NQManifestInputError(f"{field} invalido: {value!r}") from exc


def _weekday(ymd: int) -> int:
    text = str(_ymd(ymd))
    return date(int(text[:4]), int(text[4:6]), int(text[6:])).weekday()


def validate_trade_calendar(calendar_trade_dates: Sequence[int]) -> list[int]:
    calendar = [_ymd(v, "calendar_trade_date") for v in calendar_trade_dates]
    if not calendar or calendar != sorted(set(calendar)):
        raise NQManifestInputError("calendar_trade_dates debe ser unico y ascendente")
    invalid = [d for d in calendar if _weekday(d) >= 5]
    if invalid:
        raise NQManifestInputError(f"calendar_trade_dates contiene fines de semana: {invalid[:10]}")
    return calendar


def _normalize_observations(per_contract_observations):
    normalized, quarantine = {}, []
    for raw_label, raw_by_day in per_contract_observations.items():
        label = str(parse_contract_label(raw_label)["contract"])
        if label in normalized:
            raise NQManifestInputError(f"contrato duplicado: {label}")
        by_day = {}
        for raw_day, raw in raw_by_day.items():
            day = _ymd(raw_day)
            rec = {"volume": float(raw.get("volume", 0.0)),
                   "tick_count": int(raw.get("tick_count", 0)),
                   "maintenance_tick_count": int(raw.get("maintenance_tick_count", 0)),
                   "first_ts_ns": raw.get("first_ts_ns"),
                   "last_ts_ns": raw.get("last_ts_ns")}
            if rec["volume"] < 0 or rec["volume"] != rec["volume"] or min(rec["tick_count"], rec["maintenance_tick_count"]) < 0:
                raise NQManifestInputError(f"observacion invalida: {(label, day)}")
            if _weekday(day) >= 5:
                quarantine.append({"code": "INVALID_WEEKEND_TRADE_DATE", "contract": label,
                                   "trade_date": day, "tick_count": rec["tick_count"],
                                   "volume": rec["volume"]})
            else:
                by_day[day] = rec
        if not by_day:
            raise NQManifestInputError(f"{label}: sin observaciones validas de lunes a viernes")
        normalized[label] = by_day
    if not normalized:
        raise NQManifestInputError("per_contract_observations vacio")
    return normalized, quarantine


def _validate_evidence(evidence, source_identity):
    if evidence.get("schema_version") != EVIDENCE_SCHEMA:
        raise NQManifestInputError("schema de evidencia de completitud incorrecto")
    if evidence.get("source_dataset") != source_identity.get("dataset"):
        raise NQManifestInputError("evidencia ligada a otro dataset")
    hashes = source_identity.get("contract_parquet_sha256")
    if not isinstance(hashes, Mapping) or not hashes:
        raise NQManifestInputError("source_identity sin contract_parquet_sha256")
    if evidence.get("contract_parquet_sha256") != hashes:
        raise NQManifestInputError("evidencia ligada a otros hashes parquet")
    calendar = validate_trade_calendar(evidence.get("calendar_trade_dates", []))
    sessions = evidence.get("sessions")
    if not isinstance(sessions, Mapping):
        raise NQManifestInputError("evidencia sin sessions")
    return calendar, sessions


def build_completeness_evidence_template(per_contract_observations, source_identity):
    observations, quarantine = _normalize_observations(per_contract_observations)
    calendar = sorted({d for rows in observations.values() for d in rows})
    sessions = {label: {str(day): {"complete_session": False,
                                  "basis": "UNREVIEWED_OBSERVATION_REQUIRES_SOURCE_EVIDENCE",
                                  "explicit_zero_volume": False}
                        for day in sorted(rows)}
                for label, rows in sorted(observations.items())}
    return {"schema_version": EVIDENCE_SCHEMA,
            "source_dataset": source_identity.get("dataset"),
            "contract_parquet_sha256": dict(source_identity.get("contract_parquet_sha256", {})),
            "calendar_trade_dates": calendar, "sessions": sessions,
            "quarantined_observations": quarantine, "approved": False}


def prepare_nq_manifest_inputs(*, per_contract_observations,
                               completeness_evidence, source_identity):
    observations, quarantine = _normalize_observations(per_contract_observations)
    calendar, raw_evidence = _validate_evidence(completeness_evidence, source_identity)
    evidence = {str(parse_contract_label(k)["contract"]): v for k, v in raw_evidence.items()}
    if set(observations) != set(evidence):
        raise NQManifestInputError("contratos observados y certificados no coinciden")
    calendar_set, diagnostics = set(calendar), list(quarantine)
    contracts, daily_volumes = [], []
    for label, by_day in sorted(observations.items(), key=lambda x: parse_contract_label(x[0])["expiry_ordinal"]):
        valid_days = sorted(set(by_day) & calendar_set)
        for day in sorted(set(by_day) - calendar_set):
            diagnostics.append({"code": "OBSERVATION_OUTSIDE_CERTIFIED_CALENDAR",
                                "contract": label, "trade_date": day})
        if not valid_days:
            raise NQManifestInputError(f"{label}: sin observaciones dentro del calendario")
        first, last = valid_days[0], valid_days[-1]
        meta = parse_contract_label(label)
        meta.update(first_trade_date=first, last_trade_date=last)
        contracts.append(meta)
        for day in [d for d in calendar if first <= d <= last]:
            obs = by_day.get(day)
            cert = evidence[label].get(str(day), evidence[label].get(day))
            cert = cert or {"complete_session": False,
                            "basis": "MISSING_COMPLETENESS_EVIDENCE",
                            "explicit_zero_volume": False}
            complete = cert.get("complete_session")
            explicit_zero = cert.get("explicit_zero_volume", False)
            basis = str(cert.get("basis", "")).strip()
            if not isinstance(complete, bool) or not isinstance(explicit_zero, bool) or not basis:
                raise NQManifestInputError(f"certificacion incompleta para {(label, day)}")
            if obs is None:
                volume = 0.0
                if not (complete and explicit_zero):
                    complete = False
                    diagnostics.append({"code": "MISSING_SOURCE_ROW", "contract": label,
                                        "trade_date": day, "basis": basis})
            else:
                volume = float(obs["volume"])
                if explicit_zero:
                    raise NQManifestInputError(f"explicit_zero_volume con ticks: {(label, day)}")
                if obs["maintenance_tick_count"] > 0:
                    complete = False
                    diagnostics.append({"code": "MAINTENANCE_TICKS_PRESENT", "contract": label,
                                        "trade_date": day,
                                        "tick_count": obs["maintenance_tick_count"]})
                if not complete:
                    diagnostics.append({"code": "SESSION_NOT_CERTIFIED_COMPLETE",
                                        "contract": label, "trade_date": day,
                                        "basis": basis})
            daily_volumes.append({"root": meta["root"], "contract": label,
                                  "trade_date": day, "volume": volume,
                                  "complete_session": complete})
    blocking = {"MAINTENANCE_TICKS_PRESENT", "MISSING_SOURCE_ROW",
                "SESSION_NOT_CERTIFIED_COMPLETE"}
    return {"regime_inputs": {"contracts": contracts, "daily_volumes": daily_volumes,
                              "calendar_trade_dates": calendar,
                              "source_identity": dict(source_identity)},
            "diagnostics": diagnostics,
            "ready_for_certified_manifest": not any(d.get("code") in blocking for d in diagnostics)}
