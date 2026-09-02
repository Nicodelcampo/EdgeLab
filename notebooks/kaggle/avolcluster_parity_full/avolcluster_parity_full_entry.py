#!/usr/bin/env python3
"""Cruce COMPLETO celda-por-celda NT8 vs Python para aVolClusterPOI (NQ 06-26).

Extiende a TODOS los bloques el cruce que
`AVOLCLUSTERPOI_NT8_DIAG_CONFIRMED_2026-09-01.md` hizo sobre 3 casos de
muestra. Pregunta que responde: **el mecanismo conocido (el filtro
`Low[0]/High[0]` del .cs descarta ticks de borde sin reasignarlos) explica
TODAS las discrepancias, o hay una segunda causa?**

Si las explica todas, el fix del .cs es suficiente. Si no, arreglar el .cs no
alcanzaria y hay que buscar otra cosa. Esa es la diferencia entre saber que
arreglar y adivinar.

Insumo NT8: data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv
(22.508 bloques, `cells` crudas tick:vol). Insumo Python: se reconstruye el
trace real sobre la misma ventana.

Target-free: sólo compara celdas, medianas, umbrales y geometría. No toca
outcomes, retornos, P&L ni holdout. NO modifica el .cs ni el kernel Python.
"""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "PIN_PENDIENTE"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
DIAG_CSV = "data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv"
ART_TO_UTC_NS = 3 * 3600 * 10**9   # chart(ART) -> UTC, confirmado diff=0.0s
TICKS_PER_BAR = 120
TOL_NS = 2 * 10**9
OUT = Path("/kaggle/working/avolcluster_parity_full")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def checkout(commit: str) -> str:
    if len(commit) != 40:
        raise SystemExit("EXPECTED_COMMIT debe ser SHA de 40 chars")
    if not (REPO_DIR / ".git").exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        REPO_URL, str(REPO_DIR)], check=True)
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                        "edgelab/**", "data/nt8_oracles/**"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "parity_full", commit], cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    if actual != commit:
        raise SystemExit("code provenance gate failed")
    sys.path.insert(0, str(REPO_DIR))
    return actual


def parse_cells(text: str) -> dict:
    out = {}
    if not text:
        return out
    for part in text.split("|"):
        if not part:
            continue
        t, _, v = part.partition(":")
        try:
            out[int(t)] = float(v)
        except ValueError:
            continue
    return out


def parse_iso_ns(s: str) -> int:
    import datetime as dt
    s = s.strip().replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return int(dt.datetime.strptime(s, fmt).replace(
                tzinfo=dt.timezone.utc).timestamp() * 10**9)
        except ValueError:
            continue
    raise ValueError(f"bar_close_time no parseable: {s!r}")


def load_nt8(path: Path):
    rows = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = [ln for ln in f if not ln.startswith("# meta")]
    for r in csv.DictReader(lines):
        try:
            ts = parse_iso_ns(r["bar_close_time"]) + ART_TO_UTC_NS
        except ValueError:
            continue
        rows.append({
            "ts": ts, "decision": (r.get("decision") or "").strip(),
            "cells": parse_cells(r.get("cells") or ""),
            "median": float(r["median"]) if r.get("median") else None,
            "hot_threshold": float(r["hot_threshold"]) if r.get("hot_threshold") else None,
            "threshold": float(r["threshold"]) if r.get("threshold") else None,
            "lower": int(r["selected_lower_tick"]) if (r.get("selected_lower_tick") or "").strip() else None,
            "upper": int(r["selected_upper_tick"]) if (r.get("selected_upper_tick") or "").strip() else None,
        })
    return rows


