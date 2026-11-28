#!/usr/bin/env python3
"""Sonda de solo lectura para verificar fuentes gratuitas de datos de tick (Dukascopy, Binance Futures, Exness).
Descarga únicamente 1 hora / 1 muestra mínima de verificación para medir reachability, densidad y spread mediano.
Uso: python tools/probe_tick_sources.py
"""
from __future__ import annotations

import io
import json
import lzma
import struct
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / "docs/research/auditoria_cartera_20261126"
OUT.mkdir(parents=True, exist_ok=True)


def probe_dukascopy(symbol: str, year: int, month1: int, day: int, hour: int, point_div: float) -> dict:
    # Dukascopy URLs use 0-indexed month
    url = f"https://datafeed.dukascopy.com/datafeed/{symbol}/{year:04d}/{month1 - 1:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
    dec = lzma.decompress(raw)
    n = len(dec) // 20
    # Big-endian: >IIIff (time_ms_offset, ask_int, bid_int, ask_vol, bid_vol)
    recs = np.frombuffer(dec[: n * 20], dtype=">u4,>i4,>i4,>f4,>f4")
    ask = recs["f1"].astype(np.float64) / point_div
    bid = recs["f2"].astype(np.float64) / point_div
    spread = ask - bid
    return {
        "source": "Dukascopy .bi5 (free, no key)",
        "symbol": symbol,
        "url": url,
        "compressed_kb": round(len(raw) / 1024.0, 2),
        "ticks_in_hour": int(n),
        "mid_first": round(float((ask[0] + bid[0]) / 2.0), 3) if n else None,
        "spread_median_pts": round(float(np.median(spread)), 4) if n else None,
        "spread_p90_pts": round(float(np.percentile(spread, 90)), 4) if n else None,
        "status": "OK",
    }


def probe_http_head(name: str, url: str) -> dict:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {
                "source": name,
                "url": url,
                "http_status": int(resp.status),
                "content_length_mb": round(int(resp.headers.get("Content-Length", "0") or 0) / 1e6, 2),
                "status": "OK",
            }
    except Exception as e:
        return {"source": name, "url": url, "status": f"ERR: {e}"}


def main() -> None:
    results = []
    # 2024-06-12 14:00 UTC = 10:00 ET (RTH NY activa)
    for sym, div in (("USATECHIDXUSD", 1e3), ("USA500IDXUSD", 1e3), ("XAUUSD", 1e3), ("LIGHTCMDUSD", 1e3), ("EURUSD", 1e5)):
        try:
            r = probe_dukascopy(sym, 2024, 6, 12, 14, div)
        except Exception as e:
            r = {"source": "Dukascopy .bi5", "symbol": sym, "status": f"ERR: {e}"}
        results.append(r)

    results.append(
        probe_http_head(
            "Binance Futures Vision (aggTrades, real aggressor)",
            "https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-2024-06-12.zip",
        )
    )
    results.append(
        probe_http_head(
            "Bybit Public Trading (BTCUSDT)",
            "https://public.bybit.com/trading/BTCUSDT/BTCUSDT2024-06-12.csv.gz",
        )
    )
    results.append(
        probe_http_head(
            "Exness Public Tick Archive (XAUUSD Raw_Spread)",
            "https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/2024/06/Exness_XAUUSD_Raw_Spread_2024_06.zip",
        )
    )

    out_path = OUT / "probe_tick_sources.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    for r in results:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
