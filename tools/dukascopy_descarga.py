#!/usr/bin/env python3
"""Descarga autónoma de ticks de Dukascopy por HTTP (sin JForex; corre en el Debian). Formato público del datafeed:
  https://datafeed.dukascopy.com/datafeed/<SIM>/<AAAA>/<MM 0-based>/<DD>/<HH>h_ticks.bi5   (LZMA; registros de 20 bytes big-endian:
  uint32 ms desde la hora, uint32 ask, uint32 bid, float32 ask_vol, float32 bid_vol; precio = entero / PUNTO[SIM])

  python tools/dukascopy_descarga.py USATECHIDXUSD --desde 2026-09-30 --hasta 2026-10-21 --salida /var/lib/edgelab-datos/holdout_sellado
  python tools/dukascopy_descarga.py USATECHIDXUSD --validar-contra <carpeta JForex HD_NQ>/USATECHIDXUSD/ticks --dia 2026-10-02

Escribe un parquet por día UTC (time_utc_ns, bid, ask, bid_vol, ask_vol) como .part y lo renombra al terminar (un archivo final =
día completo). Retoma solo. Los días >= la frontera del holdout van SIEMPRE a la carpeta sellada que se indique (nunca a la de
desarrollo) y quedan fuera de Kaggle. `--validar-contra` compara un día con la descarga de JForex: si el PUNTO de un símbolo
estuviera mal, los precios no coinciden y la descarga se niega a seguir.
"""
from __future__ import annotations

import argparse
import datetime as dt
import lzma
import struct
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

URL = "https://datafeed.dukascopy.com/datafeed/{s}/{y:04d}/{m:02d}/{d:02d}/{h:02d}h_ticks.bi5"
PUNTO = {"USATECHIDXUSD": 1000.0, "USA500IDXUSD": 1000.0, "USA30IDXUSD": 1000.0, "XAUUSD": 1000.0, "EURUSD": 100000.0, "GBPUSD": 100000.0, "USDJPY": 1000.0}


def decodificar(crudo: bytes, hora_utc_ms: int, punto: float) -> pd.DataFrame:
    if not crudo: return pd.DataFrame(columns=["time_utc_ns", "bid", "ask", "bid_vol", "ask_vol"])
    b = lzma.decompress(crudo); n = len(b) // 20
    a = np.frombuffer(b[:n * 20], dtype=np.dtype([("ms", ">u4"), ("ask", ">u4"), ("bid", ">u4"), ("av", ">f4"), ("bv", ">f4")]))
    return pd.DataFrame(dict(time_utc_ns=(hora_utc_ms + a["ms"].astype(np.int64)) * 1_000_000, bid=a["bid"] / punto, ask=a["ask"] / punto,
                             bid_vol=a["bv"].astype(float), ask_vol=a["av"].astype(float)))


UA = "Mozilla/5.0 (X11; Linux x86_64)"   # con un User-Agent propio el datafeed resetea más conexiones (medido 2026-10-24)
PAUSA_S = 0.6                           # ritmo mínimo entre pedidos: el datafeed limita la tasa (429 "Too Many Requests", 503)
_ultimo = [0.0]


def _esperar_turno(dormir=time.sleep, reloj=time.monotonic):
    falta = PAUSA_S - (reloj() - _ultimo[0])
    if falta > 0: dormir(falta)
    _ultimo[0] = reloj()


def bajar_hora(sim, t: dt.datetime, reintentos=8, abrir=urllib.request.urlopen, dormir=time.sleep) -> bytes:
    """404 = hora sin datos. 429/503/5xx o conexión cortada = límite de tasa: espera creciente con tope (5 s, 10, 20 … 120 s;
    ~7 min en total) en vez de rendirse a los ~15 s como antes (causa de la falla en la primera hora, 2026-10-23)."""
    url = URL.format(s=sim, y=t.year, m=t.month - 1, d=t.day, h=t.hour)
    for i in range(reintentos):
        _esperar_turno(dormir)
        try:
            with abrir(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return b""                                   # hora sin datos (mercado cerrado)
            espera = float(e.headers.get("Retry-After") or 0) if getattr(e, "headers", None) else 0
            dormir(max(espera, min(120, 5 * 2 ** i)))
        except Exception:
            dormir(min(120, 5 * 2 ** i))
    raise RuntimeError(f"no se pudo bajar {url} tras {reintentos} intentos (límite de tasa del datafeed)")


def bajar_dia(sim, dia: dt.date, salida: Path, bajar=bajar_hora) -> Path | None:
    fin = salida / sim / f"{dia.isoformat()}.parquet"
    if fin.exists(): return fin
    fin.parent.mkdir(parents=True, exist_ok=True)
    partes = []
    for h in range(24):
        t = dt.datetime(dia.year, dia.month, dia.day, h, tzinfo=dt.timezone.utc)
        partes.append(decodificar(bajar(sim, t), int(t.timestamp() * 1000), PUNTO[sim]))
    df = pd.concat(partes, ignore_index=True)
    if not len(df): return None                                          # día sin mercado: no se escribe (se reintenta si fue error)
    part = fin.with_suffix(".part"); df.to_parquet(part, index=False); part.replace(fin)
    return fin


def leer_jforex_bin(ruta: Path) -> pd.DataFrame:
    """Archivo diario de la estrategia HD_NQ de JForex: registros big-endian de 32 bytes (long ms, double bid, double ask, float bv, float av)."""
    a = np.fromfile(ruta, dtype=np.dtype([("ms", ">i8"), ("bid", ">f8"), ("ask", ">f8"), ("bv", ">f4"), ("av", ">f4")]))
    return pd.DataFrame(dict(time_utc_ns=a["ms"].astype(np.int64) * 1_000_000, bid=a["bid"], ask=a["ask"], bid_vol=a["bv"].astype(float), ask_vol=a["av"].astype(float)))


def validar(sim, dia: dt.date, carpeta_jforex: Path, salida: Path) -> dict:
    a = pd.read_parquet(bajar_dia(sim, dia, salida)); b = leer_jforex_bin(carpeta_jforex / f"{dia.isoformat()}.bin")
    m = a.merge(b, on="time_utc_ns", suffixes=("", "_jf"))
    ok = len(m) > 0.9 * min(len(a), len(b)) and np.allclose(m.bid, m.bid_jf, atol=1e-6) and np.allclose(m.ask, m.ask_jf, atol=1e-6)
    return dict(simbolo=sim, dia=dia.isoformat(), ticks_http=len(a), ticks_jforex=len(b), coinciden=int(len(m)), ok=bool(ok))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("simbolo"); ap.add_argument("--desde"); ap.add_argument("--hasta"); ap.add_argument("--salida", required=False)
    ap.add_argument("--validar-contra"); ap.add_argument("--dia")
    a = ap.parse_args()
    if a.validar_contra:
        r = validar(a.simbolo, dt.date.fromisoformat(a.dia), Path(a.validar_contra), Path(a.salida or "."))
        print(r); sys.exit(0 if r["ok"] else 1)
    d, h = dt.date.fromisoformat(a.desde), dt.date.fromisoformat(a.hasta)
    while d <= h:
        if d.weekday() != 5: print(d, bajar_dia(a.simbolo, d, Path(a.salida)), flush=True)    # sábado UTC: cerrado
        d += dt.timedelta(days=1)
