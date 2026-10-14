#!/usr/bin/env python3
"""Audita los parquets publicados en Kaggle contra los originales locales, sin bajarlos.

Usa los escaneos por sesión del catálogo (`scan__*.json`: rows, trades, volumen y trades por fecha de trading) y el
censo `contract_day.parquet` de los originales. Por archivo de Kaggle y por sesión clasifica:
  EQUAL (mismos trades), CLOSE (<1 %), DIFF (>=1 %), KAGGLE_ONLY (sin fuente local), SOURCE_ONLY (la fuente tiene la
  sesión y Kaggle no, dentro del rango del archivo).
Un hash/trade count igual no prueba procedencia (D12/D22); sí prueba que no hay divergencia de contenido en lo medido.
"""
from __future__ import annotations

import argparse
import glob
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd


def kaggle_days(catalog: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(catalog / "scan__*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if not d.get("recognized") or "days" not in d:
            continue
        for c in d.get("contracts_in_file", []):
            for day in d["days"]:
                td = date.fromordinal(int(day["td"]))
                rows.append(dict(dataset=d["dataset"], file=d["file"], contract=c, trade_date=td.year * 10000 + td.month * 100 + td.day,
                                 k_trades=int(day["trades"]), k_volume=float(day["volume"]), k_minutes=int(day["minutes"]),
                                 file_rows=int(d["rows"]), file_trades=int(d["trades"]), n_contracts=len(d["contracts_in_file"])))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--analysis", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    k = kaggle_days(Path(a.catalog))
    cd = pd.read_parquet(Path(a.analysis) / "contract_day.parquet")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # mejor fuente local por (contrato, fecha): la de más ticks, y se conservan todas para el contraste
    src = cd.pivot_table(index=["contract", "trade_date"], columns="group", values="n", aggfunc="sum")
    best = cd.sort_values("n", ascending=False).drop_duplicates(["contract", "trade_date"])[["contract", "trade_date", "group", "n", "vol"]]
    best = best.rename(columns={"group": "best_group", "n": "src_n", "vol": "src_vol"})
    m = k.merge(best, on=["contract", "trade_date"], how="outer", indicator=True)
    ext = k.groupby(["dataset", "file", "contract"]).trade_date.agg(["min", "max"]).reset_index()
    m = m.merge(ext, left_on=["dataset", "file", "contract"], right_on=["dataset", "file", "contract"], how="left")
    rel = (m["k_trades"] - m["src_n"]).abs() / m[["k_trades", "src_n"]].max(axis=1).replace(0, np.nan)
    m["cls"] = np.select([m["_merge"].eq("left_only"), m["_merge"].eq("right_only"), m["k_trades"].eq(m["src_n"]), rel < 0.01],
                         ["KAGGLE_ONLY", "SOURCE_ONLY", "EQUAL", "CLOSE"], "DIFF")
    # SOURCE_ONLY sólo cuenta dentro del rango de fechas del archivo de Kaggle que cubre ese contrato
    so = m[m["cls"] == "SOURCE_ONLY"].drop(columns=["dataset", "file", "min", "max"])
    so = so.merge(ext, on="contract")
    so = so[(so["trade_date"] >= so["min"]) & (so["trade_date"] <= so["max"])]
    kk = m[m["cls"] != "SOURCE_ONLY"]
    res = pd.concat([kk, so], ignore_index=True)
    res.to_parquet(out / "kaggle_vs_sources_days.parquet", index=False)
    summ = res.groupby(["dataset", "file", "contract", "cls"]).size().unstack(fill_value=0).reset_index()
    summ.to_csv(out / "kaggle_vs_sources_by_file.csv", index=False)
    tot = res["cls"].value_counts().to_dict()
    print("sesiones clasificadas:", tot)
    bad = summ[(summ.get("DIFF", 0) > 0) | (summ.get("KAGGLE_ONLY", 0) > 0) | (summ.get("SOURCE_ONLY", 0) > 0)]
    print(f"archivos con diferencias: {len(bad)} de {len(summ)}")
    hold = res[res["trade_date"] >= 20261001]
    print("sesiones de holdout (>=2026-10-01) presentes en Kaggle:", int(hold["k_trades"].notna().sum()))


if __name__ == "__main__":
    main()
