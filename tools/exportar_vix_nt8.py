#!/usr/bin/env python3
"""Exporta series diarias causales de volatilidad CBOE (VIX, VXN, VIX9D) para `EdgeLabCandidataCarril2` en NT8.

Fuente:
  1) Si existe `data/m1nt8/cboe_volatility_daily.parquet`, lo lee directamente.
  2) Si no, descarga los CSV oficiales historicos de CBOE (`VIX_History.csv`, `VXN_History.csv`, `VIX9D_History.csv`).

Salida:
  `C:\\Users\\Usuario\\Documents\\NinjaTrader 8\\EdgeLab\\datos\\cboe_vol_diario.csv`
  con columnas: `fecha,vix_close,vxn_close,vix9d_close` (YYYY-MM-DD).
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NT8_OUT = Path.home() / "Documents" / "NinjaTrader 8" / "EdgeLab" / "datos" / "cboe_vol_diario.csv"
META_OUT = ROOT / "docs" / "research" / "candidatas_nt8_20261125" / "cboe_vol_diario_meta.json"
PARQUET_LOCAL = ROOT / "data" / "m1nt8" / "cboe_volatility_daily.parquet"

CBOE_URLS = {
    "vix_close": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
    "vxn_close": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VXN_History.csv",
    "vix9d_close": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv",
}


def _fetch_cboe_series(name: str, url: str) -> pd.Series:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        df = pd.read_csv(resp)
    cols = {c.strip().upper(): c for c in df.columns}
    dcol = cols.get("DATE") or cols.get("TRADE DATE")
    ccol = cols.get("CLOSE") or cols.get(name.upper()) or cols.get("VIX") or cols.get("VXN") or cols.get("VIX9D")
    if not dcol or not ccol:
        raise ValueError(f"Columnas inesperadas en {url}: {list(df.columns)}")
    s = pd.Series(pd.to_numeric(df[ccol], errors="coerce").values, index=pd.to_datetime(df[dcol]).dt.normalize(), name=name)
    s = s.dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def build_cboe_df() -> pd.DataFrame:
    if PARQUET_LOCAL.exists():
        df = pd.read_parquet(PARQUET_LOCAL)[["vix_close", "vxn_close", "vix9d_close"]].copy()
        df.index = pd.to_datetime(df.index).normalize()
        df = df.sort_index()
    else:
        parts = [_fetch_cboe_series(k, u) for k, u in CBOE_URLS.items()]
        df = pd.concat(parts, axis=1).sort_index()
    # Forward-fill solo sobre dias pasados (causal)
    df = df.ffill().dropna(subset=["vix_close"])
    return df


def main() -> int:
    df = build_cboe_df()
    NT8_OUT.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    out.insert(0, "fecha", out.index.strftime("%Y-%m-%d"))
    out.to_csv(NT8_OUT, index=False, float_format="%.4f")

    meta = {
        "path": str(NT8_OUT),
        "rows": int(len(out)),
        "first_date": str(out["fecha"].iloc[0]),
        "last_date": str(out["fecha"].iloc[-1]),
        "non_null": {c: int(df[c].notna().sum()) for c in ("vix_close", "vxn_close", "vix9d_close")},
        "vix9d_first_date": str(df["vix9d_close"].dropna().index.min().date()) if df["vix9d_close"].notna().any() else None,
        "last_5": out.tail(5).to_dict("records"),
    }
    META_OUT.parent.mkdir(parents=True, exist_ok=True)
    META_OUT.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items() if k != "last_5"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
