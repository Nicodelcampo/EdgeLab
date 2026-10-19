"""Evidence-bound CME Equity Index research session calendar.

Market hours and source-capture completeness are deliberately separate. The
calendar describes when the market was expected to be open; it cannot certify
that a tick source captured the whole interval.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

SCHEMA_VERSION = "cme_equity_index_session_calendar_v1"
TIMEZONE = "America/Chicago"
CHICAGO = ZoneInfo(TIMEZONE)
SESSION_CLASSES = {"NORMAL", "EARLY_CLOSE", "CLOSED"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CalendarEvidenceError(ValueError):
    pass


def _date(ymd: int) -> date:
    text = str(int(ymd))
    if len(text) != 8:
        raise CalendarEvidenceError(f"trade_date invalido: {ymd!r}")
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:]))
    except ValueError as exc:
        raise CalendarEvidenceError(f"trade_date invalido: {ymd!r}") from exc


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _evidence(items: Any) -> list[dict[str, str]]:
    if not isinstance(items, list) or not items:
        raise CalendarEvidenceError("cada sesion requiere evidencia")
    out = []
    for item in items:
        if not isinstance(item, Mapping):
            raise CalendarEvidenceError("evidencia invalida")
        url = str(item.get("url", "")); sha = str(item.get("sha256", ""))
        retrieved = str(item.get("retrieved_at", ""))
        if not url.startswith("https://www.cmegroup.com/"):
            raise CalendarEvidenceError("la fuente primaria debe ser cmegroup.com")
        if not _SHA256_RE.fullmatch(sha):
            raise CalendarEvidenceError("sha256 de evidencia invalido")
        try:
            datetime.fromisoformat(retrieved.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CalendarEvidenceError("retrieved_at invalido") from exc
        out.append({"url": url, "sha256": sha, "retrieved_at": retrieved})
    return out


def _local_iso(value: Any, field: str) -> str:
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise CalendarEvidenceError(f"{field} invalido") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise CalendarEvidenceError(f"{field} debe incluir offset")
    return dt.isoformat()


def validate_override(raw: Mapping[str, Any]) -> dict[str, Any]:
    day = int(raw.get("trade_date")); d = _date(day)
    kind = str(raw.get("session_class"))
    if kind not in SESSION_CLASSES:
        raise CalendarEvidenceError(f"session_class invalida: {kind}")
    evidence = _evidence(raw.get("evidence"))
    opened, closed = raw.get("expected_open_ct"), raw.get("expected_close_ct")
    if kind == "CLOSED":
        if opened is not None or closed is not None:
            raise CalendarEvidenceError("CLOSED requiere bounds null")
        open_iso = close_iso = None
    else:
        open_iso = _local_iso(opened, "expected_open_ct")
        close_iso = _local_iso(closed, "expected_close_ct")
        open_dt, close_dt = datetime.fromisoformat(open_iso), datetime.fromisoformat(close_iso)
        if not open_dt < close_dt or close_dt.date() != d:
            raise CalendarEvidenceError("bounds incompatibles con trade_date")
        if kind == "NORMAL" and close_dt.timetz().replace(tzinfo=None) != time(16):
            raise CalendarEvidenceError("NORMAL debe cerrar 16:00 CT")
    return {"trade_date": day, "session_class": kind,
            "expected_open_ct": open_iso, "expected_close_ct": close_iso,
            "holiday_name": raw.get("holiday_name"), "evidence": evidence}


def build_calendar(*, start_trade_date: int, end_trade_date: int,
                   holiday_review_dates: Sequence[int],
                   holiday_overrides: Sequence[Mapping[str, Any]],
                   default_hours_evidence: Sequence[Mapping[str, str]],
                   source_capture_policy_id: str) -> dict[str, Any]:
    start, end = _date(start_trade_date), _date(end_trade_date)
    if end < start:
        raise CalendarEvidenceError("rango invertido")
    review = {int(x) for x in holiday_review_dates}
    overrides = {int(x["trade_date"]): validate_override(x) for x in holiday_overrides}
    missing = sorted(review - set(overrides))
    if missing:
        raise CalendarEvidenceError(f"feriados sin override: {missing}")
    default_evidence = _evidence(list(default_hours_evidence))
    sessions, d = [], start
    while d <= end:
        ymd = d.year * 10000 + d.month * 100 + d.day
        if ymd in overrides:
            sessions.append(overrides[ymd])
        elif d.weekday() >= 5:
            sessions.append({"trade_date": ymd, "session_class": "CLOSED",
                "expected_open_ct": None, "expected_close_ct": None,
                "holiday_name": "WEEKEND", "evidence": default_evidence})
        else:
            opened = datetime.combine(d - timedelta(days=1), time(17), CHICAGO)
            closed = datetime.combine(d, time(16), CHICAGO)
            sessions.append({"trade_date": ymd, "session_class": "NORMAL",
                "expected_open_ct": opened.isoformat(),
                "expected_close_ct": closed.isoformat(),
                "holiday_name": None, "evidence": default_evidence})
        d += timedelta(days=1)
    result = {"schema_version": SCHEMA_VERSION, "timezone": TIMEZONE,
        "market_hours_only": True, "source_capture_complete_inferred": False,
        "source_capture_policy_id": source_capture_policy_id,
        "sessions": sessions}
    result["calendar_sha256"] = canonical_sha256(result)
    return result


def assert_source_capture_evidence(record: Mapping[str, Any]) -> None:
    required = {"trade_date", "contract", "source_partitions_expected",
                "source_partitions_present", "extraction_status", "source_sha256"}
    missing = sorted(required - set(record))
    if missing:
        raise CalendarEvidenceError(f"source capture evidence incompleta: {missing}")
    if record["extraction_status"] != "COMPLETE":
        raise CalendarEvidenceError("source capture no completa")
    if sorted(record["source_partitions_expected"]) != sorted(record["source_partitions_present"]):
        raise CalendarEvidenceError("faltan particiones de fuente")
    if not _SHA256_RE.fullmatch(str(record["source_sha256"])):
        raise CalendarEvidenceError("source_sha256 invalido")
