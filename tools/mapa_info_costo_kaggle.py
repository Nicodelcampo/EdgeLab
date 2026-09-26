#!/usr/bin/env python3
r"""IVC: grilla de 5 minutos con estados causales y retornos futuros del medio, por sesión (manifiesto
docs/research/MANIFIESTO_MAPA_INFO_COSTO_20260926.md). Reutiliza la carga de sesiones y el detector TBZX de
tools/tbzx_reingreso_kaggle.py; para Kaggle se empaquetan los dos archivos en uno (ver build_kernel()).

    IVC_INST=ES R3_DATA=<dir> R3_OUT=<dir> python tools/mapa_info_costo_kaggle.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

if "detect" not in globals():                      # corrida local: importar el módulo hermano
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tbzx_reingreso_kaggle as R
else:                                              # kernel empaquetado: todo está en este archivo
    R = sys.modules[__name__]

NS_ = 1_000_000_000
STEP_S = 300
HORIZ = {"h1": 60, "h5": 300, "h15": 900, "h60": 3600, "h240": 14400}
RTH_OPEN, RTH_CLOSE = 9 * 3600 + 30 * 60, 16 * 3600
COMM_SIDE = {"ES": 0.2, "NQ": 0.45, "YM": 0.45}
ZONE_CFG = (20, 8)                                 # mb20_mw8


def _mid2(s, k):
    return (s["bid"][k] + s["ask"][k]).astype(np.float64)


def session_grid(s, prev_close):
    ts, px, vol = s["ts"], s["px"], s["vol"]
    n = len(ts)
    et0 = ts[0] // NS_ + s["off"]                   # segundos ET (época) del primer trade
    t0 = ((et0 // STEP_S) + 1) * STEP_S
    etN = ts[-1] // NS_ + s["off"]
    grid_et = np.arange(t0, etN, STEP_S)
    grid_ns = (grid_et - s["off"]) * NS_
    k = np.searchsorted(ts, grid_ns, side="right") - 1
    ok = k >= 0
    grid_et, grid_ns, k = grid_et[ok], grid_ns[ok], k[ok]
    m2 = _mid2(s, k)
    out = dict(et=grid_et, tod=(grid_et % 86400).astype(np.int32))
    for name, h in (("mom5", 300), ("mom15", 900), ("mom60", 3600), ("mom240", 14400)):
        j = np.searchsorted(ts, grid_ns - h * NS_, side="right") - 1
        v = (m2 - _mid2(s, np.maximum(j, 0))) / 2
        out[name] = np.where(j >= 0, v, np.nan)
    cpv = np.cumsum(px * vol); cv = np.cumsum(vol)
    out["vwap"] = px[k] - cpv[k] / np.maximum(cv[k], 1)
    sgn = np.sign(np.diff(px, prepend=px[0])).astype(np.float64)
    for i in range(1, n):                           # tick-rule: repetir el último signo en los ceros
        if sgn[i] == 0:
            sgn[i] = sgn[i - 1]
    csv = np.cumsum(sgn * vol)
    for name, h in (("ofi5", 300), ("ofi60", 3600)):
        j = np.searchsorted(ts, grid_ns - h * NS_, side="right") - 1
        jj = np.maximum(j, 0)
        num = csv[k] - csv[jj]; den = cv[k] - cv[jj]
        out[name] = np.where((j >= 0) & (den > 0), num / np.maximum(den, 1), np.nan)
    # rango de 30 min previos
    j30 = np.searchsorted(ts, grid_ns - 1800 * NS_, side="right")
    hi = np.array([px[a:b + 1].max() if b >= a else np.nan for a, b in zip(j30, k)], np.float64)
    lo = np.array([px[a:b + 1].min() if b >= a else np.nan for a, b in zip(j30, k)], np.float64)
    out["vol30"] = np.where(grid_ns - ts[0] >= 1800 * NS_, hi - lo, np.nan)
    # zona TBZX: última franja disponible al instante t
    t, H, L, C, V, bend = R.bars25(s)
    Z = R.detect(t, H, L, C, V, ZONE_CFG[0], ZONE_CFG[1], R.E0, R.R_END)
    zv = np.full(len(k), np.nan)
    if len(Z):
        avail_k = bend[Z[:, 5].astype(np.int64)]
        idx = np.searchsorted(avail_k, k, side="right") - 1
        has = idx >= 0
        zi = idx[has]
        d = Z[zi, 0]; a = Z[zi, 1]; b = Z[zi, 2]
        mid = (a + b) / 2; W = np.abs(b - a)
        zv[has] = d * (px[k[has]] - mid) / np.maximum(W, 1)
    out["zona"] = zv
    # gap: sólo en el punto de 9:35 ET, contra el cierre RTH de la sesión previa
    out["gap"] = np.full(len(k), np.nan)
    day_last = (ts[-1] // NS_ + s["off"]) // 86400 * 86400          # día ET de la sesión (el de su cierre)
    rth_open_k = np.searchsorted(ts, (day_last + RTH_OPEN - s["off"]) * NS_)
    p935 = np.nonzero(out["tod"] == RTH_OPEN + 300)[0]
    if prev_close is not None and len(p935) and rth_open_k < n:
        out["gap"][p935[0]] = px[rth_open_k] - prev_close
    # momentum intradía de la última media hora: en el punto de 15:30 ET, primera media hora (9:30→10:00) y gap
    # como estados; el objetivo es 15:30→16:00 (literatura: la primera media hora predice la última)
    out["ap30"] = np.full(len(k), np.nan); out["gap15"] = np.full(len(k), np.nan)
    out["fwd_u30"] = np.full(len(k), np.nan); out["sp_u30"] = np.full(len(k), np.nan)
    p1530 = np.nonzero(out["tod"] == 15 * 3600 + 1800)[0]
    k1000 = np.searchsorted(ts, (day_last + 10 * 3600 - s["off"]) * NS_, side="right") - 1
    k1600 = np.searchsorted(ts, (day_last + RTH_CLOSE - s["off"]) * NS_, side="right") - 1
    if len(p1530) and rth_open_k < n and k1000 > rth_open_k and (day_last + RTH_CLOSE - s["off"]) * NS_ <= ts[-1]:
        i = p1530[0]
        out["ap30"][i] = (_mid2(s, np.array([k1000]))[0] - _mid2(s, np.array([rth_open_k]))[0]) / 2
        if prev_close is not None:
            out["gap15"][i] = px[rth_open_k] - prev_close
        out["fwd_u30"][i] = (_mid2(s, np.array([k1600]))[0] - m2[i]) / 2
        out["sp_u30"][i] = float(s["ask"][k1600] - s["bid"][k1600])
    # retornos futuros del medio y costo
    spread_t = (s["ask"][k] - s["bid"][k]).astype(np.float64)
    out["spread"] = spread_t
    for name, h in HORIZ.items():
        tgt = grid_ns + h * NS_
        j = np.searchsorted(ts, tgt, side="right") - 1
        valid = tgt <= ts[-1]
        out[f"fwd_{name}"] = np.where(valid, (_mid2(s, j) - m2) / 2, np.nan)
        out[f"sp_{name}"] = np.where(valid, (s["ask"][j] - s["bid"][j]).astype(np.float64), np.nan)
    day0 = grid_et - grid_et % 86400
    close_ns = (day0 + RTH_CLOSE - s["off"]) * NS_
    jc = np.searchsorted(ts, close_ns, side="right") - 1
    validc = (out["tod"] < RTH_CLOSE) & (out["tod"] >= RTH_OPEN) & (close_ns <= ts[-1])
    out["fwd_cierre"] = np.where(validc, (_mid2(s, jc) - m2) / 2, np.nan)
    out["sp_cierre"] = np.where(validc, (s["ask"][jc] - s["bid"][jc]).astype(np.float64), np.nan)
    # cierre RTH de esta sesión, para el gap de la siguiente
    kc = np.searchsorted(ts, (day_last + RTH_CLOSE - s["off"]) * NS_, side="right") - 1
    close_rth = float(px[kc]) if kc >= 0 else None
    D = pd.DataFrame(out)
    D["td"] = s["td"]
    return D, close_rth


def run():
    inst = os.environ.get("IVC_INST", "ES")
    R.INST = inst
    out_dir = os.environ.get("R3_OUT", "/kaggle/working")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    ss = R.load_sessions(int(os.environ.get("R3_MAXSESS", "0")))
    print(inst, "sesiones", len(ss), ss[0]["td"], ss[-1]["td"], f"{time.time() - t0:.0f}s", flush=True)
    parts, prev = [], None
    for s in ss:
        D, prev = session_grid(s, prev)
        parts.append(D)
    G = pd.concat(parts, ignore_index=True)
    G["inst"] = inst
    G["comm_side"] = COMM_SIDE.get(inst, 0.3)
    G.to_parquet(f"{out_dir}/ivc_{inst}.parquet", index=False)
    print(inst, "filas", len(G), f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    for inst in os.environ.get("IVC_INSTS", os.environ.get("IVC_INST", "ES")).split(","):
        os.environ["IVC_INST"] = inst
        run()
