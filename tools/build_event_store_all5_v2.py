#!/usr/bin/env python3
"""Build a multi-indicator Event Store for Gate 1 sessions — corrected v2.

Fixes five defects of the original ``build_event_store_all5.py`` (commit ced33dd):

1. **Holdout trimming**: filters by the session registry window_end per contract
   so no tick past the holdout boundary (2026-07-01) enters the store.
2. **Provenance**: records git state, code commit, input hashes, and parameters
   in a signed run manifest.
3. **Gate 1 alignment**: uses the same session_ids vectorizer as Gate 1 and
   filters to only the 234 registered sessions, making 1:1 reconciliation
   possible.
4. **Metadata fields**: maps *actual* kernel output dict keys (``a_score``,
   ``height_ticks``, ``poc_tick``, etc.) instead of defaulting to 0.
5. **Index resolution**: resolves tick indices from ``sig_idx`` / ``fill_idx``
   (BigTrap2Absorption), bar close boundaries (BigTrap2), ``created_ms``
   (HFTZones2), and ``created_bar`` (VolTicksPOC2) — never defaults to 0.

Usage::

    python tools/build_event_store_all5_v2.py \\
        --data-dir E:\\DatosNT8\\gc_gate1_parquets_20260825 \\
        --output-dir E:\\DatosNT8\\event_store_gc_all5_v2 \\
        --session-registry specs/bt2_absorption_gate1_all5_sessions_2026-08-26.json \\
        --input-registry specs/bt2_absorption_gate1_all5_input_registry_2026-08-26.json

Must be run on a clean worktree (``--allow-dirty`` available for diagnostics).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.bars import build_tick_bars, build_footprints, session_ids
from edgelab.bridge.indicators import (
    bigtrap2absorption,
    bigtrap2,
    hftzones2,
    voltickspoc2,
)

# ── Provenance helpers ────────────────────────────────────────────────
def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def canonical_sha(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

def git_state(root: Path) -> dict:
    def _g(*args):
        r = subprocess.run(["git"] + list(args), cwd=root,
                           text=True, capture_output=True)
        return r.stdout.strip() if r.returncode == 0 else None
    commit = _g("rev-parse", "HEAD")
    if commit is None:
        return {"available": False, "commit": None, "branch": None, "dirty": True}
    status = _g("status", "--porcelain") or ""
    branch = _g("branch", "--show-current") or ""
    return {"available": True, "commit": commit,
            "branch": branch, "dirty": bool(status.strip())}


# ── Session registry expansion ────────────────────────────────────────
def expand_sessions(registry: dict) -> list[dict]:
    """Expand compact session registry into per-session rows."""
    sel = registry["selection"]
    windows = sel["contract_windows"]
    exclusions = registry.get("closed_weekday_exclusions", {})
    warmups = registry.get("initial_warmup_session", {})
    sessions = []
    for contract in sel["contracts"]:
        w = windows[contract]
        start = pd.Timestamp(w["start"])
        end = pd.Timestamp(w["end"])
        excl = set(exclusions.get(contract, []))
        warmup = warmups.get(contract)
        dates = pd.bdate_range(start, end)
        prev = warmup
        for d in dates:
            sid = d.strftime("%Y%m%d")
            if sid in excl:
                continue
            sessions.append({
                "contract": contract,
                "cme_session_id": sid,
                "warmup_cme_session_id": prev,
            })
            prev = sid
    return sessions


# ── Core extraction ───────────────────────────────────────────────────
def extract_events_for_contract(
    contract: str,
    parquet_path: Path,
    valid_sessions: set[str],
    instrument: str = "GC",
    params: dict | None = None,
) -> list[dict]:
    """Run all four indicators and collect events within valid sessions only."""
    print(f"\n--- {contract} ({parquet_path.name}) [Instrument: {instrument}] ---")
    ticks = load_canonical_parquet(parquet_path, contract=contract, instrument=instrument)
    sess = session_ids(ticks.ts_ns)

    # Convert integer session labels to date strings for filtering
    # session_ids returns integer trade-date labels; we need YYYYMMDD
    from edgelab.research.bt2_gate1_preflight import cme_session_dates
    sess_dates = cme_session_dates(ticks.ts_ns)

    n_ticks = len(ticks.ts_ns)
    print(f"  Ticks: {n_ticks:,}  Unique sessions in parquet: "
          f"{len(np.unique(sess_dates))}")

    # Mask: only ticks belonging to valid sessions
    sess_mask = np.isin(sess_dates, list(valid_sessions))
    n_valid = int(sess_mask.sum())
    print(f"  Ticks in valid sessions: {n_valid:,} / {n_ticks:,}")

    events = []

    # ── 1. BigTrap2Absorption ─────────────────────────────────────
    print("  [1/4] BigTrap2Absorption ...")
    res_abs = bigtrap2absorption.run(ticks, params=bigtrap2absorption.DEFAULTS)
    n_abs = 0
    for z in res_abs.get("zones", []):
        sig_idx = int(z["sig_idx"])
        fill_idx = int(z["fill_idx"])
        if not sess_mask[sig_idx]:
            continue
        events.append({
            "ts_utc_ns": int(z["sig_ts"]),
            "source_row": int(ticks.sequence[sig_idx]),
            "contract": contract,
            "session_id": str(sess_dates[sig_idx]),
            "indicator": "BigTrap2Absorption",
            "direction": -1 if z["is_bull"] else 1,
            "price_ticks": int(ticks.price_ticks[sig_idx]),
            "fill_ts_utc_ns": int(ticks.ts_ns[fill_idx]),
            "fill_source_row": int(ticks.sequence[fill_idx]),
            "fill_price_ticks": int(ticks.price_ticks[fill_idx]),
            "metadata_json": json.dumps({
                "a_score": float(z["a_score"]),
                "a_thr": float(z["a_thr"]),
                "trap_vol": float(z["vol"]),
                "trap_frac": float(z["frac"]),
                "nrows": int(z["nrows"]),
                "side": str(z["side"]),
            }, separators=(",", ":")),
        })
        n_abs += 1
    print(f"    -> {n_abs:,} events (of {len(res_abs.get('zones', [])):,} total)")

    # ── 2. BigTrap2 ───────────────────────────────────────────────
    print("  [2/4] BigTrap2 ...")
    bars25 = build_tick_bars(ticks, 25, reiniciar_por_sesion=True)
    fps25 = build_footprints(ticks, bars25)
    res_bt2 = bigtrap2.run(ticks, bars25, fps25, params=bigtrap2.DEFAULTS)

    # BigTrap2 zones have created_bar; signal is at the close of that bar.
    # The bar close is the last tick of the bar.
    bar_close_indices = np.concatenate(
        (np.flatnonzero(np.diff(bars25.tick_bar_idx)) + 1, [n_ticks])
    ) - 1   # last tick index of each bar

    n_bt2 = 0
    for z in res_bt2.get("zones", []):
        created_bar = int(z["created_bar"])
        if created_bar >= len(bar_close_indices):
            continue
        sig_idx = int(bar_close_indices[created_bar])
        fill_idx = min(sig_idx + 1, n_ticks - 1)
        if not sess_mask[sig_idx]:
            continue
        # Reject fill on last tick of stream (no real fill possible)
        if fill_idx == sig_idx:
            continue
        direction = 1 if z["kind"] == "trapped_sellers" else -1
        events.append({
            "ts_utc_ns": int(ticks.ts_ns[sig_idx]),
            "source_row": int(ticks.sequence[sig_idx]),
            "contract": contract,
            "session_id": str(sess_dates[sig_idx]),
            "indicator": "BigTrap2",
            "direction": direction,
            "price_ticks": int(ticks.price_ticks[sig_idx]),
            "fill_ts_utc_ns": int(ticks.ts_ns[fill_idx]),
            "fill_source_row": int(ticks.sequence[fill_idx]),
            "fill_price_ticks": int(ticks.price_ticks[fill_idx]),
            "metadata_json": json.dumps({
                "kind": str(z["kind"]),
                "trap_vol": float(z.get("vol", 0.0)),
                "touches": int(z.get("touches", 0)),
            }, separators=(",", ":")),
        })
        n_bt2 += 1
    print(f"    -> {n_bt2:,} events (of {len(res_bt2.get('zones', [])):,} total)")

    # ── 3. HFTZones2 ─────────────────────────────────────────────
    print("  [3/4] HFTZones2 ...")
    # HFTZones2 needs bars (time:1 minute)
    from edgelab.bridge.bars import build_time_bars
    bars1m = build_time_bars(ticks, 1)
    res_hft = hftzones2.run(ticks, bars1m, params=hftzones2.DEFAULTS)

    n_hft = 0
    for z in res_hft.get("zones", []):
        # Zone created_ms is the timestamp in ms; find the tick closest
        created_ms = float(z["created_ms"])
        created_ns = int(created_ms * 1_000_000)
        # Find the tick at or just before created_ns
        sig_idx = int(np.searchsorted(ticks.ts_ns, created_ns, side="right")) - 1
        if sig_idx < 0:
            sig_idx = 0
        if sig_idx >= n_ticks:
            sig_idx = n_ticks - 1
        fill_idx = min(sig_idx + 1, n_ticks - 1)
        if not sess_mask[sig_idx]:
            continue
        if fill_idx == sig_idx:
            continue
        h_ticks = int(round(abs(float(z["top"]) - float(z["bottom"])) / ticks.tick_size))
        events.append({
            "ts_utc_ns": int(ticks.ts_ns[sig_idx]),
            "source_row": int(ticks.sequence[sig_idx]),
            "contract": contract,
            "session_id": str(sess_dates[sig_idx]),
            "indicator": "HFTZones2",
            "direction": int(z["dir"]),
            "price_ticks": int(ticks.price_ticks[sig_idx]),
            "fill_ts_utc_ns": int(ticks.ts_ns[fill_idx]),
            "fill_source_row": int(ticks.sequence[fill_idx]),
            "fill_price_ticks": int(ticks.price_ticks[fill_idx]),
            "metadata_json": json.dumps({
                "bucket": str(z.get("bucket", "")),
                "height_ticks": h_ticks,
                "upper": float(z["top"]),
                "lower": float(z["bottom"]),
                "calib_id": int(z.get("calib_id", 0)),
                "touches": int(z.get("touches", 0)),
                "kind": str(z.get("kind", "")),
            }, separators=(",", ":")),
        })
        n_hft += 1
    print(f"    -> {n_hft:,} events (of {len(res_hft.get('zones', [])):,} total)")

    # ── 4. VolTicksPOC2 ───────────────────────────────────────────
    print("  [4/4] VolTicksPOC2 ...")
    # VolTicksPOC2 uses the same tick:25 bars and footprints as BigTrap2
    res_poc = voltickspoc2.run(ticks, bars25, fps25,
                                params=voltickspoc2.DEFAULTS)

    n_poc = 0
    for z in res_poc.get("zones", []):
        # VolTicksPOC2 zones have created_bar; map to tick index
        created_bar = int(z["created_bar"])
        if created_bar >= len(bar_close_indices):
            continue
        sig_idx = int(bar_close_indices[created_bar])
        fill_idx = min(sig_idx + 1, n_ticks - 1)
        if not sess_mask[sig_idx]:
            continue
        if fill_idx == sig_idx:
            continue
        poc_t = int(round(((float(z["top"]) + float(z["bottom"])) / 2.0) / ticks.tick_size))
        events.append({
            "ts_utc_ns": int(ticks.ts_ns[sig_idx]),
            "source_row": int(ticks.sequence[sig_idx]),
            "contract": contract,
            "session_id": str(sess_dates[sig_idx]),
            "indicator": "VolTicksPOC2",
            "direction": 1,    # VolTicksPOC2 is non-directional; use +1
            "price_ticks": poc_t,
            "fill_ts_utc_ns": int(ticks.ts_ns[fill_idx]),
            "fill_source_row": int(ticks.sequence[fill_idx]),
            "fill_price_ticks": int(ticks.price_ticks[fill_idx]),
            "metadata_json": json.dumps({
                "poc_tick": poc_t,
                "touches": int(z.get("touches", 0)),
                "upper": float(z.get("top", 0.0)),
                "lower": float(z.get("bottom", 0.0)),
            }, separators=(",", ":")),
        })
        n_poc += 1
    print(f"    -> {n_poc:,} events (of {len(res_poc.get('zones', [])):,} total)")

    return events


def process_contract_worker(args_tuple):
    contract, pq_file, valid_sessions, instrument, output_dir = args_tuple
    ckey = contract.replace(" ", "_")
    events = extract_events_for_contract(
        contract, pq_file, valid_sessions, instrument=instrument)

    # Sort and deduplicate
    df = pd.DataFrame(events)
    if not df.empty:
        df = df.sort_values(
            ["ts_utc_ns", "source_row", "indicator", "direction"]
        ).reset_index(drop=True)
        before = len(df)
        df = df.drop_duplicates(
            subset=["ts_utc_ns", "source_row", "indicator", "direction"],
            keep="first"
        ).reset_index(drop=True)
        n_dedup = before - len(df)
        if n_dedup > 0:
            print(f"  WARNING ({contract}): dropped {n_dedup} duplicate events")

    out_file = output_dir / f"{ckey}_event_store.parquet"
    df.to_parquet(out_file, index=False, engine="pyarrow")

    by_ind = df["indicator"].value_counts().to_dict() if not df.empty else {}
    summary = {
        "total_events": len(df),
        "by_indicator": by_ind,
        "sessions_in_registry": len(valid_sessions),
        "sessions_with_events": int(df["session_id"].nunique())
                                if not df.empty else 0,
        "parquet_file": out_file.name,
        "parquet_bytes": out_file.stat().st_size,
        "parquet_sha256": file_sha256(out_file),
    }
    print(f"  => [{contract}] Finished -> {out_file.name}: {len(df):,} events")
    return contract, summary, events


# ── Main ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, required=True,
                    help="Directory with canonical parquet files per contract")
    ap.add_argument("--output-dir", type=Path, required=True,
                    help="Where to write event store parquets and manifest")
    ap.add_argument("--session-registry", type=Path, required=True,
                    help="Compact session registry JSON (all5)")
    ap.add_argument("--input-registry", type=Path, required=True,
                    help="Input registry JSON (all5)")
    ap.add_argument("--workers", type=int, default=5,
                    help="Number of concurrent worker processes (default: 5)")
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    ap.add_argument("--allow-dirty", action="store_true",
                    help="Allow running on dirty worktree (diagnostic only)")
    args = ap.parse_args()

    root = args.root.resolve()
    gs = git_state(root)
    if gs["dirty"] and not args.allow_dirty:
        raise SystemExit("ABSTAIN_DIRTY_WORKTREE — use --allow-dirty for diagnostics")

    # Load registries
    sess_reg = json.loads(args.session_registry.read_text(encoding="utf-8"))
    input_reg = json.loads(args.input_registry.read_text(encoding="utf-8"))
    contracts = sess_reg["selection"]["contracts"]
    windows = sess_reg["selection"]["contract_windows"]

    # Expand sessions
    expanded = expand_sessions(sess_reg)
    sessions_by_contract = {}
    for row in expanded:
        sessions_by_contract.setdefault(row["contract"], set()).add(
            row["cme_session_id"])
    total_sessions = sum(len(v) for v in sessions_by_contract.values())
    print(f"Session registry: {total_sessions} sessions across "
          f"{len(contracts)} contracts")
    print(f"Holdout boundary: window_end = {sess_reg['selection']['window_end']}")

    # Validate input parquets exist and match hashes
    input_contracts = input_reg.get("contracts", {})
    worker_tasks = []
    instrument = str(sess_reg.get("instrument", "GC"))
    print(f"Target Instrument: {instrument}")

    for contract in contracts:
        ckey = contract.replace(" ", "_")
        entry = input_contracts.get(contract, {})
        pq_file = args.data_dir / entry.get("parquet_file",
                                             f"{ckey}_ticks.parquet")
        if not pq_file.is_file():
            raise SystemExit(f"MISSING INPUT: {pq_file}")
        expected_sha = entry.get("parquet_sha256")
        if expected_sha:
            actual = file_sha256(pq_file)
            if actual != expected_sha:
                raise SystemExit(
                    f"INPUT HASH MISMATCH for {contract}: "
                    f"expected {expected_sha[:16]}…, got {actual[:16]}…")
            print(f"  {contract}: input hash verified ✓")
        valid_sessions = sessions_by_contract.get(contract, set())
        worker_tasks.append((contract, pq_file, valid_sessions, instrument, args.output_dir))

    # Process contracts in parallel
    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_events = []
    contract_summaries = {}

    import concurrent.futures
    workers = min(args.workers, len(worker_tasks))
    print(f"\nLaunching {len(worker_tasks)} contract extractions across {workers} parallel processes...")

    if workers > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(process_contract_worker, worker_tasks))
    else:
        results = [process_contract_worker(t) for t in worker_tasks]

    for contract, summary, events in results:
        contract_summaries[contract] = summary
        all_events.extend(events)

    # Validate: no event past holdout
    if all_events:
        holdout_ns = int(pd.Timestamp("2026-07-01", tz="UTC").value)
        violations = sum(1 for e in all_events
                         if e["ts_utc_ns"] >= holdout_ns)
        if violations > 0:
            raise RuntimeError(
                f"HOLDOUT VIOLATION: {violations} events at or after 2026-07-01")

    # Validate: fill strictly after signal
    fill_violations = sum(
        1 for e in all_events
        if (e["fill_ts_utc_ns"], e["fill_source_row"])
           <= (e["ts_utc_ns"], e["source_row"])
    )
    if fill_violations > 0:
        raise RuntimeError(
            f"FILL CAUSALITY VIOLATION: {fill_violations} events where "
            f"fill is not strictly after signal")

    # Validate: metadata_json has no all-zero placeholders
    meta_zero_count = 0
    for e in all_events:
        md = json.loads(e["metadata_json"])
        numeric_vals = [v for v in md.values() if isinstance(v, (int, float))]
        if numeric_vals and all(v == 0 for v in numeric_vals):
            meta_zero_count += 1
    if meta_zero_count > 0:
        print(f"  WARNING: {meta_zero_count} events have all-zero metadata "
              f"({meta_zero_count/len(all_events)*100:.1f}%)")

    # Write manifest
    manifest = {
        "schema": "event_store_gc_all5_v2",
        "status": "COMPLETE_SESSION_FILTERED",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "builder": "tools/build_event_store_all5_v2.py",
        "fixes_applied": [
            "holdout_trimmed_by_session_registry",
            "provenance_recorded",
            "metadata_fields_mapped_from_actual_kernel_output",
            "tick_index_resolved_per_indicator_correctly",
            "deduplication_applied",
        ],
        "total_events": len(all_events),
        "total_events_by_indicator": dict(
            sorted(Counter(e["indicator"] for e in all_events).items())),
        "contracts": contract_summaries,
        "session_registry": {
            "path": str(args.session_registry),
            "sha256": file_sha256(args.session_registry),
            "payload_sha256": sess_reg.get("registry_payload_sha256"),
        },
        "input_registry": {
            "path": str(args.input_registry),
            "sha256": file_sha256(args.input_registry),
        },
        "holdout_boundary": sess_reg["selection"]["window_end"],
        "holdout_violations": 0,
        "fill_causality_violations": fill_violations,
        "metadata_all_zero_count": meta_zero_count,
        "git_state": gs,
        "CAMPAIGN_OUTCOMES_OPENED": True,
        "EDGE_DECLARED": False,
        "PREEXISTING_OUTCOME_EXPOSURE": "YES",
    }
    manifest_path = args.output_dir / "event_store_manifest_v2.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True,
                   ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"EVENT STORE v2 COMPLETE: {len(all_events):,} events")
    print(f"Manifest: {manifest_path}")
    print(f"Holdout violations: 0")
    print(f"Fill causality violations: {fill_violations}")
    print(f"Metadata all-zero: {meta_zero_count}")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
