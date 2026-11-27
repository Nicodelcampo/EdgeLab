#!/usr/bin/env python3
"""Camino intradía (minuto a minuto) del P&L de cada estrategia de la cartera NT8, por sesión, en USD con 1 micro
(pre-registro docs/research/preset_diversificada_20261127/ADENDA_DLL_INTRADIA.md).

Para cada operación de las corridas NT8 (y del arnés para N):
  - desde el cierre de la vela de entrada se descuenta la fricción canónica del micro;
  - en cada vela posterior hasta la anterior a la de salida, el no realizado en el extremo ADVERSO de la vela (bajo si va largo, alto si
    va corto);
  - desde la vela de salida, el realizado (pnl_pts del archivo, que ya trae 1 tick de deslizamiento).
El minuto 0 de la sesión es las 18:00 ET del día anterior; la sesión es `fecha_int` del archivo.

  python tools/intradia_min_cartera.py          # arma el caché data/intradia_cartera/<estrategia>.npz
Uso desde cartera_lucid: `caminos(universo)` y `minimo_plan(caminos, tabla, sesiones)`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab import costos  # noqa: E402

CACHE = ROOT / "data" / "intradia_cartera"
MIN_SES = 1441
MICRO = {"NQ": "MNQ", "ES": "MES"}


def _barras(inst: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    d = pd.read_parquet(ROOT / "data" / "m1nt8" / f"{inst}_M1_nonadj_utc.parquet",
                        filters=[("datetime", ">=", pd.Timestamp("2018-12-01")), ("datetime", "<", pd.Timestamp("2026-10-01"))])
    t_ny = (pd.DatetimeIndex(d.index).tz_localize("UTC") + pd.Timedelta(minutes=1)).tz_convert("America/New_York").tz_localize(None)
    return t_ny.values.astype("datetime64[m]").astype(np.int64), d.high.to_numpy(float), d.low.to_numpy(float)


def camino_estrategia(path: Path, inst: str) -> tuple[np.ndarray, np.ndarray]:
    """(sesiones yyyymmdd, matriz sesiones × 1441 minutos) del P&L acumulado intradía en USD con 1 micro."""
    o = pd.read_csv(path)
    o = o[o.riesgo_pts > 0]
    mic = MICRO[inst]; pv = costos.tick_value_usd(mic) / costos.tick_size(mic); fr = costos.friccion_rt_puntos(mic, "base")
    tm, hi, lo = _barras(inst)
    ses = np.array(sorted(o.fecha_int.astype(int).unique()))
    pos = {s: i for i, s in enumerate(ses)}
    M = np.zeros((len(ses), MIN_SES), np.float32)
    for r in o.itertuples(index=False):
        s = int(r.fecha_int)
        d0 = pd.Timestamp(str(s)) - pd.Timedelta(days=1) + pd.Timedelta(hours=18)
        en, ex = pd.Timestamp(r.en_ny), pd.Timestamp(r.ex_ny)
        a = int((en - d0) / pd.Timedelta(minutes=1)); b = int((ex - d0) / pd.Timedelta(minutes=1))
        if not (0 <= a < MIN_SES) or b < a:
            continue
        b = min(b, MIN_SES - 1)                       # salida después de la ventana (feriados): realizado al último minuto
        fila = M[pos[s]]
        fila[a:] -= fr * pv                                                     # fricción desde la entrada
        if b > a + 1:
            i0 = np.searchsorted(tm, np.datetime64(en, "m").astype(np.int64) + 1)
            i1 = np.searchsorted(tm, np.datetime64(d0, "m").astype(np.int64) + b)  # velas (en, salida): sin la de salida
            mins = ((tm[i0:i1] - np.datetime64(d0, "m").astype(np.int64))).astype(int)
            adv = (lo[i0:i1] - r.entry_price) if r.side > 0 else (r.entry_price - hi[i0:i1])
            ok = (mins > a) & (mins < b)
            # minuto sin vela (raro, feriados): no realizado 0
            nr = np.zeros(b - a - 1, np.float32)
            nr[mins[ok] - a - 1] = adv[ok] * pv
            fila[a + 1:b] += nr
        fila[b:] += r.pnl_pts * pv                                               # realizado
    return ses, M


def caminos(universo: dict, cache: bool = True) -> dict:
    """{estrategia: (sesiones, matriz)} para un universo de cartera_lucid ({nombre: (ruta, inst)})."""
    out = {}
    CACHE.mkdir(parents=True, exist_ok=True)
    for k, (p, inst) in universo.items():
        f = CACHE / f"{k}.npz"
        if cache and f.exists():
            z = np.load(f); out[k] = (z["ses"], z["M"]); continue
        ses, M = camino_estrategia(p, inst)
        np.savez_compressed(f, ses=ses, M=M); out[k] = (ses, M)
        print(k, len(ses), "sesiones", flush=True)
    return out


def minimo_plan(cam: dict, tabla: dict, sesiones: pd.DatetimeIndex) -> pd.Series:
    """Mínimo intradía del día (USD) de un plan: Σ_k micros_k(trimestre) × camino_k, mínimo sobre los minutos (incluye el 0 inicial)."""
    out = np.zeros(len(sesiones))
    ses_int = sesiones.strftime("%Y%m%d").astype(int).to_numpy()
    q = sesiones.to_period("Q").start_time
    idx = {k: dict(zip(s.tolist(), range(len(s)))) for k, (s, _) in cam.items()}
    for j, (s, t) in enumerate(zip(ses_int, q)):
        tot = None
        for k, (_, M) in cam.items():
            i = idx[k].get(s)
            if i is None:
                continue
            n = tabla.get(t, {}).get(k, 0)
            if n:
                tot = M[i] * n if tot is None else tot + M[i] * n
        out[j] = min(0.0, float(tot.min())) if tot is not None else 0.0
    return pd.Series(out, index=sesiones)


if __name__ == "__main__":
    import cartera_lucid as CL
    caminos(CL.ESTR10, cache=False)
