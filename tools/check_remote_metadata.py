import os
import sys
import json
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

datasets_to_check = [
    "edgelab-ticks-6e-preholdout",
    "edgelab-ticks-es-preholdout",
    "edgelab-ticks-gc-preholdout",
    "edgelab-ticks-mbt-preholdout",
    "edgelab-ticks-mes-preholdout",
    "edgelab-ticks-nq-preholdout",
    "edgelab-ticks-ym-preholdout",
    "edgelab-ticks-zb-preholdout"
]

verify_dir = Path(r"E:\kaggle_verify\remote_meta_check")
verify_dir.mkdir(parents=True, exist_ok=True)

manifest_data = {}

for slug in datasets_to_check:
    ref = f"nicolasbuttaro/{slug}"
    ds_dir = verify_dir / slug
    ds_dir.mkdir(parents=True, exist_ok=True)
    try:
        # Download files.sha256 if available
        api.dataset_download_file(ref, "files.sha256", path=str(ds_dir), force=True)
        sha_file = ds_dir / "files.sha256"
        if sha_file.exists():
            content = sha_file.read_text(encoding="utf-8", errors="ignore")
            manifest_data[slug] = {"files_sha256": content}
            print(f"Downloaded files.sha256 for {slug}")
    except Exception as e:
        print(f"Could not download files.sha256 for {slug}: {e}")
        # Try downloading kaggle_research_package_manifest.json
        try:
            api.dataset_download_file(ref, "kaggle_research_package_manifest.json", path=str(ds_dir), force=True)
            man_file = ds_dir / "kaggle_research_package_manifest.json"
            if man_file.exists():
                manifest_data[slug] = {"manifest": json.loads(man_file.read_text(encoding="utf-8"))}
                print(f"Downloaded manifest for {slug}")
        except Exception as e2:
            print(f"Could not download manifest for {slug}: {e2}")

out_p = Path(r"E:\EdgeLab-edgefactory\artifacts\audit\remote_datasets_metadata.json")
with open(out_p, "w", encoding="utf-8") as f:
    json.dump(manifest_data, f, indent=2)
print("Saved remote metadata.")
