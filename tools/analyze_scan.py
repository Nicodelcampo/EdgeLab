#!/usr/bin/env python3
"""Pase 2 de la release líquida: analiza la evidencia del escaneo (sin releer ticks).

Produce en <out>:
  file_inventory.parquet     una fila por archivo fuente: filas, hash, anomalías y contraste con el manifiesto del exportador
  tz_groups.csv              huso por grupo de fuentes (ajuste a sesión CME por offset entero de horas, global y por mes)
  contract_day.parquet       (contrato, grupo de fuente, fecha de trading): ticks, volumen, extremos, calidad de quotes
  summary.json               conteos para el informe
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.data.liquid_release.calendar_tz import (raw_hour_index, trade_date, violation_by_offset)  # noqa: E402

NS_S = 1_000_000_000


def load_inventory(scan: Path) -> pd.DataFrame:
    rows = []
    for f in glob.glob(str(scan / "parts" / "*.json")):
        if f.endswith(".error.json"):
            continue
        rows.append(json.load(open(f, encoding="utf-8")))
    inv = pd.DataFrame(rows)
    inv["group"] = inv["kind"] + "|" + inv["root"].str.split("\\").str[-1] + "|" + inv["contract"]
    return inv


def manifest_contrast(inv: pd.DataFrame) -> pd.DataFrame:
    """B: compara con manifest.jsonl del exportador (sha256, ticks, first_utc/last_utc)."""
    man = {}
    for root in inv.loc[inv.kind == "B", "root"].unique():
        for mf in Path(root).glob("*/manifest.jsonl"):
            for line in open(mf, encoding="utf-8"):
                if not line.strip():
                    continue
                r = json.loads(line)
                man[(root, r["contract"], r["day_nt_local"])] = r
    out = []
    for _, r in inv[inv.kind == "B"].iterrows():
        m = man.get((r["root"], r["contract"], r["day"]))
        if m is None:
            out.append(dict(source_id=r["id"], manifest="MISSING"))
            continue
        d = dict(source_id=r["id"], manifest="OK", man_status=m["status"], man_ticks=m["ticks"], man_sha=m["sha256"])
        d["ticks_match"] = (r.get("rows_ok") == m["ticks"]) if not r.get("truncated_at_cutoff") else None
        d["sha_match"] = (r.get("sha256") == m["sha256"]) if r.get("sha256") else None
        if m["first_utc"] and pd.notna(r.get("min_ts_raw_ns")):
            d["first_match"] = bool(pd.Timestamp(m["first_utc"]).tz_localize(None).value // 1000 == int(r["min_ts_raw_ns"]) // 1000)
        out.append(d)
    return pd.DataFrame(out)


def tz_table(bins: pd.DataFrame, inv: pd.DataFrame) -> pd.DataFrame:
    g = inv.set_index("id")["group"]
    bins = bins.assign(group=bins["source_id"].map(g))
    rows = []
    for grp, b in bins.groupby("group"):
        agg = b.groupby(["raw_date", "raw_hour"], as_index=False)["n"].sum()
        v = violation_by_offset(agg)
        best = min(v, key=v.get)
        d = dict(group=grp, rows=int(agg["n"].sum()), best_offset_h=best, viol_best=v[best], viol_utc=v[0], viol_art=v[-3])
        # estabilidad por trimestre: offset óptimo en cada tramo
        agg["q"] = pd.to_datetime(agg["raw_date"].astype(str)).dt.to_period("Q").astype(str)
        per = {}
        for q, bq in agg.groupby("q"):
            vq = violation_by_offset(bq)
            per[q] = min(vq, key=vq.get)
        d["best_by_quarter"] = json.dumps(per)
        d["offset_stable"] = len(set(per.values())) == 1
        rows.append(d)
    return pd.DataFrame(rows)


def contract_day(bins: pd.DataFrame, inv: pd.DataFrame, tz: pd.DataFrame) -> pd.DataFrame:
    meta = inv.set_index("id")[["group", "contract", "instrument", "kind"]]
    bins = bins.join(meta, on="source_id")
    off = tz.set_index("group")["best_offset_h"].to_dict()
    pieces = []
    for grp, b in bins.groupby("group"):
        o = off[grp]
        naive = raw_hour_index(b["raw_date"].to_numpy(), b["raw_hour"].to_numpy())
        b = b.assign(trade_date=trade_date(naive, o), utc_offset_h=o)
        pieces.append(b)
    allb = pd.concat(pieces, ignore_index=True)
    sums = ["n", "vol", "n_vol_le0", "off_last", "off_bid", "off_ask", "noquote", "crossed", "locked", "last_gt_ask", "last_lt_bid"]
    agg = allb.groupby(["group", "contract", "instrument", "kind", "trade_date", "utc_offset_h"], as_index=False).agg(
        **{k: (k, "sum") for k in sums}, first_ts=("first_ts", "min"), last_ts=("last_ts", "max"))
    return agg, allb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    scan, out = Path(a.scan), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    inv = load_inventory(scan)
    mc = manifest_contrast(inv)
    fi = inv.merge(mc, left_on="id", right_on="source_id", how="left")
    fi.drop(columns=["invalid_samples"], errors="ignore").to_parquet(out / "file_inventory.parquet", index=False)
    files = [f for f in glob.glob(str(scan / "parts" / "*.parquet"))]
    bins = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    bins = bins[bins["n"] > 0]
    tz = tz_table(bins, inv)
    tz.to_csv(out / "tz_groups.csv", index=False)
    cd, allb = contract_day(bins, inv, tz)
    cd.to_parquet(out / "contract_day.parquet", index=False)
    allb.drop(columns=["spread_hist"]).to_parquet(out / "bins_with_trade_date.parquet", index=False)
    summ = dict(sources=int(len(inv)), rows=int(inv["rows_ok"].fillna(0).sum()), groups=int(tz.shape[0]),
                tz_offsets=tz["best_offset_h"].value_counts().to_dict(),
                tz_unstable=tz.loc[~tz["offset_stable"], "group"].tolist(),
                b_manifest=mc["manifest"].value_counts().to_dict() if len(mc) else {},
                b_sha_match=mc["sha_match"].value_counts(dropna=False).to_dict() if "sha_match" in mc else {},
                b_ticks_match=mc["ticks_match"].value_counts(dropna=False).to_dict() if "ticks_match" in mc else {})
    (out / "summary.json").write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
