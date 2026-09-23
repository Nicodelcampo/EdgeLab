#!/usr/bin/env python3
r"""Barrido de intake L2: procesa todos los CSV nuevos de una carpeta y valida la continuidad.

Los dos pasos que requieren la GUI de NinjaTrader (bajar `.nrd` con el EdgeLab Replay
Downloader, convertir con NRDToCSV) quedan manuales -- ninguno expone una API que Task
Scheduler pueda disparar. Este script cubre TODO lo que viene después, en un comando:

  1. Busca en `--csv-dir` los `yyyymmdd.csv` cuya sesión todavía no tiene manifest en `--base`.
  2. Corre `tools/l2_daily_intake.run_intake` sobre cada uno, en orden de fecha (conversión
     validada fail-closed + custodia append-only en `--log`).
  3. Corre `tools/validate_l2_session_boundaries.validate_boundaries` sobre todo `--base`.

Con `--no-continuity` solo convierte (uso por día desde el Replay Downloader; la
continuidad se valida en una corrida final sin el flag). Idempotente: una sesión con manifest ya existente se saltea. No borra CSV salvo
`--delete-csv-after-validation`. Sale con código 1 si alguna conversión no pasó o si hay
alguna frontera en FAIL.

    .venv\\Scripts\\python tools\\l2_intake_sweep.py --csv-dir "E:\gcl2\GC DEC26" ^
        --base E:\l2_parquet\GC_12-26 --instrument GC --contract "GC 12-26" --tick-size 0.1 ^
        --downloader-id EDGE_NT8RD_HARDENED_V1@fd743ad --log runs\l2_intake\gc_12-26.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.l2_daily_intake import run_intake  # noqa: E402
from tools.validate_l2_session_boundaries import validate_boundaries  # noqa: E402

_SESSION_RX = re.compile(r"^\d{8}$")


def pending_sessions(csv_dir: Path, base: Path) -> list[Path]:
    done = {p.name.replace(".manifest.json", "") for p in (base / "manifests").glob("*.manifest.json")}
    return sorted(p for p in csv_dir.glob("*.csv") if _SESSION_RX.match(p.stem) and p.stem not in done)


def sweep(*, csv_dir: Path, base: Path, instrument: str, contract: str, tick_size: float,
          downloader_id: str, log: Path, out: Path, delete_csv_after_validation: bool = False,
          continuity: bool = True) -> dict:
    records = []
    log.parent.mkdir(parents=True, exist_ok=True)
    for csv in pending_sessions(csv_dir, base):
        rec = run_intake(csv_path=csv, base=base, instrument=instrument, contract=contract,
                         tick_size=tick_size, downloader_id=downloader_id,
                         delete_csv_after_validation=delete_csv_after_validation)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        records.append({"session": rec["session_date"], "conversion_status": rec["conversion_status"]})

    n_manifests = len(list((base / "manifests").glob("*.manifest.json"))) if (base / "manifests").exists() else 0
    continuity = (validate_boundaries(base, out, tick_size, skip_book_check=True)
                  if continuity and n_manifests >= 2 else {"pass_count": 0, "review_count": 0, "fail_count": 0,
                                            "boundaries_checked": 0})
    return dict(ingested=records,
                conversion_failures=sum(1 for r in records if r["conversion_status"] != "PASS"),
                boundaries_checked=continuity["boundaries_checked"], pass_count=continuity["pass_count"],
                review_count=continuity["review_count"], fail_count=continuity["fail_count"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", type=Path, required=True)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--instrument", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--tick-size", type=float, required=True)
    ap.add_argument("--downloader-id", required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("runs/l2_continuity"))
    ap.add_argument("--delete-csv-after-validation", action="store_true")
    ap.add_argument("--no-continuity", action="store_true",
                    help="solo convertir; la continuidad se valida en una corrida final")
    a = ap.parse_args(argv)
    summary = sweep(csv_dir=a.csv_dir, base=a.base, instrument=a.instrument, contract=a.contract,
                    tick_size=a.tick_size, downloader_id=a.downloader_id, log=a.log, out=a.out,
                    delete_csv_after_validation=a.delete_csv_after_validation,
                    continuity=not a.no_continuity)
    print(json.dumps(summary, indent=2))
    return 1 if summary["conversion_failures"] or summary["fail_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
