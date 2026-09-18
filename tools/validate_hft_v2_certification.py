#!/usr/bin/env python3
"""Fail-closed preflight for an HFTZones V2 shared-input SQLite export.

This does not replace the parity reconstruction. It prevents the historical
subset comparator from being described as a full certification when causal or
identity invariants are absent.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ALLOWED_TERMINATIONS = ("REVERSAL", "MAX_PAUSE", "END_OF_SESSION", "CENSORED_END_OF_INPUT")
REQUIRED_TICK_COLUMNS = {"instrument", "contract", "session_id", "tick_seq", "timestamp_ns", "price_ticks", "volume"}
REQUIRED_ZONE_COLUMNS = {
    "instrument", "contract", "session_id", "zone_seq", "start_tick_seq", "end_tick_seq",
    "start_ts_ns", "end_ts_ns", "available_ts_ns", "direction", "lo_ticks", "hi_ticks",
    "pasos", "vol", "avg_ms", "total_ms", "volume_rate", "parameter_manifest_sha256",
    "indicator_source_sha256", "termination_reason",
}
HOLDOUT_START_NS = 1782856800000000000  # 2026-06-30T22:00:00Z, session 20260701 open


def _columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in con.execute(f"PRAGMA table_info({table})")}


def validate(con: sqlite3.Connection, instrument: str) -> dict:
    errors: list[dict] = []
    tables = {str(row[0]) for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ("hft_ticks_v2", "hft_zones_v2"):
        if table not in tables:
            errors.append({"code": "MISSING_TABLE", "table": table})
    if errors:
        return {"status": "FAIL_HARDENED_PREFLIGHT", "is_pass": False, "errors": errors}

    missing_ticks = sorted(REQUIRED_TICK_COLUMNS - _columns(con, "hft_ticks_v2"))
    missing_zones = sorted(REQUIRED_ZONE_COLUMNS - _columns(con, "hft_zones_v2"))
    if missing_ticks:
        errors.append({"code": "MISSING_TICK_COLUMNS", "columns": missing_ticks})
    if missing_zones:
        errors.append({"code": "MISSING_ZONE_COLUMNS", "columns": missing_zones})
    if errors:
        return {"status": "FAIL_HARDENED_PREFLIGHT", "is_pass": False, "errors": errors}

    params = (instrument,)
    tick_count = int(con.execute("SELECT COUNT(*) FROM hft_ticks_v2 WHERE instrument=?", params).fetchone()[0])
    zone_count = int(con.execute("SELECT COUNT(*) FROM hft_zones_v2 WHERE instrument=?", params).fetchone()[0])
    if not tick_count:
        errors.append({"code": "EMPTY_TICKS"})
    if not zone_count:
        errors.append({"code": "EMPTY_ZONES"})

    bad_availability = int(con.execute("SELECT COUNT(*) FROM hft_zones_v2 WHERE instrument=? AND available_ts_ns < end_ts_ns", params).fetchone()[0])
    if bad_availability:
        errors.append({"code": "AVAILABLE_BEFORE_END", "count": bad_availability})
    bad_origin = int(con.execute("SELECT COUNT(*) FROM hft_zones_v2 WHERE instrument=? AND end_ts_ns < start_ts_ns", params).fetchone()[0])
    if bad_origin:
        errors.append({"code": "END_BEFORE_START", "count": bad_origin})

    # NOT NULL is schema eligibility, not proof of native provenance.
    cols_zones_info = {r[1]: r for r in con.execute("PRAGMA table_info(hft_zones_v2)").fetchall()}
    term_info = cols_zones_info.get("termination_reason")
    if term_info and term_info[3] == 0:
        errors.append({
            "code": "PYTHON_BACKFILLED_TERMINATION_REASON",
            "message": "termination_reason is NULLABLE; fresh NT8 export must create it as TEXT NOT NULL",
        })

    placeholders = ",".join("?" for _ in ALLOWED_TERMINATIONS)
    bad_reasons = int(con.execute(
        f"SELECT COUNT(*) FROM hft_zones_v2 WHERE instrument=? AND (termination_reason IS NULL OR termination_reason NOT IN ({placeholders}))",
        (instrument, *ALLOWED_TERMINATIONS),
    ).fetchone()[0])
    if bad_reasons:
        errors.append({"code": "UNCERTIFIABLE_TERMINATION_REASON", "count": bad_reasons})

    holdout_ticks = int(con.execute(
        "SELECT COUNT(*) FROM hft_ticks_v2 WHERE instrument=? AND timestamp_ns >= ?",
        (instrument, HOLDOUT_START_NS),
    ).fetchone()[0])
    if holdout_ticks:
        errors.append({"code": "HOLDOUT_CONTAMINATION", "count": holdout_ticks})

    bad_tick_groups = con.execute("""
        SELECT contract, session_id, COUNT(*) n, MIN(tick_seq) lo, MAX(tick_seq) hi,
               COUNT(DISTINCT tick_seq) distinct_n
        FROM hft_ticks_v2 WHERE instrument=? GROUP BY contract, session_id
        HAVING lo<>1 OR hi<>n OR distinct_n<>n
    """, params).fetchall()
    if bad_tick_groups:
        errors.append({"code": "NONCONTIGUOUS_TICK_SEQUENCE", "samples": [list(row) for row in bad_tick_groups[:10]]})

    bad_zone_groups = con.execute("""
        SELECT contract, session_id, COUNT(*) n, MIN(zone_seq) lo, MAX(zone_seq) hi,
               COUNT(DISTINCT zone_seq) distinct_n
        FROM hft_zones_v2 WHERE instrument=? GROUP BY contract, session_id
        HAVING lo<>1 OR hi<>n OR distinct_n<>n
    """, params).fetchall()
    if bad_zone_groups:
        errors.append({"code": "NONCONTIGUOUS_ZONE_SEQUENCE", "samples": [list(row) for row in bad_zone_groups[:10]]})

    inversions = int(con.execute("""
        WITH ordered AS (
          SELECT timestamp_ns,
                 LAG(timestamp_ns) OVER (PARTITION BY contract, session_id ORDER BY tick_seq) prev_ts
          FROM hft_ticks_v2 WHERE instrument=?
        ) SELECT COUNT(*) FROM ordered WHERE prev_ts IS NOT NULL AND timestamp_ns < prev_ts
    """, params).fetchone()[0])
    if inversions:
        errors.append({"code": "NONMONOTONIC_TICK_TIMESTAMPS", "count": inversions})

    contracts = [str(row[0]) for row in con.execute("SELECT DISTINCT contract FROM hft_ticks_v2 WHERE instrument=? ORDER BY contract", params)]
    if len(contracts) > 1:
        errors.append({
            "code": "MULTICONTRACT_COMPARATOR_NOT_YET_CERTIFIABLE",
            "contracts": contracts,
            "reason": "historical comparator carries previous-session close across contract transitions",
        })

    return {
        "status": "PASS_HARDENED_PREFLIGHT_NOT_FULL_PARITY" if not errors else "FAIL_HARDENED_PREFLIGHT",
        "is_pass": not errors,
        "instrument": instrument,
        "tick_count": tick_count,
        "zone_count": zone_count,
        "contracts": contracts,
        "errors": errors,
        "certification_scope": "PREFLIGHT_ONLY_REQUIRES_FULL_FIELD_PARITY_RECONSTRUCTION",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--instrument", default="NQ JUN26")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    con = sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True)
    try:
        result = validate(con, args.instrument)
    finally:
        con.close()
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    print(rendered)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["is_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
