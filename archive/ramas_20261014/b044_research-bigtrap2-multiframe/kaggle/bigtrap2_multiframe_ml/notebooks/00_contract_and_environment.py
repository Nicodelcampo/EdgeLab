# -*- coding: utf-8 -*-
"""Notebook 00 — contrato y entorno (Kaggle).

Este notebook NO entrena modelos, NO calcula métricas predictivas y NO abre
el holdout. Su único propósito es fallar temprano si el dataset no cumple el
contrato.

Si cualquier comprobación falla, el notebook debe detenerse. Un dataset que
no pasa el contrato no habilita análisis exploratorio “provisional”.

Contrato: specs/bigtrap2_multiframe_ml_dataset_contract_v1.json
"""
from __future__ import annotations

import json
import hashlib
import os
import platform
import sys
from pathlib import Path

import pandas as pd

INPUT_ROOT = Path(
    os.environ.get(
        "EDGELAB_KAGGLE_INPUT",
        "/kaggle/input/edgelab-bigtrap2-multiframe-research",
    )
)
WORKING_ROOT = Path(os.environ.get("EDGELAB_KAGGLE_WORKING", "/kaggle/working"))

REQUIRED_FILES = [
    "dataset_manifest.json",
    "hashes.sha256",
    "contract.json",
    "events_long.parquet",
    "windows_ml.parquet",
    "targets_long.parquet",
    "folds_outer.parquet",
]


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def verify_files(root: Path) -> dict:
    missing = [name for name in REQUIRED_FILES if not (root / name).exists()]
    return {"missing_files": missing, "passed": not missing}


def verify_hashes(root: Path) -> dict:
    manifest_path = root / "hashes.sha256"
    if not manifest_path.exists():
        return {"passed": False, "detail": "hashes.sha256 ausente"}
    mismatches = []
    checked = 0
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        expected, _, name = line.partition("  ")
        target = root / name.strip()
        if not target.exists():
            mismatches.append({"file": name, "reason": "missing"})
            continue
        actual = sha256_file(target)
        checked += 1
        if actual != expected.strip():
            mismatches.append(
                {"file": name, "expected": expected.strip(), "actual": actual}
            )
    return {"passed": not mismatches, "checked": checked, "mismatches": mismatches}


def environment_report() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "cwd": str(Path.cwd()),
    }


def main() -> int:
    report = {
        "stage": "00_contract_and_environment",
        "input_root": str(INPUT_ROOT),
        "environment": environment_report(),
    }

    report["files"] = verify_files(INPUT_ROOT)
    if not report["files"]["passed"]:
        print("FAIL — faltan archivos del dataset:", report["files"]["missing_files"])
        _write(report, passed=False)
        return 2

    report["hashes"] = verify_hashes(INPUT_ROOT)

    manifest = json.loads((INPUT_ROOT / "dataset_manifest.json").read_text("utf-8"))
    contract = json.loads((INPUT_ROOT / "contract.json").read_text("utf-8"))

    events = pd.read_parquet(INPUT_ROOT / "events_long.parquet")
    windows = pd.read_parquet(INPUT_ROOT / "windows_ml.parquet")
    targets = pd.read_parquet(INPUT_ROOT / "targets_long.parquet")
    folds_outer = pd.read_parquet(INPUT_ROOT / "folds_outer.parquet")

    # El validador viaja con el dataset para que el notebook no dependa de un
    # repositorio privado; si no está disponible, esto es FAIL, no warning.
    sys.path.insert(0, str(INPUT_ROOT))
    try:
        from dataset_contract import validate_all  # type: ignore
    except Exception as exc:  # noqa: BLE001
        report["validator"] = {"passed": False, "detail": "validador ausente: %s" % exc}
        print("FAIL — validador de contrato no disponible")
        _write(report, passed=False)
        return 3

    result = validate_all(
        manifest=manifest,
        events=events,
        windows=windows,
        targets=targets,
        folds_outer=folds_outer,
        contract=contract,
        embargo_ns=int(manifest.get("embargo_ns", 0)),
    )
    report["contract"] = result.to_dict()

    passed = (
        report["files"]["passed"]
        and report["hashes"]["passed"]
        and report["contract"]["passed"]
    )
    _write(report, passed=passed)

    if not passed:
        print("FAIL — el dataset no cumple el contrato. No continuar con EDA.")
        for check in report["contract"]["checks"]:
            if not check["passed"]:
                print("  -", check["name"], "|", check["detail"])
        return 1

    print("PASS — contrato verificado.")
    print("  sesiones:", windows["session_key"].nunique())
    print("  ventanas:", len(windows))
    print("  eventos:", len(events))
    return 0


def _write(report: dict, passed: bool) -> None:
    report["passed"] = passed
    WORKING_ROOT.mkdir(parents=True, exist_ok=True)
    out = WORKING_ROOT / "contract_validation_report.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    raise SystemExit(main())
