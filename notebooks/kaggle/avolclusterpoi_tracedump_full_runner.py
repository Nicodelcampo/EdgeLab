#!/usr/bin/env python3
"""Authorized target-free pre-holdout full-block trace for aVolClusterPOI.

Exports every complete Python block (CREATE and ABSTAIN) with cells, history,
threshold, candidate clusters, decision and selected cluster. It does not read
or calculate outcomes, returns, MAE/MFE or P&L.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "eafbc0380253e029acc969e07c17ebb7912ef7ec"
REPO_DIR = Path("/kaggle/working/EdgeLab")
DATA_DIR = Path("/kaggle/input/datasets/nicolasbuttaro/edgelab-ticks-nq-preholdout")
EXPECTED_TICKS = 34_203_535
EXPECTED_BARS = 285_063
EXPECTED_BLOCKS = 28_477
EXPECTED_ZONES = 414


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not (REPO_DIR / ".git").exists():
    subprocess.run([
        "git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)
    ], check=True)
subprocess.run([
    "git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "200"
], cwd=REPO_DIR, check=True)
subprocess.run([
    "git", "checkout", "-B", "tracedump-full", EXPECTED_COMMIT
], cwd=REPO_DIR, check=True)
actual = subprocess.check_output([
    "git", "rev-parse", "HEAD"
], cwd=REPO_DIR, text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EXPECTED_COMMIT")
print("repo_commit=", actual, flush=True)

sys.path.insert(0, str(REPO_DIR))
from edgelab.bridge import bars as bars_mod, ticks as ticks_mod  # noqa: E402
from edgelab.bridge.indicators import avolclusterpoi  # noqa: E402

parquet_hits = list(DATA_DIR.rglob("NQ_06-26_ticks.parquet"))
if len(parquet_hits) != 1:
    raise SystemExit("expected exactly one NQ_06-26_ticks.parquet, found {}".format(len(parquet_hits)))
parquet = parquet_hits[0]
ticks = ticks_mod.load_canonical_parquet(str(parquet))
if len(ticks.ts_ns) != EXPECTED_TICKS:
    raise SystemExit("tick-count pin failed: {} != {}".format(len(ticks.ts_ns), EXPECTED_TICKS))
print("n_ticks=", len(ticks.ts_ns), flush=True)

bars = bars_mod.build_tick_bars(ticks, 120)
if len(bars.close_t) != EXPECTED_BARS:
    raise SystemExit("bar-count pin failed: {} != {}".format(len(bars.close_t), EXPECTED_BARS))
footprints = bars_mod.build_footprints(ticks, bars)
print("n_bars=", len(bars.close_t), flush=True)

result = avolclusterpoi.run(ticks, bars, footprints, debug_trace=True)
blocks = result["block_trace"]
if len(blocks) != EXPECTED_BLOCKS:
    raise SystemExit("block-count pin failed: {} != {}".format(len(blocks), EXPECTED_BLOCKS))
if len(result["zones"]) != EXPECTED_ZONES:
    raise SystemExit("zone-count pin failed: {} != {}".format(len(result["zones"]), EXPECTED_ZONES))
required = {
    "block_end_ns", "cells", "median", "hot_threshold", "best_score", "threshold",
    "history_samples", "decision", "clusters", "selected_cluster", "zone_ids",
}
for index, block in enumerate(blocks):
    missing = required - set(block)
    if missing:
        raise SystemExit("block {} missing diagnostic keys {}".format(index, sorted(missing)))
print("n_blocks_total=", len(blocks), flush=True)
print("n_zones=", len(result["zones"]), flush=True)

out_dir = Path("/kaggle/working/avolclusterpoi_tracedump_full")
out_dir.mkdir(parents=True, exist_ok=True)
files = {
    "zones.json": result["zones"],
    "all_blocks.json": blocks,
    "summary.json": {
        "scope": "target_free_preholdout",
        "repo_commit": actual,
        "parquet": str(parquet),
        "n_ticks": len(ticks.ts_ns),
        "n_bars": len(bars.close_t),
        "n_blocks": len(blocks),
        "n_zones": len(result["zones"]),
        "decision_counts": {
            decision: sum(1 for block in blocks if block["decision"] == decision)
            for decision in sorted({block["decision"] for block in blocks})
        },
    },
}
for name, payload in files.items():
    (out_dir / name).write_text(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8"
    )

manifest = {
    name: {"bytes": (out_dir / name).stat().st_size, "sha256": sha256(out_dir / name)}
    for name in files
}
(out_dir / "sha256_manifest.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)
archive = Path("/kaggle/working/avolclusterpoi_tracedump_full.zip")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for path in sorted(out_dir.iterdir()):
        zf.write(path, path.relative_to(out_dir.parent))
shutil.copy2(out_dir / "summary.json", Path("/kaggle/working/summary.json"))
shutil.copy2(out_dir / "sha256_manifest.json", Path("/kaggle/working/sha256_manifest.json"))
print("artifact=", archive, flush=True)
print("artifact_sha256=", sha256(archive), flush=True)
