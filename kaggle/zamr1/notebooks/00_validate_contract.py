# -*- coding: utf-8 -*-
"""ZAMR-1 Notebook 00 — validación fail-closed de contrato y transporte.

Z0 admite CSV exclusivamente para datos sintéticos truth-known. Todo dataset
real o derivado exige Parquet. No calcula outcomes, retornos, P&L ni holdout.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import sys
from pathlib import Path

import pandas as pd

EXPECTED_SCHEMA = "zamr1_structural_contract_v0"
EXPECTED_PARAMETER_SCHEMA = "zamr1_parameter_registry_v0"
BASE_REQUIRED = (
    "dataset_manifest.json",
    "contract.json",
    "parameter_registry.json",
    "instrument_manifest.json",
    "hashes.sha256",
    "structural_contract.py",
)
WORKING_ROOT = Path(os.environ.get("EDGELAB_KAGGLE_WORKING", "/kaggle/working"))


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def find_input_root(search_root: Path = Path("/kaggle/input")) -> Path:
    explicit = os.environ.get("EDGELAB_KAGGLE_INPUT")
    if explicit:
        root = Path(explicit)
        if not root.is_dir():
            raise RuntimeError("EDGELAB_KAGGLE_INPUT no existe: %s" % root)
        return root

    candidates: list[Path] = []
    if search_root.is_dir():
        for contract_path in search_root.rglob("contract.json"):
            try:
                payload = json.loads(contract_path.read_text("utf-8"))
            except Exception:
                continue
            if payload.get("schema_version") == EXPECTED_SCHEMA:
                candidates.append(contract_path.parent.resolve())
    candidates = sorted(set(candidates))
    if len(candidates) != 1:
        raise RuntimeError(
            "se esperaba exactamente un input ZAMR-1; encontrados=%d: %r"
            % (len(candidates), [str(item) for item in candidates])
        )
    return candidates[0]


def safe_child(root: Path, relative_name: str) -> Path:
    candidate = (root / relative_name).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError("path fuera del dataset: %s" % relative_name) from exc
    return candidate


def verify_hashes(root: Path) -> dict:
    violations: list[str] = []
    checked = 0
    for line_number, raw in enumerate(
        (root / "hashes.sha256").read_text("utf-8").splitlines(), start=1
    ):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        expected, separator, relative_name = line.partition("  ")
        if not separator or len(expected) != 64 or not relative_name.strip():
            violations.append("línea %d malformada" % line_number)
            continue
        target = safe_child(root, relative_name.strip())
        if not target.is_file():
            violations.append("faltante: %s" % relative_name.strip())
            continue
        checked += 1
        if sha256_file(target) != expected.lower():
            violations.append("hash mismatch: %s" % relative_name.strip())
    if checked == 0:
        violations.append("cero archivos verificados")
    return {"passed": not violations, "checked": checked, "violations": violations}


def load_tables(root: Path, manifest: dict):
    transport = manifest.get("transport_format", "parquet")
    stage = manifest.get("pilot_stage")
    if transport == "csv_truth_known":
        if stage != "Z0_SYNTHETIC_ENVIRONMENT":
            raise RuntimeError("CSV permitido sólo para Z0 sintético")
        names = ("events_long.csv", "zones_long.csv")
        if any(not (root / name).is_file() for name in names):
            raise RuntimeError("faltan tablas CSV de Z0")
        return pd.read_csv(root / names[0]), pd.read_csv(root / names[1]), transport
    if transport == "parquet":
        names = ("events_long.parquet", "zones_long.parquet")
        if any(not (root / name).is_file() for name in names):
            raise RuntimeError("faltan tablas Parquet")
        return pd.read_parquet(root / names[0]), pd.read_parquet(root / names[1]), transport
    raise RuntimeError("transport_format no permitido: %s" % transport)


def load_validator(root: Path):
    path = root / "structural_contract.py"
    spec = importlib.util.spec_from_file_location("zamr1_bundle_structural_contract", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("no se pudo cargar structural_contract.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "validate_structural_dataset"):
        raise RuntimeError("el validador no expone validate_structural_dataset")
    return module.validate_structural_dataset


def main() -> int:
    report = {
        "stage": "ZAMR1_00_VALIDATE_CONTRACT",
        "expected_schema": EXPECTED_SCHEMA,
        "outcomes_accessed": False,
        "pnl_accessed": False,
        "holdout_accessed": False,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "internet_expected": False,
            "accelerator_expected": "None/CPU",
        },
    }
    try:
        root = find_input_root()
        report["input_root"] = str(root)
        missing = [name for name in BASE_REQUIRED if not (root / name).is_file()]
        report["required_files"] = {"passed": not missing, "missing": missing}
        if missing:
            raise RuntimeError("faltan archivos base: %r" % missing)

        report["hashes"] = verify_hashes(root)
        if not report["hashes"]["passed"]:
            raise RuntimeError("integridad SHA-256 inválida")

        contract = json.loads((root / "contract.json").read_text("utf-8"))
        manifest = json.loads((root / "dataset_manifest.json").read_text("utf-8"))
        parameter_registry = json.loads((root / "parameter_registry.json").read_text("utf-8"))
        instrument_manifest = json.loads((root / "instrument_manifest.json").read_text("utf-8"))

        report["contract_schema"] = contract.get("schema_version")
        report["parameter_registry_schema"] = parameter_registry.get("schema_version")
        report["instrument_manifest_present"] = bool(instrument_manifest)
        if report["contract_schema"] != EXPECTED_SCHEMA:
            raise RuntimeError("schema de contrato incorrecto")
        if report["parameter_registry_schema"] != EXPECTED_PARAMETER_SCHEMA:
            raise RuntimeError("schema del registro paramétrico incorrecto")
        if not instrument_manifest:
            raise RuntimeError("instrument_manifest vacío")

        events, zones, transport = load_tables(root, manifest)
        report["transport_format"] = transport
        validation = load_validator(root)(
            manifest=manifest, events=events, zones=zones, contract=contract
        )
        report["contract"] = validation.to_dict()
        report["counts"] = {
            "events": len(events),
            "zones": len(zones),
            "sessions": len(set(events["session_key"]) | set(zones["session_key"])),
            "bar_specs": sorted(set(events["bar_spec"]) | set(zones["bar_spec"])),
            "indicators": sorted(set(events["indicator_id"]) | set(zones["indicator_id"])),
        }
        report["passed"] = bool(report["contract"]["passed"])
    except Exception as exc:
        report["passed"] = False
        report["fatal_error"] = "%s: %s" % (type(exc).__name__, exc)

    WORKING_ROOT.mkdir(parents=True, exist_ok=True)
    output = WORKING_ROOT / "contract_validation_report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print("Reporte:", output)
    if not report["passed"]:
        print("FAIL — no continuar con EDA, barridos ni modelos")
        return 1
    print("PASS — contrato ZAMR-1 verificado")
    print(json.dumps(report["counts"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
