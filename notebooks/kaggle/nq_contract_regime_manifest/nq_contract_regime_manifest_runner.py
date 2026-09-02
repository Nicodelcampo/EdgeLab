#!/usr/bin/env python3
"""Kaggle entrypoint: agrega volumen real por trade_date sobre los 5 contratos
NQ (03-26, 06-26, 09-25, 09-26, 12-25) y construye el `contract_regime_manifest_v1`
causal (edgelab/data/contract_regime.py). Target-free, no toca outcomes.

No es el escaneo pesado de BigTrap2Absorption: solo lee 2 columnas por
parquet (ts_utc_ns, volume) via pyarrow columnar read y agrega por sesion.
No corre ningun indicador ni construye barras.

NO SE CORRE SIN AUTORIZACION EXPLICITA -- preparado y testeado localmente
(edgelab/research/nq_contract_regime_manifest_build.py,
tests/research/test_nq_contract_regime_manifest_build.py, 5 tests en verde),
falta la corrida real sobre los 5 parquets (~2,26 GB, 119M ticks).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "PENDIENTE_FIJAR_COMMIT_ANTES_DE_CORRER"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT_ROOT = Path("/kaggle/input")
NQ_CONTRACTS = ["NQ 03-26", "NQ 06-26", "NQ 09-25", "NQ 09-26", "NQ 12-25"]

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
    subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                     "edgelab/**", "tools/**"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "200"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "-B", "nq_regime_manifest", EXPECTED_COMMIT], cwd=REPO_DIR, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EXPECTED_COMMIT")
print("repo_commit=", actual, flush=True)

sys.path.insert(0, str(REPO_DIR))
import pyarrow.parquet as pq  # noqa: E402
from edgelab.data.contract_regime import build_contract_regime, canonical_sha256  # noqa: E402
from edgelab.research.nq_contract_regime_manifest_build import build_nq_manifest_inputs  # noqa: E402

sys.path.insert(0, str(REPO_DIR / "tools"))
from bt2_absorption_param_sweep import session_dates_from_ns, file_sha256  # noqa: E402


def find_parquet(label: str) -> Path:
    filename = label.replace(" ", "_") + "_ticks.parquet"
    hits = list(KAGGLE_INPUT_ROOT.rglob(filename))
    if not hits:
        raise FileNotFoundError(f"{filename} no encontrado bajo {KAGGLE_INPUT_ROOT}")
    return hits[0]


def daily_volume_for_contract(path: Path) -> dict:
    """Lee SOLO ts_utc_ns y volume (columnar, no decodifica el resto del
    schema), agrupa por trade_date via session_dates_from_ns (mismo mapeo
    causal de sesion CME 17:00 CT ya validado en el proyecto)."""
    table = pq.read_table(str(path), columns=["ts_utc_ns", "volume"])
    ts_ns = table.column("ts_utc_ns").to_numpy(zero_copy_only=False)
    volume = table.column("volume").to_numpy(zero_copy_only=False)
    trade_dates = session_dates_from_ns(ts_ns)  # 'YYYYMMDD' string por tick

    import numpy as np
    by_date: dict[int, float] = {}
    order = np.argsort(trade_dates, kind="stable")
    sorted_dates = trade_dates[order]
    sorted_vol = volume[order]
    boundaries = np.flatnonzero(np.concatenate(([True], sorted_dates[1:] != sorted_dates[:-1])))
    boundaries = np.append(boundaries, len(sorted_dates))
    for i in range(len(boundaries) - 1):
        d = int(sorted_dates[boundaries[i]])
        by_date[d] = float(sorted_vol[boundaries[i]:boundaries[i + 1]].sum())
    return by_date


def main() -> int:
    per_contract_volume = {}
    contract_hashes = {}
    for label in NQ_CONTRACTS:
        path = find_parquet(label)
        print(f"[*] {label}: {path.name}", flush=True)
        contract_hashes[label] = file_sha256(path)
        by_date = daily_volume_for_contract(path)
        per_contract_volume[label] = by_date
        print(f"    n_trade_dates={len(by_date)} vol_total={sum(by_date.values()):,.0f}", flush=True)

    source_identity = {
        "root": "NQ", "dataset": "nicolasbuttaro/edgelab-ticks-nq-preholdout",
        "contract_parquet_sha256": contract_hashes, "repo_commit": EXPECTED_COMMIT,
    }
    inputs = build_nq_manifest_inputs(per_contract_volume, source_identity)
    manifest = build_contract_regime(**inputs)

    out_dir = Path("/kaggle/working/nq_contract_regime_manifest")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "nq_contract_regime_manifest_v1.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    daily_table_path = out_dir / "nq_daily_volume_table.json"
    daily_table_path.write_text(
        json.dumps(per_contract_volume, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    crossovers = [row for row in manifest["daily_assignments"] if row.get("decision") == "ROLL_FORWARD"]
    print(f"escrito: {manifest_path}")
    print(f"escrito: {daily_table_path}")
    print(f"manifest_sha256={manifest['manifest_sha256']}")
    print(f"n_intervals={len(manifest['intervals'])} n_crossovers={len(crossovers)}")
    for c in crossovers:
        print(f"  ROLL_FORWARD {c['trade_date']}: -> {c['active_contract']} "
              f"(leader_over_current={c['leader_over_current']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
