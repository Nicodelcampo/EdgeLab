#!/usr/bin/env python3
"""01_dataset_validation - schema, causalidad, firewall del holdout, calendario.

Segundo notebook del pipeline del Contrato Kaggle v2. Recorre los 56 archivos
de ticks por batches (peak RSS acotado), aplica el sello del holdout por trade
date de Chicago y publica el calendario empirico y la cuarentena.

Lo que mide, por archivo y por trade date:
  * filas, rango temporal, monotonicidad de ts y de sequence, duplicados
  * cotizaciones validas, cruzadas, spread, trade dentro/fuera del quote
  * minutos activos por sesion (bateria P-14/P-15 generalizada a 11 activos)
  * filas cortadas por el sello, y el leak que produciria un corte UTC ingenuo

NO construye features, targets ni folds: outcomes_accessed=False. Es el insumo
de 02_capacity_benchmark y del calendar_manifest congelado.

Checkpoint por archivo en OUT_DIR/checkpoints: la sesion de 12 h se puede
reanudar sin repetir trabajo (relevante para los 348 M ticks de MNQ).
"""
from __future__ import annotations

import gc
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
NOTEBOOK_ID = "01_dataset_validation"
BATCH_ROWS = int(os.environ.get("EDGELAB_BATCH_ROWS", 1 << 21))  # ~2 M filas
COLUMNS = ("ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")
MAX_FILES = int(os.environ.get("EDGELAB_MAX_FILES", "0")) or None
# Umbral de cuarentena: sesiones con actividad anomala se listan, no se borran.
FULL_SESSION_MINUTES = 1380


def _first_existing(paths) -> str | None:
    for p in paths:
        if p and os.path.isdir(p):
            return p
    return None


code_dir = _first_existing(CODE_CANDIDATES)
if code_dir is None:
    raise SystemExit("no se encontro el paquete edgelab")
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

import numpy as np  # noqa: E402

from edgelab.kaggle import identity, integrity, seal  # noqa: E402
from edgelab.kaggle.streaming import TickStreamAccumulator  # noqa: E402

INPUT_DIR = _first_existing(INPUT_CANDIDATES)
if INPUT_DIR is None:
    raise SystemExit("no se encontro el dataset de entrada")
CKPT_DIR = os.path.join(OUT_DIR, "checkpoints")
os.makedirs(CKPT_DIR, exist_ok=True)

try:
    import pyarrow.parquet as pq
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"pyarrow requerido: {exc}")


def list_files() -> list[str]:
    out = []
    for dirpath, _dirs, files in os.walk(INPUT_DIR):
        for f in sorted(files):
            if f.endswith(".parquet"):
                out.append(os.path.join(dirpath, f))
    out.sort()
    return out[:MAX_FILES] if MAX_FILES else out


def validate_file(path: str) -> dict:
    """Streaming por row-group/batch. Solo las columnas necesarias."""
    pf = pq.ParquetFile(path)
    names = set(pf.schema_arrow.names)
    cols = [c for c in COLUMNS if c in names]
    missing = [c for c in COLUMNS if c not in names]
    acc = TickStreamAccumulator()
    t0 = time.time()
    nbatch = 0
    for tbl in pf.iter_batches(batch_size=BATCH_ROWS, columns=cols):
        nbatch += 1
        arrs = {
            c: np.asarray(tbl.column(cols.index(c)), dtype=np.int64)
            for c in cols
        }
        acc.update(**arrs)
        del arrs, tbl
    res = acc.finalize()
    del acc
    gc.collect()
    res["file"] = os.path.basename(path)
    res["path"] = path
    res["bytes"] = os.path.getsize(path)
    res["columns_used"] = cols
    res["columns_missing"] = missing
    res["schema"] = list(pf.schema_arrow.names)
    res["row_groups"] = pf.metadata.num_row_groups
    res["rows_footer"] = pf.metadata.num_rows
    res["rows_streamed"] = res["tick_checks"].get("rows", 0)
    res["rows_match_footer"] = res["rows_footer"] == res["rows_streamed"]
    res["batches"] = nbatch
    res["elapsed_seconds"] = round(time.time() - t0, 2)
    res["ticks_per_second"] = (
        round(res["rows_streamed"] / max(res["elapsed_seconds"], 1e-9))
    )
    act = res["activity"]
    res["quarantine"] = integrity.missing_active_minutes(
        act, min_minutes_full_session=FULL_SESSION_MINUTES
    )
    res["weekday_histogram"] = integrity.weekday_histogram(act)
    return res


