#!/usr/bin/env python3
"""Validacion profunda de muestras de ticks NUEVOS (fuera de los datasets Kaggle de Nico):
1. Exness Raw_Spread (USTEC_Raw_Spread & USOIL_Raw_Spread 2024-06) -> densidad, spread real, formato EdgeLab.
2. Hugging Face syncster-data/historical-market-data (SI_tick & NQ_tick pre-2026-10-01) -> esquema exacto.
3. Binance Futures BTCUSDT aggTrades (2024-06-12) -> densidad, esquema con lado agresor real.

Uso: python tools/probe_new_ticks_deep.py
"""
from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "docs/research/auditoria_cartera_20261126"
OUT.mkdir(parents=True, exist_ok=True)


def probe_exness_sample(sym: str, ym_path: str = "2024/06/Exness_{sym}_2024_06.zip") -> dict:
    url = "https://ticks.ex2archive.com/ticks/{sym}/" + ym_path
    url = url.format(sym=sym)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
        raw = r.read()
    zf = zipfile.ZipFile(io.BytesIO(raw))
    csv_name = zf.namelist()[0]
    df = pd.read_csv(zf.open(csv_name))
    cols = list(df.columns)
    # Typical Exness columns: "Exness","Symbol","Timestamp","Bid","Ask"
    bid = pd.to_numeric(df["Bid"], errors="coerce")
    ask = pd.to_numeric(df["Ask"], errors="coerce")
    sp = (ask - bid).dropna()
    ts = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    days = ts.dt.date.nunique()
    return {
        "source": f"Exness {sym}",
        "url": url,
        "zip_mb": round(len(raw) / 1e6, 2),
        "columns": cols,
        "total_ticks_month": int(len(df)),
        "trading_days": int(days),
        "ticks_per_day": round(len(df) / max(days, 1), 0),
        "spread_median_pts": round(float(sp.median()), 4),
        "spread_mean_pts": round(float(sp.mean()), 4),
        "spread_p90_pts": round(float(np.percentile(sp, 90)), 4),
        "ts_min": str(ts.min()),
        "ts_max": str(ts.max()),
    }


def probe_hf_syncster(root: str = "SI") -> dict:
    api = f"https://huggingface.co/api/datasets/syncster-data/historical-market-data/tree/main/data/futures/tick/{root}"
    with urllib.request.urlopen(urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as r:
        items = json.loads(r.read().decode())
    # Pick a file strictly < 2026-10-01
    cands = [x for x in items if x["path"].endswith(".parquet") and "202610" not in x["path"]]
    f = cands[0]
    dl = f"https://huggingface.co/datasets/syncster-data/historical-market-data/resolve/main/{f['path']}"
    with urllib.request.urlopen(urllib.request.Request(dl, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
        buf = r.read()
    df = pd.read_parquet(io.BytesIO(buf))
    return {
        "source": f"HF syncster-data {root}",
        "file": f["path"],
        "size_mb": round(len(buf) / 1e6, 2),
        "total_files_pre_holdout": len(cands),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "sample": df.head(2).astype(str).to_dict(orient="records"),
    }


def probe_binance_aggtrades() -> dict:
    url = "https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-2024-06-12.zip"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
        raw = r.read()
    zf = zipfile.ZipFile(io.BytesIO(raw))
    df = pd.read_csv(zf.open(zf.namelist()[0]))
    return {
        "source": "Binance Futures aggTrades BTCUSDT (2024-06-12)",
        "url": url,
        "zip_mb": round(len(raw) / 1e6, 2),
        "rows_1day": int(len(df)),
        "columns": list(df.columns),
        "has_real_aggressor": "is_buyer_maker" in [c.lower() for c in df.columns],
        "sample": df.head(2).astype(str).to_dict(orient="records"),
    }


def main() -> None:
    out = []
    for fn, arg in (
        (probe_exness_sample, "USTEC_Raw_Spread"),
        (probe_exness_sample, "USOIL_Raw_Spread"),
        (probe_hf_syncster, "SI"),
        (probe_hf_syncster, "NQ"),
        (probe_binance_aggtrades, None),
    ):
        try:
            r = fn(arg) if arg is not None else fn()
        except Exception as e:
            r = {"source": f"{fn.__name__}({arg})", "error": str(e)}
        out.append(r)
        print(json.dumps(r, ensure_ascii=False), flush=True)
    (OUT / "PROBE_NEW_TICKS_DEEP.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
