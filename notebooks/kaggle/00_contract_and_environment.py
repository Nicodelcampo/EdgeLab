#!/usr/bin/env python3
"""00_contract_and_environment - identidad, licencia, hashes y preflight.

Primer notebook del pipeline del Contrato Kaggle v2. NO lee datos: solo footers
de Parquet, variables de entorno y hashes. Corre en minutos y decide si vale la
pena gastar una sesion de 12 h.

Gates que aplica:
  G0  identidad de la corrida y del codigo (run_manifest.json)
  G1  censo del dataset por footer y reconciliacion contra el censo local
  G2  presupuesto tecnico contractual (tamano, archivos top-level)
  G3  pre-screen del holdout por estadisticas de footer (sin leer datos)
  G4  gate legal M0: existencia de DATA_LICENSE_DECISION.md

Salida en /kaggle/working/reports/: run_manifest.json,
dataset_census.json, contract_validation_report.json

Uso en Kaggle: adjuntar (a) el dataset de ticks y (b) un code dataset con el
paquete `edgelab`. Internet OFF. Save & Run All.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

# --------------------------------------------------------------------- config
INPUT_CANDIDATES = (
    "/kaggle/input/edgelab-cme-futures-universe",
    "/kaggle/input/edgelab-cme-research",
    os.environ.get("EDGELAB_INPUT_DIR", ""),
)
CODE_CANDIDATES = (
    "/kaggle/input/edgelab-code",
    "/kaggle/input/edgelab-package",
    "/kaggle/usr/lib/edgelab",
    os.environ.get("EDGELAB_CODE_DIR", ""),
    "/data/replica",
)
OUT_DIR = os.environ.get("EDGELAB_OUT_DIR", "/kaggle/working/reports")
NOTEBOOK_ID = "00_contract_and_environment"
DATASET_SCHEMA_VERSION = "ticks_l1_v1"

# Censo local declarado (build 2026-08-14, `build_kaggle_bundle.py`).
# Es la afirmacion a refutar: si el censo de Kaggle no cierra contra esto, el
# upload no es el bundle que se construyo.
EXPECTED_CENSUS = {
    "assets": 11,
    "contracts": 56,
    "ticks": 1_078_414_656,
    "gib": 16.74,
    "by_asset_ticks": {
        "ES": 280_572_867,
        "MNQ": 348_596_819,
        "MES": 178_899_220,
        "NQ": 127_890_620,
        "GC": 39_789_544,
        "ZB": 30_187_184,
        "YM": 23_244_421,
        "6E": 20_455_828,
        "6J": 15_552_894,
        "6B": 8_320_560,
        "MBT": 4_904_699,
    },
    "by_asset_contracts": {
        "ES": 5, "MNQ": 5, "MES": 5, "NQ": 5, "GC": 5, "ZB": 5,
        "YM": 5, "6E": 5, "6J": 5, "6B": 5, "MBT": 6,
    },
}
EXPECTED_SCHEMA = [
    "ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks",
    "sequence", "instrument", "contract",
]
# Ancla de identidad conocida: el unico archivo cuyo sha256 esta verificado
# contra el paquete del auditor (P-16).
ANCHOR_FILE_SHA256 = {
    "6E_09-26_ticks.parquet": (
        "1311bc5ea91a111d95f17da84d9a6ee6323920686b0b0873c04d8f3dc94a9652"
    )
}
VERIFY_ANCHOR_SHA256 = True  # solo ese archivo: hashear 16 GB no entra en gate


def _first_existing(paths) -> str | None:
    for p in paths:
        if p and os.path.isdir(p):
            return p
    return None


def _bootstrap() -> str:
    code_dir = _first_existing(CODE_CANDIDATES)
    if code_dir is None:
        raise SystemExit(
            "no se encontro el paquete edgelab; adjuntar el code dataset"
        )
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)
    return code_dir


CODE_DIR = _bootstrap()
from edgelab.kaggle import identity, inventory  # noqa: E402
from edgelab.kaggle.seal import HOLDOUT_START_YMD  # noqa: E402
from edgelab.kaggle.sessions_cme import session_bounds_utc_ns  # noqa: E402

INPUT_DIR = _first_existing(INPUT_CANDIDATES)
if INPUT_DIR is None:
    raise SystemExit("no se encontro el dataset de entrada")
os.makedirs(OUT_DIR, exist_ok=True)
print(f"code_dir={CODE_DIR}\ninput_dir={INPUT_DIR}\nout_dir={OUT_DIR}")

# ------------------------------------------------------------------ G0 identidad
t0 = time.time()
manifest = identity.build_run_manifest(
    notebook_id=NOTEBOOK_ID,
    stage="PREFLIGHT",
    fields={
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "code_commit": os.environ.get("EDGELAB_CODE_COMMIT", "UNDECLARED"),
        "code_dirty": os.environ.get("EDGELAB_CODE_DIRTY", "UNDECLARED"),
        "builder_id": "kaggle_notebook_00",
        "cutoff_policy_id": "grid_60s_v1_PREREGISTERED",
    },
    extra={"input_dir": INPUT_DIR, "code_dir": CODE_DIR},
)
identity.write_json(os.path.join(OUT_DIR, "run_manifest.json"), manifest)
print("G0 manifest_sha256:", manifest["manifest_sha256"])
print("G0 environment_manifest_sha256:", manifest["environment_manifest_sha256"])

# --------------------------------------------------------------------- G1 censo
records = inventory.census_dir(INPUT_DIR)
summary = inventory.summarize_census(records)
top_level = len(
    [e for e in os.listdir(INPUT_DIR) if not e.startswith(".")]
)
identity.write_json(
    os.path.join(OUT_DIR, "dataset_census.json"),
    {"input_dir": INPUT_DIR, "top_level_entries": top_level,
     "summary": summary, "files": records},
)
print(f"G1 archivos ok={summary['files_ok']} error={summary['files_error']} "
      f"filas={summary['total_rows']:,} gib={summary['total_gib']}")

recon = {
    "expected": EXPECTED_CENSUS,
    "observed": {
        "assets": summary["assets"],
        "contracts": summary["files_ok"],
        "ticks": summary["total_rows"],
        "gib": summary["total_gib"],
    },
    "diffs": {},
}
recon["diffs"]["assets"] = summary["assets"] - EXPECTED_CENSUS["assets"]
recon["diffs"]["contracts"] = summary["files_ok"] - EXPECTED_CENSUS["contracts"]
recon["diffs"]["ticks"] = summary["total_rows"] - EXPECTED_CENSUS["ticks"]
recon["by_asset"] = {}
for asset, exp_ticks in EXPECTED_CENSUS["by_asset_ticks"].items():
    obs = summary["by_asset"].get(asset, {})
    recon["by_asset"][asset] = {
        "expected_ticks": exp_ticks,
        "observed_ticks": obs.get("rows"),
        "delta_ticks": (obs.get("rows", 0) - exp_ticks) if obs else None,
        "expected_contracts": EXPECTED_CENSUS["by_asset_contracts"][asset],
        "observed_contracts": obs.get("contracts"),
    }
recon["schema_matches_expected"] = summary.get("schema") == EXPECTED_SCHEMA
recon["schema_observed"] = summary.get("schema")
recon["schema_variants"] = summary.get("schema_variants")
recon["pass"] = (
    recon["diffs"]["ticks"] == 0
    and recon["diffs"]["contracts"] == 0
    and recon["diffs"]["assets"] == 0
    and summary["files_error"] == 0
    and recon["schema_matches_expected"]
)
print("G1 reconciliacion:", "PASS" if recon["pass"] else "FAIL", recon["diffs"])

# --------------------------------------------------------------- G2 presupuesto
budget = inventory.budget_gates(summary, top_level_files=top_level)
print("G2 presupuesto:", budget["verdict"], "fallos:", budget["failed"])

# ------------------------------------------------------- G3 pre-screen holdout
holdout_open_ns, _ = session_bounds_utc_ns(HOLDOUT_START_YMD)
flagged = []
for r in records:
    if "ts_max_ns" not in r:
        continue
    if int(r["ts_max_ns"]) >= holdout_open_ns:
        flagged.append(
            {
                "file": r["file"],
                "ts_max_utc": r.get("ts_max_utc"),
                "rows": r.get("rows"),
            }
        )
prescreen = {
    "holdout_session_open_utc_ns": holdout_open_ns,
    "rule": "ts_max_ns >= apertura (17:00 CT del 2026-06-30) de la sesion 2026-07-01",
    "files_flagged": len(flagged),
    "flagged": flagged,
    "pass": len(flagged) == 0,
    "note": (
        "FAIL aqui no invalida el archivo: significa que el dataset contiene "
        "filas de holdout y que el sello debe aplicarse SIEMPRE al leer. El "
        "contrato exige ademas que el dataset exploratorio no las contenga "
        "fisicamente (ver enmienda v2.1)."
    ),
}
print(f"G3 pre-screen holdout: {len(flagged)} archivos con filas posteriores al sello")

# ---------------------------------------------------------- G3b ancla de identidad
anchor = {}
if VERIFY_ANCHOR_SHA256:
    for r in records:
        want = ANCHOR_FILE_SHA256.get(r.get("file", ""))
        if not want:
            continue
        got = identity.sha256_file(r["path"])
        anchor[r["file"]] = {
            "expected_sha256": want,
            "observed_sha256": got,
            "match": got == want,
            "bytes": r["bytes"],
            "rows": r.get("rows"),
        }
        print(f"G3b ancla {r['file']}: {'MATCH' if got == want else 'MISMATCH'}")

# ------------------------------------------------------------------- G4 legal M0
license_paths = [
    os.path.join(INPUT_DIR, "DATA_LICENSE_DECISION.md"),
    os.path.join(CODE_DIR, "DATA_LICENSE_DECISION.md"),
    os.path.join(CODE_DIR, "docs", "DATA_LICENSE_DECISION.md"),
]
license_found = next((p for p in license_paths if os.path.exists(p)), None)
legal = {
    "searched": license_paths,
    "found": license_found,
    "sha256": identity.sha256_file(license_found) if license_found else None,
    "pass": license_found is not None,
    "rule": "M0: sin DATA_LICENSE_DECISION.md no se autoriza dato real (P-07)",
}
print("G4 gate legal M0:", "PASS" if legal["pass"] else "FAIL (P-07 abierta)")

# ------------------------------------------------------------------- veredicto
gates = {
    "G0_identity": {"pass": True},
    "G1_census_reconciliation": {"pass": bool(recon["pass"]), "detail": recon["diffs"]},
    "G2_budget": {"pass": budget["verdict"] == "PASS", "detail": budget["failed"]},
    "G3_holdout_prescreen": {"pass": prescreen["pass"], "detail": prescreen["files_flagged"]},
    "G3b_identity_anchor": {
        "pass": all(v["match"] for v in anchor.values()) if anchor else None,
    },
    "G4_legal_M0": {"pass": legal["pass"]},
}
blocking = [k for k, v in gates.items() if v["pass"] is False]
if not blocking:
    verdict = "PASS"
elif gates["G2_budget"]["pass"] is False:
    verdict = "ABSTAIN_CAPACITY"
else:
    verdict = "BLOCKED"

report = {
    "notebook_id": NOTEBOOK_ID,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "elapsed_seconds": round(time.time() - t0, 2),
    "input_dir": INPUT_DIR,
    "verdict": verdict,
    "blocking_gates": blocking,
    "gates": gates,
    "census_summary": summary,
    "reconciliation": recon,
    "budget": budget,
    "holdout_prescreen": prescreen,
    "identity_anchor": anchor,
    "legal_gate": legal,
    "manifest_sha256": manifest["manifest_sha256"],
}
identity.write_json(os.path.join(OUT_DIR, "contract_validation_report.json"), report)
print("\n" + json.dumps({"verdict": verdict, "blocking": blocking}, indent=2))
print("artefactos en", OUT_DIR)
