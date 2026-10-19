#!/usr/bin/env python3
"""Execute the official committed post-upload verifier (20_nq_post_upload_rehash.py)."""
import os
import subprocess
import sys
from pathlib import Path

os.environ["EDGELAB_EXPECTED_COMMIT"] = "5621e9400799f0b90642c38115bd7204de48019d"
os.environ["EDGELAB_DATA_DIR"] = "/kaggle/input/datasets/nicolasbuttaro/edgelab-ticks-nq-preholdout"
os.environ["EDGELAB_REPO_URL"] = "https://github.com/Nicodelcampo/EdgeLab.git"

REPO_DIR = Path("/kaggle/working/EdgeLab")
OUTPUT = Path("/kaggle/working/nq_post_upload_rehash.json")
EXPECTED_COMMIT = os.environ["EDGELAB_EXPECTED_COMMIT"]
DATA_DIR = os.environ["EDGELAB_DATA_DIR"]

print(f"=== EJECUTANDO VERIFICADOR COMITEADO (20_nq_post_upload_rehash.py) ===")
print(f"  EXPECTED_COMMIT: {EXPECTED_COMMIT}")
print(f"  DATA_DIR: {DATA_DIR}")

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", os.environ["EDGELAB_REPO_URL"], str(REPO_DIR)], check=True)

subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "1"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "--detach", EXPECTED_COMMIT], cwd=REPO_DIR, check=True)

actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
print(f"  CHECKED_OUT_COMMIT: {actual}")
if actual != EXPECTED_COMMIT:
    raise SystemExit("Commit mismatch")

cmd = [
    sys.executable,
    "tools/verify_kaggle_nq_post_upload.py",
    "--data-dir",
    DATA_DIR,
    "--contract",
    "specs/kaggle_nq_private_upload_v1.draft.json",
    "--output",
    str(OUTPUT),
]

print(f"  Ejecutando: {' '.join(cmd)}")
res = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
print("\n=== STDOUT DEL VERIFICADOR ===")
print(res.stdout)
print("=== STDERR DEL VERIFICADOR ===")
print(res.stderr)
print(f"Exit code: {res.returncode}")

if OUTPUT.exists():
    print(f"\n=== CONTENIDO DE {OUTPUT} ===")
    print(OUTPUT.read_text())
else:
    print(f"\n{OUTPUT} no fue generado.")

sys.exit(res.returncode)
