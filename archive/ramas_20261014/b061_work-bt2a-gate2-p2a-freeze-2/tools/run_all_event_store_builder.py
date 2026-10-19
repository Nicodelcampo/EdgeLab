# -*- coding: utf-8 -*-
"""Build exact canonical Gate 1 Event Store using build_bt2a_gate1_event_store.py."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(r"E:\DatosNT8\gc_gate1_parquets_20260825")
OUTPUT_DIR = Path(r"E:\DatosNT8\event_store_gc_all5")


def main():
    print("Building all 234 canonical session checkpoints with build_bt2a_gate1_event_store.py...")
    for i in range(234):
        cp_path = OUTPUT_DIR / "checkpoints" / f"session_{i:03d}.json"
        cmd = [
            sys.executable,
            str(ROOT / "tools/build_bt2a_gate1_event_store.py"),
            "--root", str(ROOT),
            "--data-dir", str(DATA_DIR),
            "--output-dir", str(OUTPUT_DIR),
            "--session-index", str(i),
            "--allow-dirty",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error on session {i}: {res.stderr}")
            sys.exit(1)
        if (i + 1) % 25 == 0 or i == 233:
            print(f"  Session {i+1}/234 completed.")

    print("Finalizing event store...")
    cmd_fin = [
        sys.executable,
        str(ROOT / "tools/build_bt2a_gate1_event_store.py"),
        "--root", str(ROOT),
        "--data-dir", str(DATA_DIR),
        "--output-dir", str(OUTPUT_DIR),
        "--finalize",
        "--allow-dirty",
    ]
    res_fin = subprocess.run(cmd_fin, capture_output=True, text=True)
    print(res_fin.stdout)
    if res_fin.returncode != 0:
        print("Finalize error:", res_fin.stderr)
        sys.exit(1)
    print("Event store build and finalize complete.")


if __name__ == "__main__":
    main()
