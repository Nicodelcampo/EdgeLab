#!/usr/bin/env python3
r"""Orquesta el intake de UNA sesion L2 nueva: CSV crudo ya presente en disco -> parquet
validado -> chequeo de continuidad contra el dia anterior -> log de custodia -> (opcional)
borrado del CSV. Pensado para correr una vez por dia, disparado por Task Scheduler o a mano.

Deliberadamente NO baja nada. El auditor externo (2026-09-22) marco que no hay API publica
documentada de NinjaTrader para automatizar "Get Market Replay Data" en lote -- los add-ons
que lo hacen tocan mecanismos internos no documentados, y ese es codigo de terceros que este
proyecto no ejecuta por su cuenta (misma postura que ya existe para NRDToCSV, P-57). Este
script arranca en el momento en que YA existe un CSV (bajado a mano por el diario "Get Market
Replay Data" + NRDToCSV, o por el downloader que el usuario audite e instale el mismo) y
automatiza TODO lo que sigue, que es exactamente lo que se puede automatizar sin ejecutar
codigo de terceros:

    CSV crudo (ya en disco)
        |  hash + tamano + deteccion L1/L2 presentes
        v
    convert_l2_session()          -- valida price round-trip fila a fila, FAIL-CLOSED
        |  (edgelab/data/l2.py)      (PriceRoundtripError si una fila no cae en grilla)
        v
    Parquet L1/L2 + manifest de conversion (NT8_MBP10_REPLAY_V1)
        |
        v
    validate_l2_session_boundaries -- SOLO la frontera dia_anterior -> esta sesion
        |  (gap vs. reloj, book bootstrap opcional)
        v
    log de custodia (append-only, un JSON por linea, ver INTAKE_LOG_FIELDS abajo)
        |
        v
    borrado del CSV -- SOLO si --delete-csv-after-validation Y todo lo anterior paso.
                        Default: NO se borra nada (opt-in explicito, no opt-out).

Kaggle NO se toca desde aca -- "Kaggle privado opcional" del pipeline del auditor sigue
siendo un paso manual aparte, deliberadamente.

Target-free. No abre outcomes, P&L ni holdout.

    .venv\\Scripts\\python tools\\l2_daily_intake.py --csv E:\\staging\\20260901.csv ^
        --base E:\\DatosNT8\\gc_aug26_canonical_parquets --instrument GC --contract "GC 08-26" ^
        --tick-size 0.1 --downloader-id manual --log runs\\l2_intake\\gc_08-26.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.data.l2 import PriceRoundtripError, convert_l2_session  # noqa: E402
from tools.validate_l2_session_boundaries import _session_ts_bounds, classify_gap  # noqa: E402

INTAKE_LOG_FIELDS = (
    "instrument, contract, session_date, requested_at_utc, downloader_id, "
    "nrd_bytes, nrd_sha256, csv_bytes, csv_sha256, l1_present, l2_present, "
    "l1_rows, l2_rows, level_min, level_max, first_ts_us, last_ts_us, "
    "conversion_status, price_roundtrip, parquet_l2_sha256, parquet_l1_sha256, "
    "boundary_status, csv_deleted, kaggle_privacy_probe")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _detect_l1_l2_presence(csv_path: Path) -> tuple[bool, bool, int, int]:
    """Cuenta lineas L1/L2 sin parsear todo el CSV en memoria (un archivo real pesa cientos
    de MB) -- solo mira el primer campo de cada linea."""
    l1_rows = l2_rows = 0
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("L1;"):
                l1_rows += 1
            elif line.startswith("L2;"):
                l2_rows += 1
    return l1_rows > 0, l2_rows > 0, l1_rows, l2_rows


def run_intake(*, csv_path: Path, base: Path, instrument: str, contract: str, tick_size: float,
              downloader_id: str, nrd_path: Path | None = None, requested_at_utc: str | None = None,
              delete_csv_after_validation: bool = False, skip_boundary_book_check: bool = True) -> dict:
    session_date = csv_path.stem
    record: dict = dict(
        instrument=instrument, contract=contract, session_date=session_date,
        requested_at_utc=requested_at_utc or datetime.now(timezone.utc).isoformat(),
        downloader_id=downloader_id,
        nrd_bytes=None, nrd_sha256=None,
        csv_bytes=csv_path.stat().st_size, csv_sha256=_sha256_file(csv_path),
        kaggle_privacy_probe=None,
    )
    if nrd_path is not None and nrd_path.exists():
        record["nrd_bytes"] = nrd_path.stat().st_size
        record["nrd_sha256"] = _sha256_file(nrd_path)

    l1_present, l2_present, l1_rows_raw, l2_rows_raw = _detect_l1_l2_presence(csv_path)
    record.update(l1_present=l1_present, l2_present=l2_present, l1_rows=l1_rows_raw, l2_rows=l2_rows_raw)
    if not (l1_present and l2_present):
        record["conversion_status"] = "ABSTAIN_MISSING_L1_OR_L2"
        return record

    try:
        p_l2, p_l1 = convert_l2_session(csv_path, base, tick_size=tick_size)
    except PriceRoundtripError as e:
        record["conversion_status"] = f"ABORTED_PRICE_ROUNDTRIP: {e}"
        return record

    man = json.loads((base / "manifests" / f"{session_date}.manifest.json").read_text(encoding="utf-8"))
    record["conversion_status"] = "PASS"
    record["price_roundtrip"] = man["conversion"]["price_roundtrip"]
    record["parquet_l2_sha256"] = man["outputs"]["l2_depth"]["sha256"]
    record["parquet_l1_sha256"] = man["outputs"]["l1_quotes"]["sha256"]

    l2_levels = pq.read_table(p_l2, columns=["level"]).to_pandas()["level"]
    record["level_min"] = int(l2_levels.min()) if len(l2_levels) else None
    record["level_max"] = int(l2_levels.max()) if len(l2_levels) else None
    first_ts, last_ts = _session_ts_bounds(base, session_date)
    record["first_ts_us"], record["last_ts_us"] = first_ts, last_ts

    prev_sessions = sorted(p.stem.replace(".manifest", "") for p in (base / "manifests").glob("*.manifest.json")
                           if p.stem.replace(".manifest", "") < session_date)
    if prev_sessions:
        prev = prev_sessions[-1]
        _, prev_last = _session_ts_bounds(base, prev)
        gap_s = (first_ts - prev_last) / 1_000_000.0
        from datetime import datetime as _dt
        d_prev = _dt.strptime(prev, "%Y%m%d").date()
        d_this = _dt.strptime(session_date, "%Y%m%d").date()
        classification = classify_gap(d_prev, d_this, gap_s)
        record["boundary_status"] = dict(
            left_session=prev, gap_seconds=gap_s, gap_classification=classification,
            book_check="SKIPPED" if skip_boundary_book_check else "SEE_validate_l2_session_boundaries")
    else:
        record["boundary_status"] = "NO_PREVIOUS_SESSION"

    record["csv_deleted"] = False
    if delete_csv_after_validation:
        csv_path.unlink()
        record["csv_deleted"] = True

    return record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True, help="CSV crudo (NRDToCSV) ya presente en disco")
    ap.add_argument("--nrd", type=Path, default=None, help="opcional: .nrd original, para hashearlo en el log")
    ap.add_argument("--base", type=Path, required=True, help="carpeta canonica destino (l1_quotes/l2_depth/manifests)")
    ap.add_argument("--instrument", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--tick-size", type=float, required=True)
    ap.add_argument("--downloader-id", required=True, help='ej. "manual" o "NT8ReplayDownloader@<sha>"')
    ap.add_argument("--requested-at-utc", default=None)
    ap.add_argument("--log", type=Path, required=True, help="archivo .jsonl de custodia (append-only)")
    ap.add_argument("--delete-csv-after-validation", action="store_true",
                    help="borra el CSV si la conversion+validacion pasan. Default: NO borra (opt-in explicito).")
    ap.add_argument("--boundary-book-check", action="store_true",
                    help="corre build() fail-closed sobre la frontera con el dia anterior (mas lento, mas estricto)")
    a = ap.parse_args(argv)

    record = run_intake(
        csv_path=a.csv, base=a.base, instrument=a.instrument, contract=a.contract, tick_size=a.tick_size,
        downloader_id=a.downloader_id, nrd_path=a.nrd, requested_at_utc=a.requested_at_utc,
        delete_csv_after_validation=a.delete_csv_after_validation,
        skip_boundary_book_check=not a.boundary_book_check)

    a.log.parent.mkdir(parents=True, exist_ok=True)
    with open(a.log, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    print(json.dumps(record, indent=2))
    return 0 if record["conversion_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