def file_gates(res: dict) -> dict:
    tc = res["tick_checks"]
    sl = res["seal"]
    return {
        "schema_complete": {"pass": not res["columns_missing"]},
        "rows_match_footer": {"pass": bool(res["rows_match_footer"])},
        "ts_monotonic": {"pass": bool(tc.get("ts_monotonic_non_decreasing", False))},
        "sequence_strictly_increasing": {
            "pass": bool(tc.get("sequence_monotonic_increasing", False))
        },
        "no_crossed_quotes": {"pass": int(tc.get("quote_crossed", 0)) == 0},
        "no_non_positive_volume": {"pass": int(tc.get("volume_non_positive", 0)) == 0},
        "trades_inside_quote": {
            "pass": int(tc.get("trade_outside_quote", 0)) == 0,
            "value": tc.get("trade_inside_quote_frac"),
        },
        "no_weekend_sessions": {
            "pass": int(res["weekday_histogram"].get("5", 0)) == 0
            and int(res["weekday_histogram"].get("6", 0)) == 0
        },
        "holdout_physically_absent": {
            "pass": int(sl.get("rows_cut_holdout", 0)) == 0,
            "value": sl.get("rows_cut_holdout"),
        },
    }


files = list_files()
print(f"input_dir={INPUT_DIR}\narchivos={len(files)} batch_rows={BATCH_ROWS}")

per_file: list[dict] = []
t_start = time.time()
for i, path in enumerate(files, 1):
    ck = os.path.join(CKPT_DIR, os.path.basename(path) + ".json")
    if os.path.exists(ck):
        with open(ck, encoding="utf-8") as fh:
            res = json.load(fh)
        print(f"[{i}/{len(files)}] {res['file']}: checkpoint reutilizado")
    else:
        res = validate_file(path)
        res["gates"] = file_gates(res)
        res["gates_failed"] = [k for k, v in res["gates"].items() if not v["pass"]]
        identity.write_json(ck, res)
        tc, sl = res["tick_checks"], res["seal"]
        print(
            f"[{i}/{len(files)}] {res['file']}: {tc['rows']:,} filas "
            f"({res['ticks_per_second']:,}/s) sesiones={res['activity']['trade_dates']} "
            f"sello_cortadas={sl['rows_cut_holdout']:,} "
            f"leak_utc={sl['rows_leaked_by_naive_utc_cut']:,} "
            f"gates_fail={res['gates_failed']}"
        )
    per_file.append(res)

# ------------------------------------------------------------------ agregacion
seal_reports = []
for res in per_file:
    r = seal.SealReport(
        rows_in=res["seal"]["rows_in"],
        rows_kept=res["seal"]["rows_kept"],
        rows_cut_holdout=res["seal"]["rows_cut_holdout"],
        rows_cut_after_holdout=res["seal"]["rows_cut_after_holdout"],
        first_trade_date_kept=res["seal"]["first_trade_date_kept"],
        last_trade_date_kept=res["seal"]["last_trade_date_kept"],
        first_trade_date_cut=res["seal"]["first_trade_date_cut"],
        last_trade_date_cut=res["seal"]["last_trade_date_cut"],
        cut_rows_by_trade_date={
            int(k): int(v) for k, v in res["seal"]["cut_rows_by_trade_date"].items()
        },
        rows_leaked_by_naive_utc_cut=res["seal"]["rows_leaked_by_naive_utc_cut"],
    )
    seal_reports.append(r)
global_seal = seal.merge_reports(seal_reports)

