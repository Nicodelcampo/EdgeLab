# -*- coding: utf-8 -*-
"""ZAMR-1 Z1 builder: BigTrap2 defaults, six tick frames, no outcomes/P&L/holdout."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.bridge import bars as bars_mod
from edgelab.bridge import ticks as ticks_mod
from edgelab.bridge.indicators import bigtrap2
from edgelab.research.zamr1.parameter_dag import param_set_id, validate_param_set
from edgelab.research.zamr1.session_clock import session_date_cme
from edgelab.research.zamr1.structural_contract import validate_structural_dataset

FRAMES = (5, 10, 25, 50, 100, 200)
CUTOFF = 1_782_856_800_000_000_000
BUILDER_ID = "zamr1_z1_bigtrap2_defaults_v2"
SCHEMA = "zamr1_structural_contract_v0"
ZONE_EVENTS = {"ZONE_CREATED", "ZONE_TOUCHED", "ZONE_INVALIDATED", "ZONE_EXPIRED"}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def obj_hash(payload) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def payloads(lines):
    parsed = {}
    for line in lines or []:
        seq, _iso, event_type, raw = line.split("|", 3)
        fields = {}
        for item in raw.split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                fields[key] = value
        parsed[int(seq)] = (event_type, fields)
    return parsed


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def tick_bounds_from_price(top, bottom, tick_size):
    """Inverse of BigTrap2 half-tick padding. Do not use banker's round on price/tick_size."""
    half = float(tick_size) / 2.0
    lo_half = int(round(float(bottom) / half))
    hi_half = int(round(float(top) / half))
    lo_tick = (lo_half + 1) // 2
    hi_tick = (hi_half - 1) // 2
    if lo_tick > hi_tick:
        raise RuntimeError("geometria invertida: lo=%s hi=%s" % (lo_tick, hi_tick))
    return lo_tick, hi_tick


def resolve_provenance(root: Path) -> tuple[str, bool]:
    try:
        head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        dirty = bool(subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"], text=True
        ).strip())
        return head, dirty
    except Exception:
        pass
    commit = os.environ.get("EDGELAB_CODE_COMMIT") or ""
    commit_file = root / "CODE_COMMIT"
    if commit_file.is_file():
        commit = commit_file.read_text("utf-8").strip() or commit
    dirty_raw = os.environ.get("EDGELAB_CODE_DIRTY", "true").strip().lower()
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit.lower()):
        raise RuntimeError("ABSTAIN_PROVENANCE: no git and no valid EDGELAB_CODE_COMMIT/CODE_COMMIT")
    if dirty_raw not in {"false", "0", "no"}:
        raise RuntimeError("ABSTAIN_PROVENANCE: offline provenance must set EDGELAB_CODE_DIRTY=false")
    return commit.lower(), False


