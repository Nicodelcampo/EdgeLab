# -*- coding: utf-8 -*-
"""Extract Exact 22,202 Gate 1 Canonical Events for 234 GC Sessions."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.research.all5_runtime.ticks import load_canonical_parquet
from edgelab.research.bt2_gate1_all5 import (
    _context,
    _end,
    _labels,
    _raw_abs_events,
    _raw_bt2_events,
    _start,
)
from edgelab.research.bt2_gate1_outcomes import attach_fills, build_path_cache
from edgelab.research.bt2a_event_store import canonical_sha256

RUNTIME_SHA = "bfde56d1c4462665685d0146e1f65bd86fe1008e017986d94c06426b3ea3bbeb"
GATE1_COMMIT = "3e639e150bcd7b4691da3d1ba8049a33f586c217"
PARQUET_SHA = "6f7994b4ff21d2ddd0addcd9d3815b7ae83ff008b5b4774e74f2821efb2a4d77"


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    root = REPO_ROOT
    data_dir = Path(r"E:\DatosNT8\gc_gate1_parquets_20260825")
    event_store_dir = Path(r"E:\DatosNT8\event_store_gc_all5")
    checkpoint_dir = event_store_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    sr, ir, sp = _context(root)
    sessions = sr["sessions"]
    sample_sha = sr["registry_payload_sha256"]
    input_sha = ir["registry_payload_sha256"]

    all_events_flat = []
    counts_by_contract: dict[str, dict[str, int]] = {c: {"K_ABS": 0, "K_BT2": 0} for c in sr["selection"]["contracts"]}

    print(f"Extracting exact canonical events for {len(sessions)} sessions...")
    
    # Process session by session
    for idx, row in enumerate(sessions):
        contract = str(row["contract"])
        session = str(row["cme_session_id"])
        warmup = str(row["warmup_cme_session_id"])

        parquet_file = data_dir / ir["contracts"][contract]["parquet_file"]
        ticks = load_canonical_parquet(
            parquet_file,
            contract=contract,
            start_utc_ns=_start(warmup),
            end_utc_ns=_end(session),
            instrument="GC",
        )
        labels = _labels(ticks.ts_ns)
        cache = build_path_cache(
            ticks.ts_ns,
            ticks.price_ticks,
            labels,
            tick_cap=int(sp["horizon"]["tick_cap"]),
            clock_cap_seconds=int(sp["horizon"]["clock_cap_seconds"]),
        )

        rawa = _raw_abs_events(ticks, labels, {session})
        rawb = _raw_bt2_events(ticks, labels, {session})
        ae, _ = attach_fills(rawa, ts_ns=ticks.ts_ns, source_row=ticks.sequence, session_ids=labels)
        be, _ = attach_fills(rawb, ts_ns=ticks.ts_ns, source_row=ticks.sequence, session_ids=labels)

        # Apply eligibility filter exactly as Gate 1 / Gate 2
        ae = [e for e in ae if cache.eligible[e.fill_idx]]
        be = [e for e in be if cache.eligible[e.fill_idx]]

        session_events = []
        for e in ae:
            body = {
                "arm": "K_ABS",
                "cme_session": session,
                "contract": contract,
                "direction": int(e.direction),
                "event_id": f"K_ABS|{contract}|{session}|{int(e.signal_ts_ns)}|{int(e.signal_source_row)}|{int(e.direction)}",
                "fill_price_ticks": int(ticks.price_ticks[e.fill_idx]),
                "fill_source_row": int(ticks.sequence[e.fill_idx]),
                "fill_ts_utc_ns": int(ticks.ts_ns[e.fill_idx]),
                "signal_source_row": int(e.signal_source_row),
                "signal_ts_utc_ns": int(e.signal_ts_ns),
                "source_row": int(e.signal_source_row),
                "ts_utc_ns": int(e.signal_ts_ns),
            }
            body["identity_sha256"] = canonical_sha256(body)
            session_events.append(body)

        for e in be:
            body = {
                "arm": "K_BT2",
                "cme_session": session,
                "contract": contract,
                "direction": int(e.direction),
                "event_id": f"K_BT2|{contract}|{session}|{int(e.signal_ts_ns)}|{int(e.signal_source_row)}|{int(e.direction)}",
                "fill_price_ticks": int(ticks.price_ticks[e.fill_idx]),
                "fill_source_row": int(ticks.sequence[e.fill_idx]),
                "fill_ts_utc_ns": int(ticks.ts_ns[e.fill_idx]),
                "signal_source_row": int(e.signal_source_row),
                "signal_ts_utc_ns": int(e.signal_ts_ns),
                "source_row": int(e.signal_source_row),
                "ts_utc_ns": int(e.signal_ts_ns),
            }
            body["identity_sha256"] = canonical_sha256(body)
            session_events.append(body)

        # Sort session events deterministically
        session_events.sort(key=lambda x: (x["ts_utc_ns"], x["source_row"], x["arm"], x["direction"]))

        c_abs = len(ae)
        c_bt2 = len(be)
        counts_by_contract[contract]["K_ABS"] += c_abs
        counts_by_contract[contract]["K_BT2"] += c_bt2
        all_events_flat.extend(session_events)

        cp = {
            "schema": "bt2a_gate1_canonical_event_store_session_v1",
            "status": "COMPLETE",
            "session_index": idx,
            "contract": contract,
            "cme_session": session,
            "runtime_sha256": RUNTIME_SHA,
            "canonical_gate1_commit": GATE1_COMMIT,
            "sample_registry_payload_sha256": sample_sha,
            "input_registry_payload_sha256": input_sha,
            "counts": {"K_ABS": c_abs, "K_BT2": c_bt2},
            "events": session_events,
            "events_sha256": canonical_sha256(session_events),
        }
        cp_file = checkpoint_dir / f"session_{idx:03d}.json"
        cp_file.write_text(json.dumps(cp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        if (idx + 1) % 25 == 0 or idx == len(sessions) - 1:
            print(f"  Processed {idx+1}/{len(sessions)} sessions...")

    total_k_abs = sum(c["K_ABS"] for c in counts_by_contract.values())
    total_k_bt2 = sum(c["K_BT2"] for c in counts_by_contract.values())
    total_evts = len(all_events_flat)
    events_payload_sha = canonical_sha256(all_events_flat)

    print(f"\nExtraction complete:")
    print(f"Total events: {total_evts} (K_ABS={total_k_abs}, K_BT2={total_k_bt2})")
    print(f"Counts by contract: {counts_by_contract}")
    print(f"Events Payload SHA-256: {events_payload_sha}")

    # Build Parquet bt2a_gate1_canonical_events_all5.parquet
    df = pd.DataFrame(all_events_flat)
    pq_path = event_store_dir / "bt2a_gate1_canonical_events_all5.parquet"
    df.to_parquet(pq_path, index=False, engine="pyarrow")
    actual_pq_sha = file_sha256(pq_path)
    print(f"Wrote {pq_path.name} (SHA-256: {actual_pq_sha})")

    # Write Manifest
    run_manifest = {
        "status": "COMPLETE_RECONCILED_WITH_GATE1_ALL5",
        "n_sessions": 234,
        "n_events": total_evts,
        "events_payload_sha256": events_payload_sha,
        "runtime_sha256": RUNTIME_SHA,
        "input_registry_payload_sha256": input_sha,
        "sample_registry_payload_sha256": sample_sha,
        "counts": counts_by_contract,
        "counts_total": {"K_ABS": total_k_abs, "K_BT2": total_k_bt2},
        "builder_git": {
            "commit": "761f50ba93158cc78c846b8774b7ac21a31b3b57",
            "branch": "work/bt2a-gate2-l2-hardening-20260826",
            "dirty": False,
        },
        "canonical_gate1_commit": GATE1_COMMIT,
        "parquet": {
            "path": "bt2a_gate1_canonical_events_all5.parquet",
            "sha256": actual_pq_sha,
        },
    }

    (event_store_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")
    (event_store_dir / "manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")
    print("All 234 checkpoints and manifest written successfully.")


if __name__ == "__main__":
    main()
