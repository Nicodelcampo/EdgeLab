#!/usr/bin/env python3
"""R2: recorrido bruto disponible vs friccion de viaje redondo. Manifiesto: docs/research/R2_RECORRIDO_VS_FRICCION_MANIFIESTO_20261014.md

Target-free: sin senales, sin direccion, sin P&L. Lee la release liquid_tick_v1 con preflight de ambos relojes y hash verificado.
Uso: python tools/r2_recorrido_vs_friccion.py --release D:/edgelab_release_work/release_v4 --out docs/research/r2_recorrido_vs_friccion_20261014 [--assets ES NQ]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_io as rio  # noqa: E402

HORIZONS = (1, 5, 15, 30, 60)
QS = (10, 25, 50, 75, 90, 99)
RTH_MIN = 390                      # 08:30-15:00 CT
SLIPPAGE_RT = 2.0                  # declarado por Nico (1 tick por lado)
# comision round-turn en ticks (min, max) entre las firmas que admiten algoritmos: REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md
COMM = {"ES": (0.28, 0.46), "NQ": (0.70, 1.15), "MES": (0.80, 1.52), "MNQ": (2.00, 3.80), "GC": (0.43, 0.62), "MGC": (1.50, 2.20),
        "6E": (0.68, 0.82), "6B": (0.68, 0.82), "6J": (0.68, 0.82), "YM": (0.70, 1.15), "MYM": (2.00, 3.80), "RTY": (0.70, 0.94),
        "MBT": (4.6, 5.8), "ZB": (0.14, 0.19)}
APROX = {"MBT", "ZB", "6B", "6J", "RTY", "YM", "MYM", "MGC"}      # comision aproximada (sin tabla directa de las props)


def spreads(root: Path) -> dict:
    d = json.loads((root / "docs/research/kaggle_v4_kernels_20261014/ATLAS_MICROESTRUCTURA_14ACTIVOS_V4.json").read_text(encoding="utf-8"))
    return {a: float(v["rth_spread_mean_ticks"]) for a, v in d["scale_equivalence_atj18"].items()}


def session_minutes(ts, px, start_ns):
    """hi, lo, first, last por minuto de la sesion regular (NaN si no hubo trades)."""
    m = ((ts - start_ns) // 60_000_000_000).astype(np.int64)
    hi = np.full(RTH_MIN, np.nan); lo = np.full(RTH_MIN, np.nan); first = np.full(RTH_MIN, np.nan); last = np.full(RTH_MIN, np.nan)
    idx = np.flatnonzero(np.r_[True, np.diff(m) != 0])
    mins = m[idx]
    hi[mins] = np.maximum.reduceat(px, idx)
    lo[mins] = np.minimum.reduceat(px, idx)
    first[mins] = px[idx]
    ends = np.r_[idx[1:], len(px)] - 1
    last[mins] = px[ends]
    return hi, lo, first, last


def windows(hi, lo, first, last, H):
    """R_H y D_H para cada inicio de minuto m con m+H <= RTH_MIN y datos en los extremos de la ventana."""
    n = RTH_MIN - H + 1
    from numpy.lib.stride_tricks import sliding_window_view as sw
    with np.errstate(all="ignore"):
        wh = np.nanmax(sw(np.nan_to_num(hi, nan=-np.inf), H), axis=1)
        wl = np.nanmin(sw(np.nan_to_num(lo, nan=np.inf), H), axis=1)
    start_px = first[:n]
    end_px = last[H - 1:H - 1 + n]
    ok = np.isfinite(wh) & np.isfinite(wl) & np.isfinite(start_px) & np.isfinite(end_px)
    R = np.where(ok, wh - wl, np.nan)
    D = np.where(ok, np.abs(end_px - start_px), np.nan)
    return R, D, np.arange(n)


def run_asset(root: Path, asset: str, sp: float):
    t0 = time.time()
    rio.verify_asset_hash(root, asset)
    man = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
    pf = pq.ParquetFile(root / man["assets"][asset]["file"])
    rio.preflight_footer(pf)
    names = pf.schema_arrow.names
    cols = ["ts_utc_ns", "price_ticks", "outside_regular", "trade_date"]
    acc = {H: {"R": [], "D": [], "start": [], "sess": []} for H in HORIZONS}
    sessions = 0
    sess_rows = []
    buf = {"td": None, "ts": [], "px": [], "out": []}

    def flush():
        nonlocal sessions
        if buf["td"] is None:
            return
        td = buf["td"]
        ts = np.concatenate(buf["ts"]); px = np.concatenate(buf["px"]); out = np.concatenate(buf["out"])
        buf.update(td=None, ts=[], px=[], out=[])
        day = pd.Timestamp(f"{td // 10000:04d}-{td // 100 % 100:02d}-{td % 100:02d} 08:30", tz="America/Chicago")
        start = day.tz_convert("UTC").value
        m = (~out) & (ts >= start) & (ts < start + RTH_MIN * 60_000_000_000)
        if m.sum() < 50:
            return
        o = np.argsort(ts[m], kind="stable")
        hi, lo, first, last = session_minutes(ts[m][o], px[m][o], start)
        sessions += 1
        for H in HORIZONS:
            R, D, st = windows(hi, lo, first, last, H)
            ok = np.isfinite(R)
            acc[H]["R"].append(R[ok]); acc[H]["D"].append(D[ok]); acc[H]["start"].append(st[ok]); acc[H]["sess"].append(np.full(ok.sum(), sessions - 1))

    for g in range(pf.metadata.num_row_groups):
        t = pf.read_row_group(g, columns=cols)
        td = int(t.column("trade_date")[0].as_py())
        if buf["td"] is not None and td != buf["td"]:
            flush()
        buf["td"] = td
        buf["ts"].append(t.column("ts_utc_ns").to_numpy()); buf["px"].append(t.column("price_ticks").to_numpy().astype(np.float64))
        buf["out"].append(t.column("outside_regular").to_numpy(zero_copy_only=False))
    flush()
    f_lo = sp + COMM[asset][0] + SLIPPAGE_RT
    f_hi = sp + COMM[asset][1] + SLIPPAGE_RT
    res = {"asset": asset, "sessions": sessions, "spread_mean_rth_ticks": sp, "commission_rt_ticks": list(COMM[asset]), "commission_approx": asset in APROX,
           "slippage_rt_ticks": SLIPPAGE_RT, "friction_rt_ticks": {"low": round(f_lo, 3), "high": round(f_hi, 3)}, "horizons": {}}
    for H in HORIZONS:
        R = np.concatenate(acc[H]["R"]); D = np.concatenate(acc[H]["D"]); st = np.concatenate(acc[H]["start"]); se = np.concatenate(acc[H]["sess"])
        hour = 8 + (st + 30) // 60                      # hora CT de inicio (08:30 -> 9 no: 8:30+m minutos)
        hour = ((8 * 60 + 30 + st) // 60).astype(int)
        def q(a): return {f"p{p}": round(float(np.percentile(a, p)), 2) for p in QS} if len(a) else {}
        entry = {"windows": int(len(R)), "R": q(R), "D": q(D),
                 "frac_R_ge_F_low": round(float((R >= f_lo).mean()), 4), "frac_R_ge_F_high": round(float((R >= f_hi).mean()), 4),
                 "frac_D_ge_F_low": round(float((D >= f_lo).mean()), 4), "frac_D_ge_F_high": round(float((D >= f_hi).mean()), 4),
                 "frac_sessions_with_any_R_ge_F_high": round(float(len(np.unique(se[R >= f_hi])) / sessions), 4),
                 "median_session_median_R": round(float(np.median([np.median(R[se == s]) for s in np.unique(se)])), 2),
                 "by_start_hour_CT": {}}
        for h in sorted(set(hour.tolist())):
            k = hour == h
            entry["by_start_hour_CT"][str(h)] = {"windows": int(k.sum()), "R_p50": round(float(np.percentile(R[k], 50)), 2), "R_p90": round(float(np.percentile(R[k], 90)), 2),
                                                 "frac_R_ge_F_high": round(float((R[k] >= f_hi).mean()), 4), "frac_D_ge_F_high": round(float((D[k] >= f_hi).mean()), 4)}
        res["horizons"][str(H)] = entry
    res["seconds"] = round(time.time() - t0, 1)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--assets", nargs="*")
    a = ap.parse_args()
    repo = Path(__file__).resolve().parents[1]
    root = Path(a.release)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sp = spreads(repo)
    man = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
    for asset in (a.assets or list(man["assets"])):
        r = run_asset(root, asset, sp[asset])
        r["release_manifest_sha256"] = rio.manifest_sha256(root)
        (out / f"R2_{asset}.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
        print(asset, r["sessions"], "sesiones", r["seconds"], "s | F", r["friction_rt_ticks"], "| 15m frac R>=F_hi", r["horizons"]["15"]["frac_R_ge_F_high"], flush=True)


if __name__ == "__main__":
    main()
