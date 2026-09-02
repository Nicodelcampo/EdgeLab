#!/usr/bin/env python3
"""Entrypoint autocontenido para Kaggle: kernels tipo 'script' NO exponen
archivos hermanos junto al code_file en tiempo de ejecucion (confirmado
empiricamente -- runpy.run_path a un sibling file fallo con
FileNotFoundError: /kaggle/src/nq_contract_regime_manifest_runner.py no
existe). Este archivo es una copia byte-a-byte del cuerpo de
nq_contract_regime_manifest_runner.py (mismo directorio, revisado y testeado
por separado) con sys.argv fijado antes de invocar main() en vez de leer
argv real. Si se edita el runner, este archivo se debe volver a sincronizar.

modo scan-and-build con el template de evidencia SIN aprobar (approved=False,
generado por el propio scan): produce el candidato v2 con status
ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED si falta evidencia real de
completitud, nunca certifica en falso. Aprobar evidencia es una decision
separada, posterior, de Nico -- no de esta corrida.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
REPO_DIR = Path("/kaggle/working/EdgeLab")
CONTRACTS = ["NQ 09-25", "NQ 12-25", "NQ 03-26", "NQ 06-26", "NQ 09-26"]
EXPECTED_SCHEMA = ["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks",
                   "sequence", "instrument", "contract"]
BATCH_ROWS = 1 << 20


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def checkout_code(commit: str) -> str:
    if len(commit) != 40:
        raise SystemExit("--expected-code-commit must be a full 40-char SHA")
    if not (REPO_DIR / ".git").exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        REPO_URL, str(REPO_DIR)], check=True)
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                        "edgelab/**", "specs/**"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"],
                   cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "nq_regime_v2", commit],
                   cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR,
                                     text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_DIR,
                                    text=True).strip()
    if actual != commit or dirty:
        raise SystemExit("code provenance gate failed")
    sys.path.insert(0, str(REPO_DIR))
    return actual


def find_parquet(root: Path, label: str) -> Path:
    hits = sorted(root.rglob(label.replace(" ", "_") + "_ticks.parquet"))
    if len(hits) != 1:
        raise RuntimeError(f"{label}: expected one parquet, found {len(hits)}")
    return hits[0]


def scan_contract(path: Path, expected_label: str):
    import numpy as np
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from edgelab.kaggle.inventory import footer_census
    from edgelab.kaggle.seal import HOLDOUT_START_YMD
    from edgelab.kaggle.sessions_cme import (is_maintenance_break,
        minutes_since_session_open, session_bounds_utc_ns, trade_date_ymd)
    from edgelab.research.nq_contract_regime_manifest_build import canonical_contract_from_columns

    footer = footer_census(str(path))
    if footer.get("column_names") != EXPECTED_SCHEMA:
        raise RuntimeError(f"{path.name}: schema mismatch")
    holdout_open_ns, _ = session_bounds_utc_ns(HOLDOUT_START_YMD)
    if int(footer["ts_max_ns"]) >= holdout_open_ns:
        raise RuntimeError(f"{path.name}: footer reaches holdout; no pages read")

    sessions, rows = {}, 0
    last_ts = last_seq = None
    bad_ts = bad_seq = bad_volume = 0
    raw_instruments, raw_contracts = set(), set()
    pf = pq.ParquetFile(path)
    cols = ["ts_utc_ns", "volume", "sequence", "instrument", "contract"]
    for batch in pf.iter_batches(batch_size=BATCH_ROWS, columns=cols):
        ts = np.asarray(batch.column(0), dtype=np.int64)
        vol = np.asarray(batch.column(1), dtype=np.int64)
        seq = np.asarray(batch.column(2), dtype=np.int64)
        if not len(ts):
            continue
        rows += len(ts)
        instruments = {str(x) for x in pc.unique(batch.column(3)).to_pylist()}
        contracts = {str(x) for x in pc.unique(batch.column(4)).to_pylist()}
        raw_instruments |= instruments; raw_contracts |= contracts
        for inst in instruments:
            for con in contracts:
                if canonical_contract_from_columns(inst, con) != expected_label:
                    raise RuntimeError(f"{path.name}: internal identity mismatch")
        dts = np.diff(ts if last_ts is None else np.concatenate(([last_ts], ts)))
        dsq = np.diff(seq if last_seq is None else np.concatenate(([last_seq], seq)))
        bad_ts += int((dts < 0).sum()); bad_seq += int((dsq <= 0).sum())
        bad_volume += int((vol <= 0).sum())
        last_ts, last_seq = int(ts[-1]), int(seq[-1])
        days = trade_date_ymd(ts)
        maint = is_maintenance_break(ts)
        minutes = minutes_since_session_open(ts)
        for day in np.unique(days):
            m = days == day
            rec = sessions.setdefault(int(day), {"volume": 0.0,
                "volume_in_maintenance": 0.0, "tick_count": 0,
                "maintenance_tick_count": 0, "first_ts_ns": None,
                "last_ts_ns": None, "active_minutes": set()})
            rec["volume"] += float(vol[m & ~maint].sum())
            rec["volume_in_maintenance"] += float(vol[m & maint].sum())
            rec["tick_count"] += int(m.sum())
            rec["maintenance_tick_count"] += int((m & maint).sum())
            tt = ts[m]; lo, hi = int(tt.min()), int(tt.max())
            rec["first_ts_ns"] = lo if rec["first_ts_ns"] is None else min(lo, rec["first_ts_ns"])
            rec["last_ts_ns"] = hi if rec["last_ts_ns"] is None else max(hi, rec["last_ts_ns"])
            rec["active_minutes"].update(int(x) for x in np.unique(minutes[m & ~maint]))
    if rows != int(footer["rows"]) or bad_ts or bad_seq or bad_volume:
        raise RuntimeError(f"{path.name}: structural gate failed rows={rows}, "
                           f"bad_ts={bad_ts}, bad_seq={bad_seq}, bad_volume={bad_volume}")
    for rec in sessions.values():
        rec["active_minutes"] = len(rec["active_minutes"])
    source = {"file": path.name, "bytes": path.stat().st_size, "rows": rows,
              "row_groups": int(footer["row_groups"]), "schema": EXPECTED_SCHEMA,
              "ts_min_ns": int(footer["ts_min_ns"]), "ts_max_ns": int(footer["ts_max_ns"]),
              "sha256": sha256_file(path),
              "raw_instrument_values": sorted(raw_instruments),
              "raw_contract_values": sorted(raw_contracts), "identity_verified": True}
    return source, sessions


def scan_all(input_root: Path, code_commit: str):
    from edgelab.research.nq_contract_regime_manifest_build import OBSERVATIONS_SCHEMA
    sources, sessions, hashes = {}, {}, {}
    for label in CONTRACTS:
        path = find_parquet(input_root, label)
        print(f"[*] {label}: {path}", flush=True)
        source, by_day = scan_contract(path, label)
        sources[label] = source; hashes[label] = source["sha256"]
        sessions[label] = {str(k): v for k, v in sorted(by_day.items())}
    return {"schema_version": OBSERVATIONS_SCHEMA,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_identity": {"root": "NQ",
                "dataset": "nicolasbuttaro/edgelab-ticks-nq-preholdout",
                "contract_parquet_sha256": hashes, "repo_commit": code_commit},
            "contracts": sources, "sessions": sessions,
            "outcomes_accessed": False, "holdout_accessed": False}


def build_candidate(observations_path: Path, evidence_path: Path, out: Path):
    from edgelab.data.contract_regime import build_contract_regime, validate_contract_regime
    from edgelab.research.nq_contract_regime_manifest_build import (
        OBSERVATIONS_SCHEMA, prepare_nq_manifest_inputs)
    observed, evidence = read_json(observations_path), read_json(evidence_path)
    if observed.get("schema_version") != OBSERVATIONS_SCHEMA:
        raise RuntimeError("wrong observations schema")
    prepared = prepare_nq_manifest_inputs(
        per_contract_observations=observed["sessions"],
        completeness_evidence=evidence, source_identity=observed["source_identity"])
    manifest = build_contract_regime(**prepared["regime_inputs"])
    validate_contract_regime(manifest)
    if any(date(int(str(d)[:4]), int(str(d)[4:6]), int(str(d)[6:])).weekday() >= 5
           for d in manifest["calendar_trade_dates"]):
        raise RuntimeError("weekend leaked into manifest")
    write_json(out / "nq_contract_regime_diagnostics_v2.json", prepared)
    certified = prepared["ready_for_certified_manifest"] and evidence.get("approved") is True
    name = "nq_contract_regime_manifest_v1.json" if certified else "nq_contract_regime_candidate_v2.json"
    write_json(out / name, manifest)
    return {"status": "PASS_CERTIFIED" if certified else "ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED",
            "manifest_file": name, "manifest_sha256": manifest["manifest_sha256"],
            "roll_schedule_sha256": manifest["manifest_sha256"] if certified else None}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("scan", "build", "scan-and-build"), required=True)
    p.add_argument("--expected-code-commit", required=True)
    p.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    p.add_argument("--output-dir", type=Path,
                   default=Path("/kaggle/working/nq_contract_regime_manifest_v2"))
    p.add_argument("--observations", type=Path); p.add_argument("--evidence", type=Path)
    args = p.parse_args(); commit = checkout_code(args.expected_code_commit)
    out = args.output_dir; out.mkdir(parents=True, exist_ok=True)
    observations = args.observations
    if args.mode in {"scan", "scan-and-build"}:
        observed = scan_all(args.input_root, commit)
        observations = out / "nq_contract_session_observations_v2.json"
        write_json(observations, observed)
        from edgelab.research.nq_contract_regime_manifest_build import build_completeness_evidence_template
        write_json(out / "nq_complete_session_evidence_template_v1.json",
                   build_completeness_evidence_template(observed["sessions"], observed["source_identity"]))
    if args.mode in {"build", "scan-and-build"} and observations and args.evidence:
        result = build_candidate(observations, args.evidence, out)
    else:
        result = {"status": "ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED",
                  "roll_schedule_sha256": None}
    status = {**result, "runner_version": "nq_contract_regime_manifest_runner_v2",
              "code_commit": commit, "runner_sha256": sha256_file(Path(__file__)),
              "heavy_scan_executed": args.mode in {"scan", "scan-and-build"},
              "outcomes_accessed": False, "holdout_accessed": False,
              "price_adjustment": "NONE_ACTUAL_TRADED_PRICES",
              "state_boundary": "RESET_AT_CONTRACT_ROLL",
              "superseded_artifact_commit": "c3d575fbdfc989952aace8572630a8c6ce046061",
              "superseded_artifact_status": "PROVISIONAL_INVALID_CALENDAR_DO_NOT_USE_FOR_EF0"}
    write_json(out / "contract_regime_status.json", status)
    hashes = {f.name: sha256_file(f) for f in out.iterdir()
              if f.is_file() and f.name != "sha256_manifest.json"}
    write_json(out / "sha256_manifest.json", hashes)
    print(json.dumps(status, indent=2), flush=True)
    return 0 if status["status"] == "PASS_CERTIFIED" else 3


if __name__ == "__main__":
    EXPECTED_CODE_COMMIT = "ab89de5ff176bab5abb38cc17c5e5f6db568f763"
    OUTPUT_DIR = "/kaggle/working/nq_contract_regime_manifest_v2"
    sys.argv = [
        "nq_contract_regime_manifest_runner.py",
        "--mode", "scan-and-build",
        "--expected-code-commit", EXPECTED_CODE_COMMIT,
        "--output-dir", OUTPUT_DIR,
        "--evidence", f"{OUTPUT_DIR}/nq_complete_session_evidence_template_v1.json",
    ]
    raise SystemExit(main())
