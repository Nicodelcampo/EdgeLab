#!/usr/bin/env python3
"""CPU exploratory outcome runner with a supplied frozen split.

This is not an input-file/features firewall or authority to open market data.
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.funnel.runner import FunnelRunner
from edgelab.funnel.splits import load_frozen_split, validate_split

ARRAY_NAMES = ("trade_date", "signal_bar_idx", "signal_dir", "high_ticks", "low_ticks",
               "bid_open_ticks", "ask_open_ticks")


def _verify_arrays_manifest(root, manifest_path, expected_sha256):
    """Bind every array to gated-window evidence before any array is opened.

    The manifest is caller-pinned, like the gate inputs: integrity, not approval.
    """
    import hashlib
    from edgelab.data.research_data_gate import DataEligibilityError, _sha, seal
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not _sha(expected_sha256) or seal(manifest) != expected_sha256:
        raise DataEligibilityError("arrays manifest: unpinned/mismatched hash")
    if manifest.get("schema") != "funnel_arrays_manifest_v1":
        raise DataEligibilityError("arrays manifest: unsupported schema")
    evidence = manifest.get("source_evidence")
    if not isinstance(evidence, dict) or evidence.get("reader_contract") != "research_window_v1":
        raise DataEligibilityError("arrays must derive from read_research_window evidence")
    for key in ("data_certificate_sha256", "roll_schedule_sha256", "liquidity_limits_sha256"):
        if not _sha(evidence.get(key)):
            raise DataEligibilityError("source evidence missing pin: " + key)
    files = manifest.get("files")
    if not isinstance(files, dict) or sorted(files) != sorted(ARRAY_NAMES):
        raise DataEligibilityError("arrays manifest must list exactly the funnel arrays")
    for name in ARRAY_NAMES:
        entry, path = files[name], root / f"{name}.npy"
        if not isinstance(entry, dict) or not _sha(entry.get("sha256")) or type(entry.get("size_bytes")) is not int:
            raise DataEligibilityError("invalid manifest entry: " + name)
        if not path.is_file() or path.stat().st_size != entry["size_bytes"]:
            raise DataEligibilityError("array missing or size mismatch: " + name)
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(block)
        if h.hexdigest() != entry["sha256"]:
            raise DataEligibilityError("array SHA256 mismatch: " + name)
    return {"mode": "GATED_WINDOW", "arrays_manifest_sha256": expected_sha256,
            "data_certificate_sha256": evidence["data_certificate_sha256"],
            "authority_authenticated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arrays", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--split", required=True, help="Original frozen split JSON; does not grant data permission")
    parser.add_argument("--out", required=True)
    parser.add_argument("--backend", choices=["cpu"], default="cpu")
    parser.add_argument("--max-hold-bars", type=int, default=200)
    parser.add_argument("--max-matrix-bytes", type=int, default=512*1024*1024)
    gate = parser.add_mutually_exclusive_group(required=True)
    gate.add_argument("--arrays-manifest", help="funnel_arrays_manifest_v1 bound to research_window evidence")
    gate.add_argument("--technical-only", action="store_true",
                      help="Explicitly ungated technical run on synthetic/QA arrays; never research input")
    parser.add_argument("--expected-manifest-sha256", help="External pin of --arrays-manifest")
    args = parser.parse_args()
    root = Path(args.arrays)
    if args.arrays_manifest:
        data_gate = _verify_arrays_manifest(root, args.arrays_manifest, args.expected_manifest_sha256)
    else:
        data_gate = {"mode": "TECHNICAL_ONLY_UNGATED", "research_input": False}
    load = lambda name: np.load(root / f"{name}.npy", mmap_mode="r", allow_pickle=False)
    frozen = load_frozen_split(args.split)
    trade_dates = load("trade_date")
    validate_split(frozen, trade_dates)  # Reject changed labels before opening price arrays.
    registry = json.loads(Path(args.registry).read_text())
    if isinstance(registry, dict):
        raw = registry["candidates"]
        fallback_family = registry.get("family_id", "UNDECLARED_FAMILY")
    elif isinstance(registry, list):
        raw, fallback_family = registry, "UNDECLARED_FAMILY"
    else:
        raise ValueError("registry must be object or list")
    configs = [{"candidate_id":c["candidate_id"], "family_id":c.get("family_id", fallback_family),
                "direction":c.get("direction", "normal"), "sl_ticks":c["sl_ticks"], "tp_ticks":c["tp_ticks"]} for c in raw]
    runner = FunnelRunner(trade_dates=trade_dates, signal_idx=load("signal_bar_idx"),
                          signal_dir=load("signal_dir"), high=load("high_ticks"), low=load("low_ticks"),
                          bid_open=load("bid_open_ticks"), ask_open=load("ask_open_ticks"),
                          configs=configs, out_dir=args.out, backend="cpu", frozen_split=frozen)
    result = runner.run_e1_e3(max_hold_bars=args.max_hold_bars, max_matrix_bytes=args.max_matrix_bytes)
    result["data_gate"] = data_gate
    print(json.dumps(result, indent=2, allow_nan=False))

if __name__ == "__main__":
    main()
