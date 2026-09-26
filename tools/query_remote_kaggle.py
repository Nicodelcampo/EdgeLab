import os
import sys
import json
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

datasets = [
    "edgelab-ticks-6b-preholdout",
    "edgelab-ticks-6e-preholdout",
    "edgelab-ticks-6j-preholdout",
    "edgelab-ticks-es-preholdout",
    "edgelab-ticks-gc-preholdout",
    "edgelab-ticks-mbt-preholdout",
    "edgelab-ticks-mes-preholdout",
    "edgelab-ticks-mnq-preholdout",
    "edgelab-ticks-nq-preholdout",
    "edgelab-ticks-ym-preholdout",
    "edgelab-ticks-zb-preholdout",
    "edgelab-edge-factory-target-free-audited",
    "edgelab-edge-factory-audit-evidence-20260919"
]

remote_inventory = {}

for slug in datasets:
    ref = f"nicolasbuttaro/{slug}"
    try:
        files = api.dataset_list_files(ref).files
        file_list = []
        for f in files:
            file_list.append({
                "name": str(f.name) if hasattr(f, 'name') else str(f),
                "size": getattr(f, 'size', getattr(f, 'totalBytes', None)),
                "description": getattr(f, 'description', None)
            })
        remote_inventory[slug] = {
            "status": "EXISTS",
            "file_count": len(files),
            "files": file_list
        }
        print(f"{slug}: {len(files)} remote files")
    except Exception as e:
        remote_inventory[slug] = {
            "status": "ERROR",
            "error": str(e)
        }
        print(f"{slug}: ERROR ({e})")

out_p = Path(r"E:\EdgeLab-edgefactory\artifacts\audit\kaggle_remote_inventory.json")
out_p.parent.mkdir(parents=True, exist_ok=True)
with open(out_p, "w", encoding="utf-8") as f:
    json.dump(remote_inventory, f, indent=2)
print(f"Saved remote inventory to {out_p}")
