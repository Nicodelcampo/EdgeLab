#!/usr/bin/env python3
"""Verifica una release ya escrita, de forma independiente del escritor.

Chequeos por activo (streaming por row groups):
  - manifiesto, tamaño y SHA-256 (lector seguro);
  - filas totales = manifiesto; filas por fecha de trading = suma de ticks de los bins elegidos del censo (exacto);
  - un único contrato por fecha de trading y igual al de la decisión; regime_id sin retrocesos;
  - ts_utc_ns no decreciente; sin fechas de holdout ni ticks >= 2026-09-30T22:00Z;
  - precios > 0 en la grilla (price_ticks entero por construcción), bid <= ask cuando hay quote;
  - cada row group abarca una sola fecha de trading (estadísticas min = max).
Uso: python tools/verify_release.py --release D:/.../release --census D:/.../census [--only ES]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.data.liquid_release.release_reader import load_manifest  # noqa: E402

CUTOFF_NS = 1_790_805_600_000_000_000


def expected_rows(inst, dec, chosen, ann):
    sel = dec[(dec["instrument"] == inst) & (dec["status"] == "SELECTED")][["trade_date", "contract"]]
    ch = chosen[chosen["instrument"] == inst].set_index(["contract", "trade_date"])["group"]
    sel = sel.assign(group=[ch[(c, d)] for c, d in zip(sel["contract"], sel["trade_date"])])
    a = ann[(ann["instrument"] == inst) & (~ann["dup_copy"])]
    m = a.merge(sel, on=["group", "trade_date"])
    return m.groupby("trade_date")["n"].sum(), sel.set_index("trade_date")["contract"]


def verify_asset(inst, info, root, dec, chosen, ann):
    res = dict(instrument=inst, ok=True, problems=[])
    exp_n, exp_c = expected_rows(inst, dec, chosen, ann)
    pf = pq.ParquetFile(Path(root) / info["file"])
    names = pf.schema_arrow.names
    td_i = names.index("trade_date")
    per_td, contract_by_td, last_ts, last_regime, nonmono = {}, {}, -1, 0, 0
    bad = dict(price=0, quote=0, holdout=0, regime_back=0)
    for g in range(pf.metadata.num_row_groups):
        st = pf.metadata.row_group(g).column(td_i).statistics
        if st is None or st.min != st.max:
            res["problems"].append(f"row group {g} sin estadísticas o con varias fechas")
        t = pf.read_row_group(g, columns=["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "contract", "regime_id", "trade_date"])
        ts = t["ts_utc_ns"].to_numpy()
        nonmono += int((np.diff(ts) < 0).sum()) + int(len(ts) and ts[0] < last_ts)
        last_ts = int(ts[-1]) if len(ts) else last_ts
        bad["holdout"] += int((ts >= CUTOFF_NS).sum()) + int((t["trade_date"].to_numpy() >= 20261001).sum())
        bad["price"] += int((t["price_ticks"].to_numpy() <= 0).sum())
        b, a_ = t["bid_ticks"].to_numpy(), t["ask_ticks"].to_numpy()
        bad["quote"] += int(((b > 0) & (a_ > 0) & (a_ < b)).sum())
        td = int(t["trade_date"][0].as_py())
        per_td[td] = per_td.get(td, 0) + len(ts)
        contract_by_td.setdefault(td, set()).update(t["contract"].to_pylist())
        rg = t["regime_id"].to_numpy()
        if len(rg):
            bad["regime_back"] += int(rg.min() < last_regime)
            last_regime = int(rg.max())
    tot = sum(per_td.values())
    if tot != info["rows"]:
        res["problems"].append(f"filas {tot} != manifiesto {info['rows']}")
    diffs = [(d, per_td.get(d, 0), int(exp_n.get(d, 0))) for d in sorted(set(per_td) | set(exp_n.index)) if per_td.get(d, 0) != int(exp_n.get(d, 0))]
    if diffs:
        res["problems"].append(f"{len(diffs)} fechas con filas != censo, p. ej. {diffs[:3]}")
    multi = [d for d, c in contract_by_td.items() if len(c) != 1]
    wrong = [d for d, c in contract_by_td.items() if len(c) == 1 and next(iter(c)) != exp_c.get(d)]
    if multi:
        res["problems"].append(f"{len(multi)} fechas con más de un contrato")
    if wrong:
        res["problems"].append(f"{len(wrong)} fechas con contrato distinto de la decisión")
    for k, v in bad.items():
        if v:
            res["problems"].append(f"{k}: {v}")
    if nonmono:
        res["problems"].append(f"ts no decreciente: {nonmono} retrocesos")
    res.update(rows=tot, sessions=len(per_td), row_groups=pf.metadata.num_row_groups, ok=not res["problems"])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    root = Path(a.release)
    files = load_manifest(root, verify_hash=True)
    man = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
    dec = pd.read_parquet(root / "metadata" / "selection_decisions.parquet")
    chosen = pd.read_parquet(Path(a.census) / "chosen_sources.parquet")
    ann = pd.read_parquet(Path(a.census) / "annotated_bins.parquet", columns=["group", "trade_date", "dup_copy", "instrument", "n"])
    out = []
    for inst, info in man["assets"].items():
        if a.only and inst not in a.only:
            continue
        r = verify_asset(inst, info, root, dec, chosen, ann)
        out.append(r)
        print(f"{inst}: {'OK' if r['ok'] else 'FALLA'} filas={r['rows']:,} sesiones={r['sessions']} row_groups={r['row_groups']}", flush=True)
        for p in r["problems"]:
            print("   -", p)
    (root / "metadata" / "verification.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    sys.exit(0 if all(r["ok"] for r in out) else 1)


if __name__ == "__main__":
    main()