def main() -> int:
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, flush=True)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries
    from edgelab.bridge.indicators import avolclusterpoi

    csv_path = REPO_DIR / DIAG_CSV
    nt8 = load_nt8(csv_path)
    print(f"NT8 bloques={len(nt8):,} sha={sha256(csv_path)[:16]}...", flush=True)
    lo_ns, hi_ns = min(r["ts"] for r in nt8), max(r["ts"] for r in nt8)

    hits = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))
    full = ticks_mod.load_canonical_parquet(str(hits[0]))
    # ventana del oraculo, con margen de una sesion para el warmup de barras
    m = (full.ts_ns >= lo_ns - 86400 * 10**9) & (full.ts_ns <= hi_ns + 86400 * 10**9)
    idx = np.flatnonzero(m)
    t = TickSeries(ts_ns=full.ts_ns[idx], price_ticks=full.price_ticks[idx],
                   volume=full.volume[idx],
                   bid_ticks=full.bid_ticks[idx] if full.bid_ticks is not None else None,
                   ask_ticks=full.ask_ticks[idx] if full.ask_ticks is not None else None,
                   sequence=full.sequence[idx], tick_size=full.tick_size,
                   instrument=full.instrument, contract=full.contract, source=full.source)
    bars = bars_mod.build_tick_bars(t, TICKS_PER_BAR)
    fp = bars_mod.build_footprints(t, bars)
    py = avolclusterpoi.run(t, bars, fp, debug_trace=True)["block_trace"]
    print(f"Python bloques={len(py):,}", flush=True)

    by_ts = {}
    for b in py:
        by_ts.setdefault(int(b["block_end_ns"]), b)
    py_ts = sorted(by_ts)

    matched, unmatched = [], 0
    for r in nt8:
        pos = np.searchsorted(py_ts, r["ts"])
        best, bd = None, None
        for k in (pos - 1, pos, pos + 1):
            if 0 <= k < len(py_ts):
                d = abs(py_ts[k] - r["ts"])
                if bd is None or d < bd:
                    bd, best = d, py_ts[k]
        if best is None or bd > TOL_NS:
            unmatched += 1
            continue
        matched.append((r, by_ts[best], bd))
    print(f"emparejados={len(matched):,}  sin par={unmatched:,}", flush=True)

    recs = []
    for r, b, d in matched:
        pc, nc = {int(k): float(v) for k, v in (b.get("cells") or {}).items()}, r["cells"]
        only_py = sorted(set(pc) - set(nc))
        only_nt8 = sorted(set(nc) - set(pc))
        shared_diff = [k for k in (set(pc) & set(nc)) if abs(pc[k] - nc[k]) > 1e-9]
        pdec, ndec = b.get("decision"), r["decision"]
        pg = (b.get("selected_cluster") or {})
        geom_py = (int(pg["lower_tick"]), int(pg["upper_tick"])) if pg else None
        geom_nt8 = (r["lower"], r["upper"]) if r["lower"] is not None else None
        recs.append({
            "ts": r["ts"], "match_ns": d,
            "n_only_py": len(only_py), "vol_only_py": round(sum(pc[k] for k in only_py), 6),
            "n_only_nt8": len(only_nt8), "n_shared_diff": len(shared_diff),
            "median_py": b.get("median"), "median_nt8": r["median"],
            "hot_py": b.get("hot_threshold"), "hot_nt8": r["hot_threshold"],
            "decision_py": pdec, "decision_nt8": ndec,
            "decision_match": pdec == ndec,
            "geom_py": geom_py, "geom_nt8": geom_nt8,
            "geom_match": (geom_py == geom_nt8) if (geom_py and geom_nt8) else None,
        })

    def frac(pred, pool):
        pool = list(pool)
        return {"n": len(pool), "con_ticks_ausentes_en_nt8": sum(1 for x in pool if pred(x)),
                "solo_ruido_de_valor": sum(1 for x in pool if not pred(x) and x["n_shared_diff"] > 0),
                "sin_diferencia_de_celdas": sum(1 for x in pool if not pred(x) and x["n_shared_diff"] == 0)}

    has_missing = lambda x: x["n_only_py"] > 0
    dec_mismatch = [x for x in recs if not x["decision_match"]]
    geom_mismatch = [x for x in recs if x["geom_match"] is False]
    both_create = [x for x in recs if x["decision_py"] == "CREATE" and x["decision_nt8"] == "CREATE"]
    cells_identical = sum(1 for x in recs
                          if x["n_only_py"] == 0 and x["n_only_nt8"] == 0 and x["n_shared_diff"] == 0)

    report = {
        "schema": "avolclusterpoi_parity_full_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "question": "el filtro Low/High del .cs explica TODAS las discrepancias o hay una segunda causa",
        "code_commit": commit, "nt8_csv_sha256": sha256(csv_path),
        "n_nt8_blocks": len(nt8), "n_py_blocks": len(py),
        "n_matched": len(matched), "n_unmatched_nt8": unmatched,
        "cells_identical_blocks": cells_identical,
        "blocks_with_ticks_missing_in_nt8": sum(1 for x in recs if x["n_only_py"] > 0),
        "blocks_with_ticks_missing_in_py": sum(1 for x in recs if x["n_only_nt8"] > 0),
        "blocks_with_value_noise_only": sum(1 for x in recs
                                            if x["n_only_py"] == 0 and x["n_only_nt8"] == 0
                                            and x["n_shared_diff"] > 0),
        "decision_mismatch": frac(has_missing, dec_mismatch),
        "geometry_mismatch": frac(has_missing, geom_mismatch),
        "both_create_n": len(both_create),
        "verdict_note": ("si 'sin_diferencia_de_celdas' es 0 en ambos bloques de mismatch, "
                         "toda discrepancia tiene una diferencia de celdas detras; si ademas "
                         "'solo_ruido_de_valor' es chico, domina el mecanismo del filtro Low/High"),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "parity_full_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    worst = sorted(recs, key=lambda x: -x["n_only_py"])[:40]
    (OUT / "parity_worst_cases_v1.json").write_text(
        json.dumps(worst, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "sha256_manifest.json").write_text(json.dumps(
        {p.name: sha256(p) for p in sorted(OUT.iterdir()) if p.is_file()}, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
