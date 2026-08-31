#!/usr/bin/env python3
"""Kaggle Entrypoint: BT2A NQ Gate 1 (16-cell) Execution.

Implementation authorized under Token 3 (AUTHORIZE_IMPLEMENT_BT2A_NQ_GATE1_16CELL_V1).
Execution authorized under Token 4 (AUTHORIZE_RUN_BT2A_NQ_GATE1_V1), recorded in
docs/research/DECISION_NICO_IMPLEMENT_Y_RUN_BT2A_NQ_GATE1_2026-08-31.md.

Order of operations (fail-closed):
1. Partial clone at FULL_COMMIT (speed lever 3).
2. PHYSICAL preflight of the repo (tools/preflight_bt2a_nq_gate1.py
   --preflight-only) against the staged artifacts; abort unless PASS.
3. Per-contract computation as SUBPROCESSES under a bounded thread pool
   (speed lever 1, per KAGGLE_LAUNCHER_PARALLELISM_POLICY_V1_2026-08-30.md:
   parallelism lives here in the launcher, not inside the tool).
4. Aggregation subprocess -> result + manifest.

Speed lever 2 (cached pre-anchor features per contract) lives inside the
tool's per-contract pipeline.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
FULL_COMMIT = "fca5516de8021e4debd9e7bc07eb2d1c68ab8081"  # pinned post-s_row-NameError-fix + live progress heartbeat (fca5516)
TEMP_REPO_DIR = Path("/tmp/EdgeLab")
OUTPUT_DIR = Path("/kaggle/working/edgelab-output")
WORKING_DIR = Path("/kaggle/working")
STATS_DIR = Path("/kaggle/working/edgelab-stats")
EXECUTION_TOKEN = "AUTHORIZE_RUN_BT2A_NQ_GATE1_V1"

CONTRACTS = ["NQ 03-26", "NQ 06-26", "NQ 09-25", "NQ 09-26", "NQ 12-25"]
MAX_WORKERS = 4
REPLICATIONS = 1000
SEED = 20260831


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def find_dataset_dir(name_fragment: str) -> Path:
    search_roots = [Path("/kaggle/input"), Path("/kaggle/input/datasets"), Path(".")]
    print(f"Searching for dataset matching '{name_fragment}' in {[str(r) for r in search_roots if r.is_dir()]}", flush=True)
    for root in search_roots:
        if root.is_dir():
            hits = [p for p in root.rglob("*") if p.is_dir() and name_fragment in p.name]
            if hits:
                hits.sort(key=lambda p: len(p.parts))
                print(f"-> found '{name_fragment}' at: {hits[0]}", flush=True)
                return hits[0]
    for root in search_roots:
        if root.is_dir():
            candidate = root / name_fragment
            if candidate.is_dir():
                print(f"-> found '{name_fragment}' at: {candidate}", flush=True)
                return candidate
    raise SystemExit(f"no dataset directory matching '{name_fragment}' found under /kaggle/input")


def find_file(search_dir: Path, stub: str, suffix: str) -> Path:
    hits = [p for p in search_dir.rglob(f"*{suffix}") if stub in p.name]
    if not hits:
        raise SystemExit(f"no file matching '{stub}' with suffix '{suffix}' under {search_dir}")
    hits.sort(key=lambda p: len(str(p)))
    return hits[0]


def _memavail(tag: str) -> None:
    """VM-level memory readout at stage boundaries (no dependencies).

    The 2026-08-31 Kaggle runs restarted the whole session twice (workers=4
    and workers=2 alike): per-worker footprint peaked near ~10 GB/contract in
    the pre-fix CLI. These markers make the next run self-report instead of
    needing a post-mortem log poll.
    """
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    print(f"[mem] {tag}: MemAvailable={line.split(':', 1)[1].strip()}", flush=True)
                    return
    except Exception:
        pass


def run_parallel_contracts(args_for, log_for, order, label, max_workers=MAX_WORKERS):
    """Policy pattern: thread pool OF SUBPROCESSES, fail-closed.

    Each worker's stdout/stderr streams to its own log file on disk (no
    capture_output buffering in the main process), so a worker killed by the
    OOM killer still leaves its last lines for the post-mortem. A heartbeat
    thread tails each active worker's log file into the MAIN process stdout
    every 60s, so `kaggle kernels logs -f` shows live per-contract progress
    -- per-worker disk logging otherwise made a long-running attempt look
    silent from outside (2026-08-31 15:00 ART: 30+ min with zero visible
    output, no way to tell "slow" from "stuck").
    """
    import threading
    import time

    log_paths = {i: log_for(i) for i in order}
    done_flag = {"stop": False}
    last_pos: dict[int, int] = {i: 0 for i in order}

    def _heartbeat():
        while not done_flag["stop"]:
            for i in order:
                p = log_paths[i]
                try:
                    with open(p, "r", errors="replace") as f:
                        f.seek(last_pos[i])
                        new = f.read()
                        last_pos[i] = f.tell()
                    if new.strip():
                        for line in new.strip().splitlines()[-3:]:
                            print(f"[hb w{i}] {line}", flush=True)
                except FileNotFoundError:
                    pass
            for _ in range(60):
                if done_flag["stop"]:
                    break
                time.sleep(1)

    hb_thread = threading.Thread(target=_heartbeat, daemon=True)
    hb_thread.start()

    def _run_one(i):
        log_path = log_for(i)
        with open(log_path, "w") as lf:
            proc = subprocess.run(args_for(i), stdout=lf, stderr=subprocess.STDOUT)
        return i, proc.returncode, log_path
    pool = ThreadPoolExecutor(max_workers=max_workers)
    completed = 0
    try:
        futures = {pool.submit(_run_one, i): i for i in order}
        for future in as_completed(futures):
            i, rc, log_path = future.result()
            if rc != 0:
                tail = Path(log_path).read_text(errors="replace")[-4000:]
                print(f"FAILED {label} {i} (log: {log_path})\n--- tail ---\n{tail}", flush=True)
                pool.shutdown(wait=False, cancel_futures=True)
                raise SystemExit(f"{label} failed at index {i}")
            completed += 1
            print(f"{label} progress: {completed}/{len(order)}", flush=True)
            _memavail(f"{label} {completed}/{len(order)}")
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
        done_flag["stop"] = True


def main() -> None:
    t_start = datetime.now(timezone.utc)
    print("=== BT2A NQ GATE 1 (16-CELL) EXECUTION RUNNER ===", flush=True)
    print(f"Started at: {t_start.isoformat()}", flush=True)

    # 1. Partial clone at the pinned commit
    if TEMP_REPO_DIR.exists():
        shutil.rmtree(TEMP_REPO_DIR)
    run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(TEMP_REPO_DIR)])
    run(["git", "fetch", "origin", FULL_COMMIT, "--depth", "200"], cwd=TEMP_REPO_DIR)
    run(["git", "checkout", "--detach", FULL_COMMIT], cwd=TEMP_REPO_DIR)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TEMP_REPO_DIR, text=True).strip()
    print("repo_commit=", actual, flush=True)
    if actual != FULL_COMMIT:
        raise SystemExit(f"checked-out commit differs: {actual} != {FULL_COMMIT}")

    # 2. Locate inputs dynamically (speed lever 3, robust discovery).
    #    RE-APPLIED 2026-08-31 14:52 UTC: the 8830b74 memory-fix commit was
    #    authored against a pre-9aa7912 checkout and silently reverted this
    #    discovery block back to the broken "coordinates"/"package"/"bt2"
    #    search terms -- confirmed by a real run failing again with "no
    #    dataset directory matching 'coordinates'" at 14:47 UTC. Two agents
    #    editing the same file without re-reading the other's latest push
    #    first; re-applying verbatim what 9aa7912 + c6aec73 already fixed.
    ticks_dir = find_dataset_dir("edgelab-ticks-nq-preholdout")
    package_dir = ticks_dir
    event_store_dir = find_dataset_dir("event-store")
    bt2_dir = find_dataset_dir("bt2-v2")

    spec_path = TEMP_REPO_DIR / "specs/bt2a_nq_gate1_v1.draft.json"
    event_store_manifest = find_file(event_store_dir, "bt2a_nq_creation_event_store_manifest", ".json")
    bt2_result_path = TEMP_REPO_DIR / "docs/research/bigtrap2_nq_tickframes_sweep_v2_result.json"
    bt2_coords_path = find_file(bt2_dir, "tick_25_IMB30_VOL10", ".parquet")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATS_DIR.mkdir(parents=True, exist_ok=True)

    # 3. PHYSICAL preflight of the repo before any outcome computation.
    #    Token 4 does NOT replace this gate (DECISION doc, puerta 4).
    preflight_cmd = [
        sys.executable, str(TEMP_REPO_DIR / "tools/preflight_bt2a_nq_gate1.py"),
        "--spec", str(spec_path),
        "--data-dir", str(package_dir),
        "--event-store-dir", str(event_store_dir),
        "--bt2-artifact-dir", str(bt2_dir),
        "--output-dir", str(OUTPUT_DIR),
        "--expected-commit", FULL_COMMIT,
        "--preflight-only",
    ]
    proc = subprocess.run(preflight_cmd, capture_output=True, text=True)
    print(proc.stdout, flush=True)
    if proc.returncode != 0:
        print(proc.stderr, flush=True)
        raise SystemExit("[FAIL_CLOSED] physical preflight NOT READY -- aborting before any outcome access")

    def contract_args(i: int) -> list[str]:
        return [
            sys.executable, str(tool),
            "--spec", str(spec_path),
            "--event-store", str(event_store_manifest),
            "--bt2-result", str(bt2_result_path),
            "--bt2-coords", str(bt2_coords_path),
            "--data-dir", str(ticks_dir),
            "--stats-dir", str(STATS_DIR),
            "--contract", CONTRACTS[i],
            "--authorization", EXECUTION_TOKEN,
            "--seed", str(SEED + i * 10000),
        ]

    # 4. Per-contract subprocesses under the bounded pool (speed lever 1).
    #    Order: ascending tick-file size, so the big contracts (peak memory)
    #    start last and their peaks don't stack with each other's.
    tool = TEMP_REPO_DIR / "tools/run_bt2a_nq_gate1_outcomes.py"

    def _tick_file_size(i: int) -> int:
        stub = CONTRACTS[i].split(" ")[1]
        hits = [p for p in ticks_dir.rglob("*") if p.is_file() and stub in p.name and p.suffix in (".parquet", ".pq")]
        return hits[0].stat().st_size if hits else 0

    order = sorted(range(len(CONTRACTS)), key=_tick_file_size)
    print(f"contract order (ascending size): {[CONTRACTS[i] for i in order]}", flush=True)
    _memavail("before contract workers")
    run_parallel_contracts(
        contract_args,
        lambda i: STATS_DIR / f"gate1_contract_{i}.log",
        order,
        "gate1-contract",
    )
    _memavail("after contract workers")

    # 5. Aggregation subprocess
    run([
        sys.executable, str(tool),
        "--aggregate",
        "--spec", str(spec_path),
        "--event-store", str(event_store_manifest),
        "--bt2-result", str(bt2_result_path),
        "--stats-dir", str(STATS_DIR),
        "--output-dir", str(OUTPUT_DIR),
        "--authorization", EXECUTION_TOKEN,
        "--replications", str(REPLICATIONS),
        "--seed", str(SEED),
    ])

    for f in OUTPUT_DIR.glob("*.json"):
        shutil.copy2(f, WORKING_DIR / f.name)

    result = json.loads((OUTPUT_DIR / "bt2a_nq_gate1_result.json").read_text(encoding="utf-8"))
    print("\n================ SUMMARY RESULT ================", flush=True)
    print(json.dumps(
        {
            "decision": result["decision"],
            "decision_details": result["decision_details"],
            "coverage": result["coverage"],
            "execution_metadata": result["execution_metadata"],
            "attestation": result["attestation"],
        },
        indent=2, default=str,
    ), flush=True)
    print("================ END SUMMARY ================", flush=True)


if __name__ == "__main__":
    main()