calendar: dict[int, dict] = {}
for res in per_file:
    asset = res["file"].split("_")[0]
    for day, rec in res["activity"]["by_trade_date"].items():
        day = int(day)
        if day > seal.RESEARCH_MAX_YMD:
            continue  # el calendario de investigacion nunca incluye holdout
        cal = calendar.setdefault(
            day, {"assets": {}, "ticks": 0, "minutes_active_max": 0}
        )
        cal["assets"][asset] = cal["assets"].get(asset, 0) + int(rec["ticks"])
        cal["ticks"] += int(rec["ticks"])
        cal["minutes_active_max"] = max(
            cal["minutes_active_max"], int(rec.get("minutes_active") or 0)
        )
calendar_manifest = {
    "rule": "trade date = sesion CME America/Chicago, apertura 17:00 CT",
    "research_max_trade_date": seal.RESEARCH_MAX_YMD,
    "sessions": len(calendar),
    "first_session": min(calendar) if calendar else None,
    "last_session": max(calendar) if calendar else None,
    "by_session": {str(k): v for k, v in sorted(calendar.items())},
}
calendar_manifest["calendar_manifest_sha256"] = identity.sha256_json(
    {k: v for k, v in calendar_manifest.items()}
)

all_failed: dict[str, list[str]] = {}
for res in per_file:
    for g in res.get("gates_failed", []):
        all_failed.setdefault(g, []).append(res["file"])

quarantine = {
    res["file"]: {
        "n_partial": res["quarantine"]["n_partial"],
        "n_sparse": res["quarantine"]["n_sparse"],
        "sparse_trade_dates": res["quarantine"]["sparse_trade_dates"],
    }
    for res in per_file
}

totals = {
    "files": len(per_file),
    "rows_streamed": sum(r["rows_streamed"] for r in per_file),
    "bytes": sum(r["bytes"] for r in per_file),
    "elapsed_seconds": round(time.time() - t_start, 2),
    "sessions_research": len(calendar),
}
verdict = "PASS"
if any(
    g in all_failed
    for g in (
        "schema_complete",
        "rows_match_footer",
        "ts_monotonic",
        "sequence_strictly_increasing",
    )
):
    verdict = "CONTRACT_FAIL"
elif "holdout_physically_absent" in all_failed:
    verdict = "SEAL_ENFORCED_BUT_HOLDOUT_PRESENT"

report = {
    "notebook_id": NOTEBOOK_ID,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "input_dir": INPUT_DIR,
    "verdict": verdict,
    "totals": totals,
    "gates_failed_by_type": {k: sorted(v) for k, v in sorted(all_failed.items())},
    "global_seal": global_seal.to_dict(include_kept_list=True),
    "quarantine": quarantine,
    "per_file": [
        {
            k: v
            for k, v in res.items()
            if k not in ("activity", "path")
        }
        for res in per_file
    ],
}
identity.write_json(os.path.join(OUT_DIR, "dataset_validation_report.json"), report)
identity.write_json(os.path.join(OUT_DIR, "calendar_manifest.json"), calendar_manifest)
identity.write_json(
    os.path.join(OUT_DIR, "seal_report.json"),
    global_seal.to_dict(include_kept_list=True),
)
manifest = identity.build_run_manifest(
    notebook_id=NOTEBOOK_ID,
    stage="VALIDATION",
    fields={
        "dataset_schema_version": "ticks_l1_v1",
        "calendar_manifest_sha256": calendar_manifest["calendar_manifest_sha256"],
        "builder_id": "kaggle_notebook_01",
    },
    extra={"totals": totals, "verdict": verdict},
)
identity.write_json(os.path.join(OUT_DIR, "run_manifest_01.json"), manifest)

print("\n== RESUMEN ==")
print(json.dumps({"verdict": verdict, "totals": totals,
                  "gates_failed": {k: len(v) for k, v in all_failed.items()},
                  "seal": {k: global_seal.to_dict()[k] for k in (
                      "rows_in", "rows_kept", "rows_cut_holdout",
                      "rows_leaked_by_naive_utc_cut", "kept_trade_dates")}},
                 indent=2))
