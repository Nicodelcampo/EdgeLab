from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CALENDAR = ROOT / "specs" / "bt2a_macro_calendar_gc_20250804_20260630_v1.json"


def _dt(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def test_official_macro_calendar_is_complete_sorted_and_pre_holdout():
    value = json.loads(CALENDAR.read_text(encoding="utf-8"))
    assert value["schema"] == "bt2a_macro_calendar_v1"
    assert value["status"] == "FROZEN_RESEARCH_SOURCED"
    events = value["events"]
    assert len(events) == 26
    assert Counter(row["event_type"] for row in events) == {"FOMC": 7, "CPI": 10, "NFP": 9}
    timestamps = [_dt(row["release_utc"]) for row in events]
    assert timestamps == sorted(timestamps)
    assert min(timestamps) >= _dt("2025-08-04T00:00:00Z")
    assert max(timestamps) < _dt("2026-07-01T00:00:00Z")
    assert len({row["event_id"] for row in events}) == len(events)
    assert all(row["source_url"].startswith("https://www.") for row in events)
    assert all("bls.gov" in row["source_url"] or "federalreserve.gov" in row["source_url"] for row in events)


def test_dst_conversions_and_cancellations_are_explicit():
    value = json.loads(CALENDAR.read_text(encoding="utf-8"))
    by_id = {row["event_id"]: row["release_utc"] for row in value["events"]}
    assert by_id["FOMC-2025-09-17"].endswith("18:00:00Z")
    assert by_id["FOMC-2025-12-10"].endswith("19:00:00Z")
    assert by_id["CPI-2026-02"].endswith("12:30:00Z")
    assert by_id["NFP-2026-02"].endswith("13:30:00Z")
    canceled = {(row["event_type"], row["reference_period"]) for row in value["canceled_releases"]}
    assert canceled == {("CPI", "2025-10"), ("NFP", "2025-10")}


def test_calendar_firewall_remains_closed():
    value = json.loads(CALENDAR.read_text(encoding="utf-8"))
    assert value["firewall"] == {
        "P2B_RUN": False,
        "PNL_ACCESSED": False,
        "FUTURE_PRICE_PATH_ACCESSED": False,
        "HOLDOUT_TOUCHED": False,
        "WINNER_SELECTED": False,
        "EDGE_DECLARED": False,
    }
