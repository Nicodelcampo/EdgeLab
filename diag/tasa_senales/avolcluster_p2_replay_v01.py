# -*- coding: utf-8 -*-
"""aVolClusterPOI v0.5 — P2-only parity replay, repaired v0.1.

This runner deliberately does NOT run the formal first-passage race. It first
proves exact parity between the frozen NT8 indicator and the Python kernel.
Only a later, separate runner may measure the indicator after P2_PASS.

Repairs derived from nt8/aVolClusterPOI.cs (blob d512d91a...):
- disjoint 10-bar blocks, reset each session (confirmed; not sliding);
- historical FIFO by 20 complete sessions, not 20 individual scores;
- first complete session retained;
- bucket anchor = bar close - 1 second;
- warmup uses all data before the oracle comparison window;
- one-to-one matching; both missing oracle rows and extra Python rows fail;
- fail closed on input hash or P1A.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

REPO_PATH = Path(__file__).resolve().parents[2]
if str(REPO_PATH) not in sys.path:
    sys.path.insert(0, str(REPO_PATH))

import numpy as np
import pandas as pd

from edgelab.bridge.bars import build_footprints, build_time_bars, p1a_gate, session_ids
from edgelab.bridge.indicators.avolclusterpoi import (
    NS,
    RESEARCH_DEFAULTS,
    SessionProfile,
    detect_block,
    session_relative_bucket,
)
from edgelab.bridge.ticks import load_canonical_parquet

SCHEMA_VERSION = "avolcluster_p2_replay_v0_1"
EXPECTED_6E_09_26_SHA256 = "6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4"
EXPECTED_INSTRUMENT_META = "6E 09-26"
TZ = "America/Chicago"
WINDOW_START = datetime(2026, 4, 10, 0, 0, 0)
WINDOW_END = datetime(2026, 7, 1, 0, 0, 0)  # exclusive


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_payload(payload: dict) -> dict:
    out = dict(payload)
    out.pop("payload_sha256", None)
    raw = json.dumps(out, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    out["payload_sha256"] = hashlib.sha256(raw).hexdigest()
    return out


def parse_oracle(path: str | Path) -> tuple[dict, list[dict]]:
    lines = Path(path).read_text(encoding="utf-8", errors="strict").splitlines()
    if not lines:
        raise ValueError("oráculo vacío")
    meta = {}
    first = lines[0].lstrip("# ")
    if first.startswith("meta,"):
        for item in first.split(",")[1:]:
            if "=" in item:
                k, v = item.split("=", 1)
                meta[k.strip()] = v.strip()
    header_i = next((i for i, line in enumerate(lines)
                     if "event_type" in line and "lower_tick" in line), None)
    if header_i is None:
        raise ValueError("header del oráculo ausente")
    delim = ";" if lines[header_i].count(";") > lines[header_i].count(",") else ","
    out = []
    for row in csv.DictReader(lines[header_i:], delimiter=delim):
        if row.get("event_type") != "ZONE_CREATED":
            continue
        raw_time = (row.get("bar_close_time") or "").strip()
        try:
            dt = datetime.fromisoformat(raw_time)
        except ValueError as exc:
            raise ValueError(f"timestamp de oráculo inválido: {raw_time!r}") from exc
        direction_raw = (row.get("direction") or "").upper()
        direction = 1 if direction_raw == "LONG" else (-1 if direction_raw == "SHORT" else 0)
        out.append({
            "time": dt.replace(tzinfo=None),
            "lower_tick": int(row["lower_tick"]),
            "upper_tick": int(row["upper_tick"]),
            "direction": direction,
            "zone_id": int(row.get("zone_id") or 0),
        })
    return meta, sorted(out, key=lambda z: (z["time"], z["lower_tick"], z["upper_tick"]))


def session_begin_utc_ns(bar_end_ns: int) -> int:
    """ActualSessionBegin surrogate for CME ETH (17:00 America/Chicago).

    ``bar_end_ns - 1s`` selects the session containing the bar interval, matching
    both C# GetTimeBucket and the [start,end) bar contract.
    """
    anchor = pd.Timestamp(int(bar_end_ns) - NS, unit="ns", tz="UTC").tz_convert(TZ)
    begin_day: date = anchor.date() if anchor.hour >= 17 else anchor.date() - timedelta(days=1)
    begin_local = pd.Timestamp(datetime.combine(begin_day, time(17, 0)), tz=TZ)
    return int(begin_local.tz_convert("UTC").value)


def local_naive_from_ns(ns: int) -> datetime:
    return pd.Timestamp(int(ns), unit="ns", tz="UTC").tz_convert(TZ).to_pydatetime().replace(tzinfo=None)


def replay_python_zones(ticks) -> tuple[list[dict], dict, dict]:
    bars = build_time_bars(ticks, minutes=1)
    fps = build_footprints(ticks, bars)
    p1a = p1a_gate(ticks, bars, fps)

    # A bar [start,end) belongs to the session containing end-1s.
    ses = session_ids(bars.end_ns - NS)
    profile = SessionProfile(lookback_sessions=RESEARCH_DEFAULTS["lookback_sessions"])
    zones = []
    session_diag = []

    for sid in np.unique(ses):
        indices = np.flatnonzero(ses == sid)
        if len(indices) < RESEARCH_DEFAULTS["window_bars"]:
            continue
        begin_ns = session_begin_utc_ns(int(bars.end_ns[indices[0]]))
        n_blocks = len(indices) // RESEARCH_DEFAULTS["window_bars"]
        n_before = len(zones)

        for block_no in range(n_blocks):
            block = indices[
                block_no * RESEARCH_DEFAULTS["window_bars"]:
                (block_no + 1) * RESEARCH_DEFAULTS["window_bars"]
            ]
            cells = {}
            for bar_idx in block:
                for price_tick, volume in fps.total[int(bar_idx)].items():
                    cells[price_tick] = cells.get(price_tick, 0.0) + volume

            creator = int(block[-1])
            bucket = session_relative_bucket(
                int(bars.end_ns[creator]), begin_ns,
                RESEARCH_DEFAULTS["time_bucket_minutes"],
            )
            hist_before = profile.history_scores(bucket)
            detected = detect_block(
                cells,
                hist_before,
                close_tick=int(bars.close_t[creator]),
            )
            # C# appends the block's best score only AFTER detecting this block.
            profile.add_block(bucket, detected["best_score"])

            for zone in detected["zones"]:
                if zone["kind"] != "OFF_PRICE":
                    continue
                zones.append({
                    "time": local_naive_from_ns(int(bars.end_ns[creator])),
                    "lower_tick": int(zone["lower_tick"]),
                    "upper_tick": int(zone["upper_tick"]),
                    "direction": int(zone.get("direction", 0)),
                    "bucket": int(bucket),
                    "history_samples": len(hist_before),
                    "history_sessions": profile.history_session_count(bucket),
                    "score": float(zone["score"]),
                    "threshold": float(zone["threshold"]),
                })
        profile.commit()
        session_diag.append({
            "session_id": int(sid),
            "bars": int(len(indices)),
            "complete_blocks": int(n_blocks),
            "off_price_zones": int(len(zones) - n_before),
        })

    diagnostics = {
        "n_ticks": int(len(ticks)),
        "n_bars": int(len(bars)),
        "n_sessions_processed": int(len(session_diag)),
        "sessions": session_diag,
    }
    return zones, p1a, diagnostics


def _brief(row: dict) -> dict:
    return {
        "time": row["time"].isoformat(timespec="seconds"),
        "lower_tick": int(row["lower_tick"]),
        "upper_tick": int(row["upper_tick"]),
        "direction": int(row.get("direction", 0)),
    }


def match_one_to_one(oracle: list[dict], python: list[dict], tolerance_seconds=60) -> dict:
    """Consume each Python row at most once; duplicates cannot share a match."""
    used = set()
    pairs = []
    unmatched_oracle = []
    for oi, oz in enumerate(oracle):
        candidates = []
        for pi, pz in enumerate(python):
            if pi in used:
                continue
            if pz["lower_tick"] != oz["lower_tick"] or pz["upper_tick"] != oz["upper_tick"]:
                continue
            delta = abs((pz["time"] - oz["time"]).total_seconds())
            if delta <= tolerance_seconds:
                candidates.append((delta, pi))
        if not candidates:
            unmatched_oracle.append(_brief(oz))
            continue
        delta, pi = min(candidates)
        used.add(pi)
        pairs.append({"oracle_index": oi, "python_index": pi, "delta_seconds": delta})
    unmatched_python = [_brief(pz) for pi, pz in enumerate(python) if pi not in used]
    return {
        "matched": len(pairs),
        "pairs": pairs,
        "unmatched_oracle": unmatched_oracle,
        "unmatched_python": unmatched_python,
    }


def decide_p2(input_hash_ok: bool, p1a_status: str, diff: dict | None) -> str:
    if not input_hash_ok:
        return "ABSTAIN_INPUT"
    if p1a_status != "PASS" or diff is None:
        return "ABSTAIN_P2"
    if diff["unmatched_oracle"] or diff["unmatched_python"]:
        return "ABSTAIN_P2"
    return "P2_PASS"


def run(parquet_path: str | Path, oracle_path: str | Path) -> dict:
    parquet_path = Path(parquet_path)
    oracle_path = Path(oracle_path)
    actual_hash = sha256_file(parquet_path)
    hash_ok = actual_hash == EXPECTED_6E_09_26_SHA256
    meta, oracle_all = parse_oracle(oracle_path)
    oracle = [z for z in oracle_all if WINDOW_START <= z["time"] < WINDOW_END]

    base = {
        "schema_version": SCHEMA_VERSION,
        "label": "ABSTAIN_INPUT" if not hash_ok else "ABSTAIN_P2",
        "source_of_truth": {
            "nt8_cs": "nt8/aVolClusterPOI.cs",
            "nt8_git_blob": "d512d91a606d41609b21ef244c896ead1dc52a10",
            "oracle": str(oracle_path),
            "oracle_meta_instrument": meta.get("instrument"),
        },
        "input": {
            "parquet": str(parquet_path),
            "expected_sha256": EXPECTED_6E_09_26_SHA256,
            "actual_sha256": actual_hash,
            "hash_ok": hash_ok,
        },
        "window": {
            "timezone": TZ,
            "start_inclusive": WINDOW_START.isoformat(),
            "end_exclusive": WINDOW_END.isoformat(),
            "warmup": "all complete sessions available before window start",
        },
        "oracle_rows": len(oracle),
        "outcomes_accessed": False,
        "pnl_accessed": False,
        "holdout_included": False,
        "formal_race_executed": False,
    }
    if meta.get("instrument") != EXPECTED_INSTRUMENT_META:
        base["label"] = "ABSTAIN_INPUT"
        base["input"]["oracle_instrument_ok"] = False
        return seal_payload(base)
    base["input"]["oracle_instrument_ok"] = True
    if not hash_ok:
        return seal_payload(base)

    # IMPORTANT: load the full contract. Filtering before replay would remove
    # the history that NT8 had before the first exported zone.
    ticks = load_canonical_parquet(parquet_path, instrument="6E")
    python_all, p1a, diagnostics = replay_python_zones(ticks)
    python = [z for z in python_all if WINDOW_START <= z["time"] < WINDOW_END]
    diff = match_one_to_one(oracle, python, tolerance_seconds=60)
    label = decide_p2(True, p1a["status"], diff)
    base.update({
        "label": label,
        "p1a_gate": p1a,
        "python_rows": len(python),
        "p2_gate": {
            "p2_pass": label == "P2_PASS",
            "match_rule": "one-to-one exact (lower_tick,upper_tick), |dt|<=60s",
            "pass_rule": "P1A PASS AND zero unmatched oracle AND zero unmatched Python",
            "matched": diff["matched"],
            "match_rate_oracle": diff["matched"] / max(1, len(oracle)),
            "unmatched_oracle_count": len(diff["unmatched_oracle"]),
            "unmatched_python_count": len(diff["unmatched_python"]),
            "unmatched_oracle": diff["unmatched_oracle"],
            "unmatched_python": diff["unmatched_python"],
        },
        "replay_diagnostics": diagnostics,
    })
    return seal_payload(base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True, help="6E_09-26_ticks.parquet canónico")
    ap.add_argument("--oracle", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    payload = run(args.parquet, args.oracle)
    text = json.dumps(payload, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    print("LABEL:", payload["label"])


if __name__ == "__main__":
    main()
