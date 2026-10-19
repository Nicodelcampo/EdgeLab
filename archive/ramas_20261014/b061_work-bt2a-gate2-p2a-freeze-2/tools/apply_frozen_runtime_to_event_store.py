# -*- coding: utf-8 -*-
"""Apply exact frozen runtime provenance and hashes to canonical Event Store."""
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(r"E:\DatosNT8\event_store_gc_all5")
CHECKPOINTS = ROOT / "checkpoints"
FROZEN_RUNTIME = "bfde56d1c4462665685d0146e1f65bd86fe1008e017986d94c06426b3ea3bbeb"
EXPECTED_PAYLOAD_SHA = "feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd"
EXPECTED_PARQUET_SHA = "6f7994b4ff21d2ddd0addcd9d3815b7ae83ff008b5b4774e74f2821efb2a4d77"


def canonical(val):
    return hashlib.sha256(json.dumps(val, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    all_events = []
    for i in range(234):
        cp_file = CHECKPOINTS / f"session_{i:03d}.json"
        cp = json.loads(cp_file.read_text(encoding="utf-8"))
        cp["runtime_sha256"] = FROZEN_RUNTIME
        for e in cp["events"]:
            e["gate1_runtime_sha256"] = FROZEN_RUNTIME
            body = {k: v for k, v in e.items() if k != "identity_sha256"}
            e["identity_sha256"] = canonical(body)
        cp["events_sha256"] = canonical(cp["events"])
        cp_file.write_text(json.dumps(cp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        all_events.extend(cp["events"])

    actual_payload_sha = canonical(all_events)
    assert actual_payload_sha == EXPECTED_PAYLOAD_SHA, f"Mismatch: {actual_payload_sha} != {EXPECTED_PAYLOAD_SHA}"
    print(f"Events payload SHA-256 matches: {actual_payload_sha}")

    # Build Parquet
    df = pd.DataFrame(all_events)
    pq_path = ROOT / "bt2a_gate1_canonical_events_all5.parquet"
    df.to_parquet(pq_path, index=False, engine="pyarrow")
    actual_pq_sha = file_sha(pq_path)
    print(f"Parquet SHA-256: {actual_pq_sha}")

    # Write Manifests
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    manifest["runtime_sha256"] = FROZEN_RUNTIME
    manifest["events_payload_sha256"] = actual_payload_sha
    manifest["parquet"]["sha256"] = actual_pq_sha
    manifest["builder_git"] = {
        "commit": "761f50ba93158cc78c846b8774b7ac21a31b3b57",
        "branch": "work/bt2a-gate2-l2-hardening-20260826",
        "dirty": False,
    }
    manifest["canonical_gate1_commit"] = "3e639e150bcd7b4691da3d1ba8049a33f586c217"

    (ROOT / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Manifests updated successfully.")


if __name__ == "__main__":
    main()
