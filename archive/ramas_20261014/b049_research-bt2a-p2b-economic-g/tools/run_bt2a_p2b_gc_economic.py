#!/usr/bin/env python3
"""P2-B económica GC: preflight sin outcomes y ejecución con autorización separada."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.research.all5_runtime.ticks import load_canonical_parquet  # noqa: E402
from edgelab.research.bt2_gate1_all5 import _context, _end, _labels, _start  # noqa: E402
from edgelab.research.bt2a_event_store import (  # noqa: E402
    canonical_sha256,
    file_sha256,
    validate_event_checkpoint,
    verify_file_sha256,
)
from edgelab.research.holdout_guard import check_holdout  # noqa: E402

SPEC_REL = "specs/bt2a_p2b_gc_economic_v1.json"
AUTH = "AUTHORIZE_BT2A_P2B_GC_ECONOMIC_V1"
BRANCH = "research/bt2a-p2b-economic-gc-v1-20260827"
EVENT_PAYLOAD = "602f8f18467f6be081f36e8fc08f5d7e703f510a088afeb480d0b27b5e678e1d"  # rebuilt fresh+complete on Kaggle 2026-08-29 (234/234 sessions, single consistent pass, matches EXPECTED counts exactly); see specs/bt2a_p2b_gc_economic_v1.json source_p2a.event_store_rebuild_note
BARRIERS = (5, 9, 18, 30)
HORIZONS = (25, 50, 100, 250)
SCENARIOS = {
    "base": {"spread_ticks": 1.0, "slippage_ticks": 2.0, "commission_ticks": 0.5, "all_in_ticks": 3.5},
    "adverse": {"spread_ticks": 1.0, "slippage_ticks": 4.0, "commission_ticks": 0.5, "all_in_ticks": 5.5},
}
HOLDOUT_NS = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1_000_000_000)
RTH_START = time(7, 20)
RTH_END = time(12, 30)
ALLOWED_MACRO = {"FOMC", "CPI", "NFP"}
BASE_SEED = 20260827


def canonical(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                              allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_spec(root: Path = ROOT) -> dict:
    value = json.loads((root / SPEC_REL).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("P2-B spec must be an object")
    return value


def frozen_checks(spec: dict) -> dict[str, bool]:
    family = spec.get("primary_family", {})
    costs = spec.get("costs", {})
    scenarios = costs.get("scenarios", {})
    firewall = spec.get("firewall", {})
    return {
        "schema": spec.get("schema") == "bt2a_p2b_gc_economic_v1",
        "status": spec.get("status") == "FROZEN_PREAUTHORIZATION",
        "preparation_only": spec.get("P2B_SPEC_PREPARATION") is True and spec.get("P2B_RUN") is False,
        "barriers": tuple(family.get("barriers_ticks", ())) == BARRIERS,
        "horizons": tuple(family.get("horizons_ticks", ())) == HORIZONS,
        "all_16_cells": int(family.get("n_cells", -1)) == 16 and family.get("evaluate_all_cells") is True,
        "no_winner": family.get("cross_cell_winner_selection_allowed") is False,
        "commission": float(costs.get("commission_and_fees_round_trip_usd", -1)) == 5.0,
        "spread": float(costs.get("spread_ticks_round_trip_assumption", -1)) == 1.0,
        "base_all_in": float(scenarios.get("base", {}).get("all_in_friction_ticks_including_spread", -1)) == 3.5,
        "adverse_all_in": float(scenarios.get("adverse", {}).get("all_in_friction_ticks_including_spread", -1)) == 5.5,
        "holdout_closed": firewall.get("HOLDOUT_TOUCHED") is False,
        "pnl_closed": firewall.get("PNL_ACCESSED_BY_PREPARATION") is False,
        "execution_closed": firewall.get("P2B_RUN") is False,
        "authorization": spec.get("authorization", {}).get("execution_token") == AUTH,
        "event_identity": spec.get("source_p2a", {}).get("event_store_payload_sha256") == EVENT_PAYLOAD,
    }


def _iso_ns(text: str) -> int:
    dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000_000)


def load_macro_calendar(path: Path, expected_sha256: str) -> tuple[dict, list[tuple[int, int]]]:
    actual = file_sha256(path)
    if not expected_sha256 or actual.lower() != expected_sha256.lower():
        raise RuntimeError("ABSTAIN_MACRO_CALENDAR_SHA256_MISMATCH_OR_UNBOUND")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "bt2a_macro_calendar_v1" or not isinstance(value.get("events"), list):
        raise RuntimeError("ABSTAIN_INVALID_MACRO_CALENDAR_SCHEMA")
    ids = set()
    intervals = []
    for event in value["events"]:
        event_id = str(event.get("event_id", ""))
        event_type = str(event.get("event_type", ""))
        if not event_id or event_id in ids or event_type not in ALLOWED_MACRO:
            raise RuntimeError("ABSTAIN_INVALID_MACRO_CALENDAR_EVENT")
        ids.add(event_id)
        start = _iso_ns(event["release_utc"])
        if start >= HOLDOUT_NS:
            raise RuntimeError("ABSTAIN_MACRO_CALENDAR_TOUCHES_HOLDOUT")
        intervals.append((start, start + 5 * 60 * 1_000_000_000))
    intervals.sort()
    return value, intervals


def is_macro_excluded(ts_ns: int, intervals: list[tuple[int, int]]) -> bool:
    return any(start <= int(ts_ns) < end for start, end in intervals)


def is_rth(ts_ns: int) -> bool:
    local = datetime.fromtimestamp(int(ts_ns) / 1_000_000_000, tz=timezone.utc).astimezone(
        ZoneInfo("America/Chicago")
    ).time()
    return RTH_START <= local < RTH_END


def scenario_cost(name: str) -> dict:
    if name not in SCENARIOS:
        raise KeyError(name)
    return dict(SCENARIOS[name])


def apply_cost(gross_ticks: float, scenario: str, tick_value_usd: float = 10.0) -> tuple[float, float]:
    cost = scenario_cost(scenario)
    net_ticks = float(gross_ticks) - float(cost["all_in_ticks"])
    return net_ticks, net_ticks * float(tick_value_usd)


def _trade_digest(trades: list[dict]) -> str:
    return canonical(trades)


def simulate_cell(*, signals: list[dict], ts_ns, price_ticks, source_row, barrier_ticks: int,
                  horizon_ticks: int, scenario: str,
                  macro_intervals: list[tuple[int, int]]) -> dict:
    ts = np.asarray(ts_ns, dtype=np.int64)
    price = np.asarray(price_ticks, dtype=np.int64)
    source = np.asarray(source_row, dtype=np.int64)
    if len(ts) != len(price) or len(ts) != len(source) or not len(ts):
        raise ValueError("invalid path arrays")
    if np.any(ts[1:] < ts[:-1]):
        raise ValueError("nonmonotone timestamps")
    if int(barrier_ticks) < 1 or int(horizon_ticks) < 1:
        raise ValueError("invalid cell")

    ordered = sorted(signals, key=lambda s: (
        int(s["entry_idx"]), int(s["signal_ts_utc_ns"]), str(s["event_id"])
    ))
    trades = []
    rejected = []
    open_until = -1
    macro_excluded = 0
    latency_outside = 0

    for signal in ordered:
        entry = int(signal["entry_idx"])
        direction = int(signal["direction"])
        if direction not in (-1, 1) or not 0 <= entry < len(ts):
            raise ValueError("invalid signal")
        if is_macro_excluded(int(signal["signal_ts_utc_ns"]), macro_intervals):
            macro_excluded += 1
            rejected.append({"event_id": str(signal["event_id"]), "reason": "macro_blackout"})
            continue
        if entry <= open_until:
            rejected.append({"event_id": str(signal["event_id"]), "reason": "position_open"})
            continue

        signal_ts = int(signal["signal_ts_utc_ns"])
        signal_row = int(signal["signal_source_row"])
        # Matches edgelab.research.bt2_gate1_outcomes.strict_next_index's own
        # guarantee: strictly after means the (ts, source_row) tuple, not ts
        # alone -- real tick data ties timestamps at nanosecond resolution and
        # source_row is the tie-break. entry_idx is already identity-verified
        # against the Event Store's fill_source_row/fill_ts_utc_ns/fill_price_ticks
        # in map_signals(); this is a defense-in-depth check and must use the same
        # ordering semantics as the code that produced entry_idx.
        if (int(ts[entry]), int(source[entry])) <= (signal_ts, signal_row):
            raise ValueError("entry is not strictly after signal")
        latency_ms = (int(ts[entry]) - signal_ts) / 1_000_000.0
        if not 100.0 <= latency_ms <= 250.0:
            latency_outside += 1

        entry_price = int(price[entry])
        target = entry_price + direction * int(barrier_ticks)
        stop = entry_price - direction * int(barrier_ticks)
        end = min(entry + int(horizon_ticks), len(ts) - 1)
        exit_idx = end
        exit_reason = "timeout"
        gross_ticks = float(direction * (int(price[end]) - entry_price))

        for index in range(entry + 1, end + 1):
            px = int(price[index])
            hit_target = px >= target if direction > 0 else px <= target
            hit_stop = px <= stop if direction > 0 else px >= stop
            if hit_target and hit_stop:
                exit_idx = index
                exit_reason = "stop_ambiguous"
                gross_ticks = float(direction * (px - entry_price))
                break
            if hit_stop:
                exit_idx = index
                exit_reason = "stop"
                gross_ticks = float(direction * (px - entry_price))
                break
            if hit_target:
                exit_idx = index
                exit_reason = "target"
                gross_ticks = float(barrier_ticks)
                break

        net_ticks, net_usd = apply_cost(gross_ticks, scenario)
        trades.append({
            "event_id": str(signal["event_id"]),
            "direction": direction,
            "entry_idx": entry,
            "entry_ts_utc_ns": int(ts[entry]),
            "exit_idx": int(exit_idx),
            "exit_ts_utc_ns": int(ts[exit_idx]),
            "exit_reason": exit_reason,
            "gross_ticks": gross_ticks,
            "spread_ticks": SCENARIOS[scenario]["spread_ticks"],
            "slippage_ticks": SCENARIOS[scenario]["slippage_ticks"],
            "commission_ticks": SCENARIOS[scenario]["commission_ticks"],
            "net_ticks": net_ticks,
            "net_usd": net_usd,
            "rth": is_rth(int(ts[entry])),
            "latency_ms": latency_ms,
        })
        open_until = exit_idx

    eligible = len(ordered) - macro_excluded
    net_ticks_total = float(sum(row["net_ticks"] for row in trades))
    net_usd_total = float(sum(row["net_usd"] for row in trades))
    rth_trades = [row for row in trades if row["rth"]]
    summary = {
        "barrier_ticks": int(barrier_ticks),
        "horizon_ticks": int(horizon_ticks),
        "scenario": scenario,
        "n_source_signals": len(ordered),
        "n_macro_excluded": macro_excluded,
        "n_eligible_signals": eligible,
        "n_trades": len(trades),
        "n_concurrency_rejected": sum(row["reason"] == "position_open" for row in rejected),
        "n_latency_outside_expected_band": latency_outside,
        "n_rth_trades": len(rth_trades),
        "net_ticks": net_ticks_total,
        "net_usd": net_usd_total,
        "mean_net_ticks_per_trade": net_ticks_total / len(trades) if trades else None,
        "mean_net_usd_per_trade": net_usd_total / len(trades) if trades else None,
        "mean_net_ticks_per_eligible_signal": net_ticks_total / eligible if eligible else None,
        "mean_net_usd_per_eligible_signal": net_usd_total / eligible if eligible else None,
        "rth_net_usd": float(sum(row["net_usd"] for row in rth_trades)),
        "exit_reasons": {reason: sum(row["exit_reason"] == reason for row in trades)
                         for reason in ("target", "stop", "stop_ambiguous", "timeout")},
        "trade_digest": _trade_digest(trades),
    }
    return {"trades": trades, "rejected": rejected, "summary": summary}


def map_signals(events: list[dict], ticks) -> list[dict]:
    source = np.asarray(ticks.sequence, dtype=np.int64)
    signals = []
    for event in events:
        if event.get("arm") != "K_ABS":
            continue
        fill_row = int(event["fill_source_row"])
        index = int(np.searchsorted(source, fill_row, side="left"))
        if index >= len(source) or int(source[index]) != fill_row:
            raise RuntimeError(f"fill_source_row absent: {event['event_id']}")
        if int(ticks.ts_ns[index]) != int(event["fill_ts_utc_ns"]):
            raise RuntimeError(f"fill timestamp mismatch: {event['event_id']}")
        if int(ticks.price_ticks[index]) != int(event["fill_price_ticks"]):
            raise RuntimeError(f"fill price mismatch: {event['event_id']}")
        signals.append({
            "event_id": str(event["event_id"]),
            "direction": int(event["direction"]),
            "signal_ts_utc_ns": int(event.get("signal_ts_utc_ns", event.get("ts_utc_ns"))),
            "signal_source_row": int(event.get("signal_source_row", event.get("source_row"))),
            "entry_idx": index,
        })
    return signals


def _find_manifest(event_store_dir: Path) -> Path | None:
    for name in ("run_manifest.json", "event_store_run_manifest.json", "manifest.json"):
        path = event_store_dir / name
        if path.is_file():
            return path
    return None


def _git_checks(root: Path) -> dict[str, bool]:
    def run(*args):
        return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    branch = run("branch", "--show-current")
    status = run("status", "--porcelain")
    return {
        "git_available": branch.returncode == 0,
        "branch": branch.returncode == 0 and branch.stdout.strip() == BRANCH,
        "worktree_clean": status.returncode == 0 and not status.stdout.strip(),
    }


def preflight(root: Path, event_store_dir: Path, data_dir: Path,
              macro_calendar: Path, macro_sha256: str,
              *, check_git: bool = True) -> dict:
    spec = load_spec(root)
    constants = frozen_checks(spec)
    registry, inputs, _ = _context(root)
    manifest_path = _find_manifest(event_store_dir)
    manifest_checks = {"manifest_exists": manifest_path is not None}
    if manifest_path is not None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_checks.update({
            "status": manifest.get("status") == "COMPLETE_RECONCILED_WITH_GATE1_ALL5",
            "events_payload": manifest.get("events_payload_sha256") == EVENT_PAYLOAD,
            "n_sessions": int(manifest.get("n_sessions", -1)) == 234,
            "n_events": int(manifest.get("n_events", -1)) == 22202,
        })
    missing = [index for index in range(234)
               if not (event_store_dir / "checkpoints" / f"session_{index:03d}.json").is_file()]
    files = {}
    for contract, entry in inputs["contracts"].items():
        files[contract] = (data_dir / entry["parquet_file"]).is_file()
    macro_checks = {"exists": macro_calendar.is_file(), "sha_bound": bool(macro_sha256)}
    if macro_calendar.is_file() and macro_sha256:
        try:
            calendar, _ = load_macro_calendar(macro_calendar, macro_sha256)
            macro_checks.update({"valid": True, "events": len(calendar["events"]) >= 0})
        except RuntimeError:
            macro_checks["valid"] = False
    git_checks = _git_checks(root) if check_git else {"skipped_for_test": True}
    sessions = registry["sessions"]
    sample_checks = {
        "n_sessions": len(sessions) == 234,
        "contracts": len({row["contract"] for row in sessions}) == 5,
        "pre_holdout": max(str(row["cme_session_id"]) for row in sessions) <= "20260630",
    }
    groups = (constants, manifest_checks, files, macro_checks, sample_checks, git_checks)
    ready = not missing and all(all(group.values()) for group in groups)
    return {
        "schema": "bt2a_p2b_gc_preflight_v1",
        "status": "PASS_READY_FOR_P2B_AUTHORIZATION" if ready else "NOT_READY",
        "spec_payload_sha256": canonical(spec),
        "frozen_constants": constants,
        "event_store_manifest": manifest_checks,
        "n_missing_event_checkpoints": len(missing),
        "missing_event_checkpoint_indices": missing[:50],
        "data_files_exist": files,
        "macro_calendar": macro_checks,
        "sample": sample_checks,
        "git": git_checks,
        "P2B_RUN": False,
        "PNL_ACCESSED": False,
        "FUTURE_PRICE_PATH_ACCESSED": False,
        "HOLDOUT_TOUCHED": False,
        "WINNER_SELECTED": False,
        "EDGE_DECLARED": False,
    }


def _session_checkpoint(output_dir: Path, index: int) -> Path:
    return output_dir / "checkpoints" / f"session_{index:03d}.json"


def run_session(*, root: Path, data_dir: Path, event_store_dir: Path,
                output_dir: Path, macro_calendar: Path, macro_sha256: str,
                index: int) -> dict:
    spec = load_spec(root)
    registry, inputs, _ = _context(root)
    row = registry["sessions"][int(index)]
    contract = str(row["contract"])
    session = str(row["cme_session_id"])
    start_iso = datetime.fromtimestamp(_start(session) / 1e9, timezone.utc).isoformat()
    end_iso = datetime.fromtimestamp(_end(session) / 1e9, timezone.utc).isoformat()
    check_holdout(start_iso, end_iso, purpose="development", caller="bt2a_p2b_gc_economic")

    source_path = event_store_dir / "checkpoints" / f"session_{index:03d}.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    events = validate_event_checkpoint(
        source, contract=contract, session=session,
        sample_registry_sha256=registry["registry_payload_sha256"],
        input_registry_sha256=inputs["registry_payload_sha256"],
    )
    parquet = data_dir / inputs["contracts"][contract]["parquet_file"]
    verify_file_sha256(parquet, inputs["contracts"][contract]["parquet_sha256"])
    ticks = load_canonical_parquet(
        parquet, contract=contract, instrument="GC",
        start_utc_ns=_start(session), end_utc_ns=_end(session),
    )
    if len(ticks) == 0 or int(ticks.ts_ns[-1]) >= HOLDOUT_NS:
        raise RuntimeError("HOLDOUT_OR_EMPTY_PATH_DETECTED")
    labels = _labels(ticks.ts_ns)
    if set(labels.tolist()) != {session}:
        raise RuntimeError("foreign session in price path")
    signals = map_signals(events, ticks)
    _, intervals = load_macro_calendar(macro_calendar, macro_sha256)

    cells = []
    for barrier in BARRIERS:
        for horizon in HORIZONS:
            for scenario in ("base", "adverse"):
                result = simulate_cell(
                    signals=signals, ts_ns=ticks.ts_ns,
                    price_ticks=ticks.price_ticks, source_row=ticks.sequence,
                    barrier_ticks=barrier,
                    horizon_ticks=horizon, scenario=scenario,
                    macro_intervals=intervals,
                )
                cells.append(result["summary"])
    value = {
        "schema": "bt2a_p2b_gc_session_v1",
        "status": "COMPLETE_P2B_AUTHORIZED_SESSION",
        "session_index": int(index),
        "contract": contract,
        "cme_session": session,
        "spec_payload_sha256": canonical(spec),
        "source_event_checkpoint_sha256": canonical_sha256(source),
        "macro_calendar_file_sha256": macro_sha256.lower(),
        "n_K_ABS": len(signals),
        "cells": cells,
        "P2B_RUN": True,
        "PNL_ACCESSED": True,
        "HOLDOUT_TOUCHED": False,
        "WINNER_SELECTED": False,
        "EDGE_DECLARED": False,
    }
    value["payload_sha256"] = canonical(value)
    atomic_json(_session_checkpoint(output_dir, index), value)
    return value


def _seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{BASE_SEED}|{label}".encode()).digest()[:8], "little") % (2**32 - 1)


def _inference(values: list[float], label: str, replications: int = 10000) -> dict:
    x = np.asarray(values, dtype=float)
    if not len(x) or not np.all(np.isfinite(x)):
        raise RuntimeError("invalid session estimands")
    rng = np.random.default_rng(_seed(label))
    indices = rng.integers(0, len(x), size=(replications, len(x)))
    boot = x[indices].mean(axis=1)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(replications, len(x)))
    null = (signs * x).mean(axis=1)
    point = float(x.mean())
    p_one = float((1 + np.sum(null >= point)) / (replications + 1))
    return {
        "point": point,
        "lower_95": float(np.quantile(boot, 0.025)),
        "upper_95": float(np.quantile(boot, 0.975)),
        "p_one_sided": p_one,
        "n_sessions": len(x),
        "replications": replications,
    }


def holm(pvalues: list[float]) -> list[float]:
    order = np.argsort(np.asarray(pvalues, dtype=float))
    adjusted = np.empty(len(pvalues), dtype=float)
    running = 0.0
    m = len(pvalues)
    for rank, index in enumerate(order):
        running = max(running, (m - rank) * float(pvalues[int(index)]))
        adjusted[int(index)] = min(1.0, running)
    return adjusted.tolist()


def finalize(*, root: Path, output_dir: Path, macro_sha256: str) -> dict:
    spec = load_spec(root)
    spec_sha = canonical(spec)
    rows = []
    for index in range(234):
        path = _session_checkpoint(output_dir, index)
        if not path.is_file():
            raise RuntimeError(f"missing P2-B checkpoint {index}")
        value = json.loads(path.read_text(encoding="utf-8"))
        payload = value.pop("payload_sha256", None)
        if payload != canonical(value):
            raise RuntimeError(f"invalid checkpoint payload {index}")
        value["payload_sha256"] = payload
        if value.get("spec_payload_sha256") != spec_sha or value.get("macro_calendar_file_sha256") != macro_sha256.lower():
            raise RuntimeError(f"stale checkpoint {index}")
        rows.append(value)

    results = []
    for scenario in ("base", "adverse"):
        family = []
        for barrier in BARRIERS:
            for horizon in HORIZONS:
                cells = [next(cell for cell in row["cells"]
                              if cell["scenario"] == scenario
                              and cell["barrier_ticks"] == barrier
                              and cell["horizon_ticks"] == horizon) for row in rows]
                values = [cell["mean_net_usd_per_eligible_signal"] for cell in cells]
                if any(value is None for value in values):
                    raise RuntimeError("session without eligible K_ABS signal")
                inf = _inference(values, f"{scenario}|{barrier}|{horizon}")
                family.append({
                    "barrier_ticks": barrier,
                    "horizon_ticks": horizon,
                    "scenario": scenario,
                    "p2a_positive_annotation": (barrier, horizon) in {(9, 25), (30, 100), (30, 250)},
                    "net_usd_per_eligible_signal_equal_session": inf,
                    "n_source_signals": int(sum(cell["n_source_signals"] for cell in cells)),
                    "n_trades": int(sum(cell["n_trades"] for cell in cells)),
                    "n_macro_excluded": int(sum(cell["n_macro_excluded"] for cell in cells)),
                    "n_concurrency_rejected": int(sum(cell["n_concurrency_rejected"] for cell in cells)),
                })
        adjusted = holm([cell["net_usd_per_eligible_signal_equal_session"]["p_one_sided"] for cell in family])
        for cell, p_holm in zip(family, adjusted):
            cell["net_usd_per_eligible_signal_equal_session"]["p_holm_16"] = p_holm
            estimate = cell["net_usd_per_eligible_signal_equal_session"]
            cell["supported"] = estimate["lower_95"] > 0 and p_holm <= 0.05
        results.extend(family)

    robust = []
    fragile = []
    for barrier in BARRIERS:
        for horizon in HORIZONS:
            base = next(row for row in results if row["scenario"] == "base" and row["barrier_ticks"] == barrier and row["horizon_ticks"] == horizon)
            adverse = next(row for row in results if row["scenario"] == "adverse" and row["barrier_ticks"] == barrier and row["horizon_ticks"] == horizon)
            if base["supported"] and adverse["supported"]:
                robust.append({"barrier_ticks": barrier, "horizon_ticks": horizon})
            elif base["supported"]:
                fragile.append({"barrier_ticks": barrier, "horizon_ticks": horizon})
    if robust:
        classification = "P2B_DIAGNOSTIC_ECONOMIC_ROBUST_CELL_EXISTS"
    elif fragile:
        classification = "P2B_DIAGNOSTIC_ECONOMIC_BASE_ONLY"
    else:
        classification = "P2B_DIAGNOSTIC_EXECUTION_NEGATIVE"
    final = {
        "schema": "bt2a_p2b_gc_economic_result_v1",
        "status": "COMPLETE_P2B_AUTHORIZED_POST_OUTCOME_DIAGNOSTIC",
        "classification": classification,
        "n_sessions": 234,
        "family": results,
        "robust_cells": robust,
        "base_only_cells": fragile,
        "winner_selected": None,
        "spec_payload_sha256": spec_sha,
        "macro_calendar_file_sha256": macro_sha256.lower(),
        "P2B_RUN": True,
        "PNL_ACCESSED": True,
        "HOLDOUT_TOUCHED": False,
        "WINNER_SELECTED": False,
        "EDGE_DECLARED": False,
        "confirmatory_eligible": False,
        "promotion_eligible": False,
    }
    final["payload_sha256"] = canonical(final)
    atomic_json(output_dir / "bt2a_p2b_gc_economic_result.json", final)
    return final


def require_authorization(token: str | None) -> None:
    if token != AUTH:
        raise SystemExit("ABSTAIN_MISSING_EXPLICIT_P2B_AUTHORIZATION")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--event-store-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--macro-calendar", type=Path, required=True)
    parser.add_argument("--macro-calendar-sha256", required=True)
    parser.add_argument("--output-dir", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--session-index", type=int)
    modes.add_argument("--finalize", action="store_true")
    parser.add_argument("--authorization-token")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    readiness = preflight(
        root, args.event_store_dir.resolve(), args.data_dir.resolve(),
        args.macro_calendar.resolve(), args.macro_calendar_sha256,
    )
    if args.preflight_only:
        print(json.dumps(readiness, indent=2, sort_keys=True))
        return 0 if readiness["status"] == "PASS_READY_FOR_P2B_AUTHORIZATION" else 2
    require_authorization(args.authorization_token)
    if readiness["status"] != "PASS_READY_FOR_P2B_AUTHORIZATION":
        raise SystemExit("ABSTAIN_P2B_PREFLIGHT_NOT_READY")
    if args.output_dir is None:
        raise SystemExit("--output-dir required")
    output = args.output_dir.resolve()
    if args.finalize:
        result = finalize(root=root, output_dir=output,
                          macro_sha256=args.macro_calendar_sha256)
    else:
        if args.session_index is None or not 0 <= args.session_index < 234:
            raise SystemExit("ABSTAIN_SESSION_INDEX_OUT_OF_RANGE")
        result = run_session(
            root=root, data_dir=args.data_dir.resolve(),
            event_store_dir=args.event_store_dir.resolve(), output_dir=output,
            macro_calendar=args.macro_calendar.resolve(),
            macro_sha256=args.macro_calendar_sha256,
            index=args.session_index,
        )
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {"cells", "family"}}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