def transform(result, bars, tk, sessions, rid, pid):
    parsed = payloads(result.get("csv_lines"))
    meta = {}
    for zone in result.get("zones") or []:
        created_bar = int(zone["created_bar"])
        created_ns = int(bars.end_ns[created_bar])
        session = session_date_cme(created_ns)
        if session not in sessions:
            continue
        lo_tick, hi_tick = tick_bounds_from_price(zone.get("top"), zone.get("bottom"), tk.tick_size)
        meta[str(zone["id"])] = {
            "zone": zone,
            "created_bar": created_bar,
            "created_ns": created_ns,
            "session": session,
            "lo": lo_tick,
            "hi": hi_tick,
            "side": str(zone.get("kind")),
        }

    events = []
    for event in result.get("events") or []:
        zone_id = str(event.get("zone_id"))
        event_type = str(event.get("type"))
        if zone_id not in meta or event_type not in ZONE_EVENTS:
            continue
        item = meta[zone_id]
        event_ns = int(event["ts_ns"])
        bar_index = int(event["bar_index"])
        if event_ns >= CUTOFF or int(bars.end_ns[bar_index]) >= CUTOFF:
            raise RuntimeError("FIREWALL event")
        volume = as_float(parsed.get(int(event["seq"]), (event_type, {}))[1].get("vol"))
        session_key = "%s|%s|%s" % (tk.instrument, tk.contract, item["session"])
        event_id = str(event["seq"])
        events.append({
            "event_key": "%s|%s" % (rid, event_id),
            "session_key": session_key,
            "instrument": tk.instrument,
            "contract": tk.contract,
            "session_date": item["session"],
            "indicator_id": "BigTrap2",
            "indicator_version": "2.2",
            "bar_spec": "tick:%d" % bars.param,
            "ticks_per_bar": int(bars.param),
            "param_set_id": pid,
            "source_run_id": rid,
            "event_id": event_id,
            "zone_id": zone_id,
            "event_type": event_type,
            "side": item["side"],
            "event_time_ns": event_ns,
            "bar_end_ns": int(bars.end_ns[bar_index]),
            "available_at_ns": int(bars.end_ns[bar_index]),
            "anchor_price_tick": int(bars.close_t[item["created_bar"]]),
            "zone_lo_tick": item["lo"],
            "zone_hi_tick": item["hi"],
            "strength": volume,
            "aggressive_volume": volume,
            "bar_volume": float(bars.volume[item["created_bar"]]),
            "oracle_parity_status": "NOT_ESTABLISHED",
        })

    zones = []
    for zone_id, item in meta.items():
        zone = item["zone"]
        ended_ns = None if zone.get("ended_ms") is None else int(zone["ended_ms"]) * 1_000_000
        if ended_ns is not None and ended_ns >= CUTOFF:
            raise RuntimeError("FIREWALL zone")
        created_event = next(
            (row for row in events if row["zone_id"] == zone_id and row["event_type"] == "ZONE_CREATED"),
            None,
        )
        session_key = "%s|%s|%s" % (tk.instrument, tk.contract, item["session"])
        zones.append({
            "zone_key": "%s|%s" % (rid, zone_id),
            "session_key": session_key,
            "instrument": tk.instrument,
            "contract": tk.contract,
            "session_date": item["session"],
            "indicator_id": "BigTrap2",
            "indicator_version": "2.2",
            "bar_spec": "tick:%d" % bars.param,
            "ticks_per_bar": int(bars.param),
            "param_set_id": pid,
            "source_run_id": rid,
            "zone_id": zone_id,
            "side": item["side"],
            "created_at_ns": item["created_ns"],
            "available_at_ns": item["created_ns"],
            "ended_at_ns": ended_ns,
            "state": zone.get("state"),
            "end_reason": zone.get("end_reason"),
            "zone_lo_tick": item["lo"],
            "zone_hi_tick": item["hi"],
            "strength": None if created_event is None else created_event["strength"],
            "touch_count": int(zone.get("touches") or 0),
            "oracle_parity_status": "NOT_ESTABLISHED",
        })
    return events, zones


