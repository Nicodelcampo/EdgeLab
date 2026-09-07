# -*- coding: utf-8 -*-
"""Quarantine premature clock heterogeneity execution files."""
import hashlib
import json
import shutil
from pathlib import Path

SRC = Path(r"E:\DatosNT8\bt2a_p2a_gc_clock_run")
DST = Path(r"E:\DatosNT8\quarantine\bt2a_p2a_gc_clock_run_premature_20260828")


def main():
    records = []
    if SRC.is_dir():
        DST.mkdir(parents=True, exist_ok=True)
        for p in SRC.rglob("*"):
            if p.is_file():
                rel = str(p.relative_to(SRC))
                target = DST / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                data = p.read_bytes()
                target.write_bytes(data)
                h = hashlib.sha256(data).hexdigest()
                records.append({"file": rel, "bytes": len(data), "sha256": h})
        shutil.rmtree(SRC)
        manifest = DST / "quarantine_manifest.json"
        manifest.write_text(json.dumps(records, indent=2), encoding="utf-8")
        print(f"Quarantined {len(records)} files to {DST}")
        for r in records:
            print(f"  {r['file']}: bytes={r['bytes']}, sha256={r['sha256']}")
    else:
        print("No directory found at", SRC)


if __name__ == "__main__":
    main()
