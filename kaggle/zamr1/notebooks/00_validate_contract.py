# -*- coding: utf-8 -*-
"""ZAMR-1 / Notebook 00 — validación de contrato y entorno Kaggle.

Uso permitido: bundle sintético Z0 o dataset derivado Z1.
No entrena modelos, no calcula outcomes, no lee retornos/P&L y no admite holdout.
Cualquier ambigüedad o comprobación no ejecutable termina en FAIL.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import platform
import sys
from pathlib import Path

import pandas as pd

EXPECTED_SCHEMA = "zamr1_structural_contract_v0"
KAGGLE_INPUT = Path("/kaggle/input")
WORKING_ROOT = Path(os.environ.get("EDGELAB_KAGGLE_WORKING", "/kaggle/working"))
REQUIRED_FILES = (
    "dataset_manifest.json",
    "contract.json",
    "parameter_registry.json",
    "instrument_manifest.json",
    "hashes.sha256",
    "events_long.parquet",
    "zones_long.parquet",
    "structural_contract.py",
)


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def find_input_root() -> Path:
    explicit = os.environ.get("EDGELAB_KAGGLE_INPUT")
    if explicit:
        root = Path(explicit)
        if not root.is_dir():
            raise RuntimeError("EDGELAB_KAGGLE_INPUT no existe: %s" % root)
        return root

    candidates = []
    if KAGGLE_INPUT.is_dir():
        for contract_path in KAGGLE_INPUT.glob("*/contract.json"):
            try:
                payload = json.loads(contract_path.read_text("utf-8"))
            except Exception:
                continue
            if payload.get("schema_version") == EXPECTED_SCHEMA:
                candidates.append(contract_path.parent)
    if len(candidates) != 1:
        raise RuntimeError(
            "se esperaba exactamente un input ZAMR-1; encontrados=%d: %r"
            % (len(candidates), [str(item) for item in candidates])
        )
    return candidates[0]


def verify_required_files(root: Path) -> dict:
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    return {"passed": not missing, "missing": missing}


def _safe_child(root: Path, relative_name: str) -> Path:
    candidate = (root / relative_name).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError("path fuera del dataset: %s" % relative_name) from exc
    return candidate


def verify_hashes(root: Path) -> dict:
    path = root / "hashes.sha256"
    if not path.is_file():
        return {"passed": False, "checked": 0, "violations": ["hashes.sha256 ausente"]}
    violations = []
    checked = 0
    for line_number, raw in enumerate(path.read_text("utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        expected, separator, relative_name = line.partition("  ")
        if not separator or len(expected) != 64 or not relative_name.strip():
            violations.append("línea %d malformada" % line_number)
            continue
        try:
            target = _safe_child(root, relative_name.strip())
        except RuntimeError as exc:
            violations.append(str(exc))
            continue
        if not target.is_file():
            violations.append("faltante: %s" % relative_name.strip())
            continue
        actual = sha256_file(target)
        checked += 1
        if actual != expected.lower():
            violations.append("hash mismatch: %s" % relative_name.strip())
    if checked == 0:
        violations.append("cero archivos verificados")
    return {"passed": not violations, "checked": checked, "violations": violations}


def environment_report() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "cwd": str(Path.cwd()),
        "internet_expected": False,
        "accelerator_expected": "None/CPU",
    }


def load_validator(root: Path):
    sys.path.insert(0, str(root))
    try:
        module = importlib.import_module("structural_contract")
    except Exception as exc:
        raise RuntimeError("no se pudo importar structural_contract.py: %s" % exc) from exc
    if not hasattr(module, "validate_structural_dataset"):
        raise RuntimeError("el validador no expone validate_structural_dataset")
    return module.validate_structural_dataset


def write_report(report: dict) -> Path:
    WORKING_ROOT.mkdir(parents=True, exist_ok=True)
    output = WORKING_ROOT / "contract_validation_report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Reporte:", output)
    return output


def main() -> int:
    report = {
        "stage": "ZAMR1_00_VALIDATE_CONTRACT",
        "expected_schema": EXPECTED_SCHEMA,
        "environment": environment_report(),
        "outcomes_accessed": False,
        "pnl_accessed": False,
        "holdout_accessed": False,
    }
    try:
        root = find_input_root()
        report["input_root"] = str(root)
        report["required_files"] = verify_required_files(root)
        if not report["required_files"]["passed"]:
            report["passed"] = False
            write_report(report)
            print("FAIL — faltan archivos obligatorios")
            return 2

        report["hashes"] = verify_hashes(root)
        contract = json.loads((root / "contract.json").read_text("utf-8"))
        manifest = json.loads((root / "dataset_manifest.json").read_text("utf-8"))
        parameter_registry = json.loads((root / "parameter_registry.json").read_text("utf-8"))
        instrument_manifest = json.loads((root / "instrument_manifest.json").read_text("utf-8"))
        report["contract_schema"] = contract.get("schema_version")
        report["parameter_registry_schema"] = parameter_registry.get("schema_version")
        report["instrument_manifest_present"] = bool(instrument_manifest)

        events = pd.read_parquet(root / "events_long.parquet")
        zones = pd.read_parquet(root / "zones_long.parquet")
        validate = load_validator(root)
        validation = validate(
            manifest=manifest,
            events=events,
            zones=zones,
            contract=contract,
        )
        report["contract"] = validation.to_dict()
        report["counts"] = {
            "events": len(events),
            "zones": len(zones),
            "sessions": len(set(events["session_key"]) | set(zones["session_key"])),
            "bar_specs": sorted(set(events["bar_spec"]) | set(zones["bar_spec"])),
            "indicators": sorted(set(events["indicator_id"]) | set(zones["indicator_id"])),
        }
        report["passed"] = bool(report["hashes"]["passed"] and report["contract"]["passed"])
    except Exception as exc:  # fail-closed: el detalle queda serializado
        report["passed"] = False
        report["fatal_error"] = "%s: %s" % (type(exc).__name__, exc)

    write_report(report)
    if not report["passed"]:
        print("FAIL — no continuar con EDA, barridos ni modelos")
        for check in report.get("contract", {}).get("checks", []):
            if not check.get("passed"):
                print(" -", check.get("name"), "|", check.get("detail"))
        return 1

    print("PASS — contrato ZAMR-1 verificado")
    print(json.dumps(report["counts"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