def build(plan_path, data_root, out_dir, root):
    root = Path(root)
    plan = json.loads(Path(plan_path).read_text("utf-8"))
    contract = json.loads((root / "specs/zamr1_structural_contract_v0.json").read_text("utf-8"))
    head, dirty = resolve_provenance(root)
    if dirty:
        raise RuntimeError("ABSTAIN_PROVENANCE: dirty tree")
    if tuple(plan["bar_specs_ticks"]) != FRAMES:
        raise RuntimeError("Z1 scope altered")
    if validate_param_set("BigTrap2", {}):
        raise RuntimeError("BigTrap2 defaults rejected")
    if plan.get("session_definition") != "cme_eth_1700_america_chicago":
        raise RuntimeError("Z1 plan must pin session_definition=cme_eth_1700_america_chicago")
    sessions = [session for source in plan["sources"] for session in source["selected_sessions"]]
    if len(sessions) != len(set(sessions)) or not 20 <= len(sessions) <= 30:
        raise RuntimeError("need 20-30 unique sessions")

    param_id = param_set_id("BigTrap2", {})
    events = []
    zones = []
    units = []
    sources = []
    for source in plan["sources"]:
        path = Path(data_root) / source["filename"]
        digest = file_hash(path)
        if digest != source["sha256"]:
            raise RuntimeError("hash mismatch %s" % path.name)
        end_ns = min(int(source["load_end_utc_ns"]), CUTOFF)
        series = ticks_mod.load_canonical_parquet(
            str(path),
            start_utc_ns=int(source["load_start_utc_ns"]),
            end_utc_ns=end_ns,
        )
        if not len(series) or int(np.max(series.ts_ns)) >= CUTOFF:
            raise RuntimeError("invalid/cutoff ticks %s" % path.name)
        if not bool((np.diff(series.sequence) > 0).all()):
            raise RuntimeError("sequence is not a total order: %s" % path.name)
        sources.append({
            "filename": path.name,
            "sha256": digest,
            "rows_loaded": len(series),
            "max_ts_ns": int(np.max(series.ts_ns)),
            "warmup_note": source.get("warmup_note"),
        })
        for ticks_per_bar in FRAMES:
            started = time.perf_counter()
            bars = bars_mod.build_tick_bars(series, ticks_per_bar, reiniciar_por_sesion=True)
            footprints = bars_mod.build_footprints(series, bars)
            gate = bars_mod.p1a_gate(series, bars, footprints)
            if gate["status"] != "PASS":
                raise RuntimeError("P1A FAIL %s tick:%s: %s" % (path.name, ticks_per_bar, gate))
            result = bigtrap2.run(
                series, bars, footprints, params={}, chart_tz="America/Argentina/Buenos_Aires"
            )
            run_id = obj_hash({
                "source": digest,
                "contract": series.contract,
                "frame": ticks_per_bar,
                "params": param_id,
            })
            event_rows, zone_rows = transform(
                result, bars, series, set(source["selected_sessions"]), run_id, param_id
            )
            events.extend(event_rows)
            zones.extend(zone_rows)
            units.append({
                "file": path.name,
                "bar_spec": "tick:%d" % ticks_per_bar,
                "ticks": len(series),
                "bars": len(bars),
                "events": len(event_rows),
                "zones": len(zone_rows),
                "seconds": round(time.perf_counter() - started, 6),
                "ru_maxrss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            })

    events_df = pd.DataFrame(events)
    zones_df = pd.DataFrame(zones)
    instrument = plan["instrument_manifest"]
    missing_sessions = sorted(set(sessions) - set(zones_df.get("session_date", pd.Series(dtype=str))))
    if missing_sessions:
        raise RuntimeError("P-01 SIN_ZONAS in selected sessions: %s" % missing_sessions)
    manifest = {
        "dataset_id": obj_hash({
            "builder": BUILDER_ID,
            "sources": sources,
            "sessions": sessions,
            "commit": head,
        }),
        "dataset_schema_version": SCHEMA,
        "code_commit": head,
        "code_dirty": False,
        "builder_id": BUILDER_ID,
        "source_data_manifest_sha256": obj_hash(sources),
        "parameter_registry_sha256": file_hash(root / "specs/zamr1_parameter_registry_v0.json"),
        "instrument_manifest_sha256": obj_hash(instrument),
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "research_cutoff_utc": "2026-06-30T22:00:00Z",
        "session_definition": "cme_eth_1700_america_chicago",
        "outcomes_accessed": False,
        "pnl_accessed": False,
        "holdout_included": False,
        "license_decision": "NO_UPLOAD",
        "operational_override": "USER_RISK_ACCEPTANCE_NOT_LICENSE_PERMISSION",
        "pilot_stage": "Z1_BIGTRAP2_DEFAULTS",
    }
    report = validate_structural_dataset(
        manifest=manifest, events=events_df, zones=zones_df, contract=contract
    )
    if not report.passed:
        raise RuntimeError(json.dumps(report.to_dict(), ensure_ascii=False))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    events_path = out / "events_long.parquet"
    zones_path = out / "zones_long.parquet"
    events_df.to_parquet(events_path, index=False)
    zones_df.to_parquet(zones_path, index=False)
    artifacts = {path.name: file_hash(path) for path in (events_path, zones_path)}
    outputs = {
        "dataset_manifest.json": manifest,
        "source_data_manifest.json": sources,
        "instrument_manifest.json": instrument,
        "contract_validation_report.json": report.to_dict(),
        "resource_report.json": {"units": units, "artifacts": artifacts},
    }
    for name, payload in outputs.items():
        (out / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return {
        "passed": True,
        "sessions": len(set(sessions)),
        "events": len(events_df),
        "zones": len(zones_df),
        "artifacts": artifacts,
        "builder_id": BUILDER_ID,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    print(json.dumps(build(args.plan, args.data_root, args.out_dir, args.repo_root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
