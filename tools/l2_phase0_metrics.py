#!/usr/bin/env python3
r"""Fase 0 L2 sobre sesiones PRE-HOLDOUT: QA por sesion, lista de dias defectuosos, tabla de costos y reloj.

    .venv\Scripts\python tools\l2_phase0_metrics.py --base E:\DatosNT8\gc_aug26_canonical_parquets ^
        --instrument GC --contract "GC 08-26" --out artifacts\l2_phase0

Rechaza cualquier sesion >= inicio del holdout (`edgelab.research.holdout_guard.HOLDOUT_START_ISO`): los costos
no se calibran con el holdout. Escribe `<out>/<inst>_<contract>/{qa.jsonl,blocks.parquet}` con procedencia.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from edgelab.research.holdout_guard import L2_HOLDOUT_START_ISO as HOLDOUT_START_ISO  # enmienda L2 2026-09-24  # noqa: E402
from edgelab.research.l2_phase0 import block_table, defect_reasons, process_session  # noqa: E402

HOLDOUT_YMD = int(HOLDOUT_START_ISO[:10].replace("-", ""))
COLS2 = ["side", "operation", "level", "price_tick", "size", "ts_us", "source_row"]
COLS1 = ["side", "price_tick", "size", "ts_us", "source_row"]


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--instrument", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--out", type=Path, default=REPO / "artifacts" / "l2_phase0")
    a = ap.parse_args(argv)
    out = a.out / f"{a.instrument}_{a.contract.replace(' ', '_')}"
    out.mkdir(parents=True, exist_ok=True)
    prov = dict(code_commit=_git("rev-parse", "HEAD"), tree_dirty=bool(_git("status", "--porcelain")),
                base=str(a.base), holdout_start=HOLDOUT_START_ISO)
    sessions = sorted(p.stem for p in (a.base / "l2_depth").glob("*.parquet"))
    rows, qa_lines = [], []
    for s in sessions:
        if int(s) >= HOLDOUT_YMD:
            qa_lines.append(dict(session=s, skipped="HOLDOUT"))
            continue
        t0 = time.time()
        l2 = pq.read_table(a.base / "l2_depth" / f"{s}.parquet", columns=COLS2).to_pandas()
        l1 = pq.read_table(a.base / "l1_quotes" / f"{s}.parquet", columns=COLS1).to_pandas()
        res = process_session(l2, l1)
        reasons = defect_reasons(res.qa)
        qa_lines.append(dict(session=s, **res.qa, defect_reasons=reasons, usable=not reasons,
                             seconds=round(time.time() - t0, 1)))
        if not reasons:
            rows += block_table(res, instrument=a.instrument, contract=a.contract, session=s)
        print(json.dumps(dict(session=s, usable=not reasons, reasons=reasons, s=round(time.time() - t0, 1))), flush=True)
    with open(out / "qa.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(dict(provenance=prov)) + "\n")
        for q in qa_lines:
            f.write(json.dumps(q) + "\n")
    if rows:
        pd.DataFrame(rows).to_parquet(out / "blocks.parquet", index=False)
    print(json.dumps(dict(out=str(out), sessions=len(sessions), usable=sum(1 for q in qa_lines if q.get("usable")),
                          provenance=prov)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
