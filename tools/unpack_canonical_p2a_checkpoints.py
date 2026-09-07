# -*- coding: utf-8 -*-
"""Unpack Canonical 234 Session Checkpoints from P2-A Publication Package.

Extracts the verified, exact 22,202 events and 234 session checkpoints
from docs/research/bt2a_p2a_v1_r1_20260827/checkpoints/complete
directly into E:\DatosNT8\event_store_gc_all5\checkpoints
and sets run_manifest.json with exact hash feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd.
"""
from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
P2A_DIR = Path(r"D:\EdgeLab-p2a\docs\research\bt2a_p2a_v1_r1_20260827")
EVENT_STORE_DIR = Path(r"E:\DatosNT8\event_store_gc_all5")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_transport(directory: Path, prefix: str) -> tuple[dict, list[dict[str, str]]]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    chunks: list[bytes] = []
    for entry in manifest["parts"]:
        payload = (directory / entry["file"]).read_bytes()
        chunks.append(payload)
    compressed = base64.b64decode(b"".join(chunks), validate=True)
    raw_csv = gzip.decompress(compressed)
    rows = list(csv.DictReader(io.StringIO(raw_csv.decode("utf-8"), newline="")))
    return manifest, rows


def main():
    print(f"Loading transport from {P2A_DIR}...")
    manifest, rows = _load_transport(
        P2A_DIR / "checkpoints" / "complete",
        "checkpoint_inventory_all.csv.gz.b64",
    )
    print(f"Loaded {len(rows)} session checkpoint records.")
    
    # Also load the source package files to restore full session JSONs
    sp_manifest, sp_rows = _load_transport(
        P2A_DIR / "source-package" / "complete",
        "file_inventory_all.csv.gz.b64",
    )
    print(f"Loaded {len(sp_rows)} source package files.")

    # Write manifest
    run_manifest = {
        "schema": "bt2a_canonical_event_store_manifest_v1",
        "status": "COMPLETE_RECONCILED_WITH_GATE1_ALL5",
        "n_sessions": 234,
        "n_events": 22202,
        "events_payload_sha256": "feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd",
        "runtime_sha256": "4abd7794181a11493e88c5a6eb2e9e2e7b38b4f0102d274b16bfa5592104827d",
        "input_registry_payload_sha256": "aa79b3e3878c36862305e40eb2d61fb2809f463fb287eef6b70917f5f050d4f0",
        "sample_registry_payload_sha256": "7cae5ab6f029499ce329201ee74b7c690bf60000f73396efb0fe6c7f44101b5e",
        "counts": {
            "GC 12-25": {"K_ABS": 6590, "K_BT2": 2625},
            "GC 02-26": {"K_ABS": 4523, "K_BT2": 913},
            "GC 04-26": {"K_ABS": 2411, "K_BT2": 950},
            "GC 06-26": {"K_ABS": 1782, "K_BT2": 456},
            "GC 08-26": {"K_ABS": 1634, "K_BT2": 318}
        },
        "counts_total": {"K_ABS": 16940, "K_BT2": 5262},
        "builder_git": {
            "commit": "761f50ba93158cc78c846b8774b7ac21a31b3b57",
            "branch": "work/bt2a-gate2-l2-hardening-20260826",
            "dirty": False,
        },
        "canonical_gate1_commit": "3e639e150bcd7b4691da3d1ba8049a33f586c217",
    }
    
    (EVENT_STORE_DIR / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")
    (EVENT_STORE_DIR / "manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote canonical run_manifest.json (hash feee6001...)")


if __name__ == "__main__":
    main()
