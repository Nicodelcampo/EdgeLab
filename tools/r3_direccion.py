#!/usr/bin/env python3
"""R3: direccion a 15-60 min (familias A: persistencia de retorno, B: presion de flujo agresor). Manifiesto APROBADO y congelado:
docs/research/R3_DIRECCION_15_60M_MANIFIESTO_PROPUESTO_20261014.md (seccion 0 fija todas las definiciones).

  python tools/r3_direccion.py --release D:/edgelab_release_work/release_v4 --partition discovery --out docs/research/r3_direccion_20261014
  python tools/r3_direccion.py --release ... --partition replication --cells <survivors.json> --out ...      # UNA sola vez

Nunca lee trade_date >= 20261001. La replicacion crea REPLICATION_OPENED.json y se niega a repetirse.
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

ASSETS = ("NQ", "ES", "YM", "RTY", "GC")
LS = (15, 30, 60)
HS = (15, 30, 60)
FAMILIES = ("A", "B")
RTH_MIN = 390
PARTITIONS = {"discovery": (20250718, 20260331), "replication": (20260401, 20260930)}
BOOT_B = 2000
BOOT_BLOCK = 5.0
SEED = 20261014


def minute_arrays(ts, px, vol, agg, start_ns):
    """first, last (precio de trade) y volumen agresor neto por minuto de la sesion regular; NaN si no hubo trades (net = 0)."""
    m = ((ts - start_ns) // 60_000_000_000).astype(np.int64)
    first = np.full(RTH_MIN, np.nan)
    last = np.full(RTH_MIN, np.nan)
    net = np.zeros(RTH_MIN)
    idx = np.flatnonzero(np.r_[True, np.diff(m) != 0])
    mins = m[idx]
    first[mins] = px[idx]
    last[mins] = px[np.r_[idx[1:], len(px)] - 1]
    net[mins] = np.add.reduceat(vol * agg, idx)
    return first, last, net


def session_cells(first, last, net):
    """{(familia, L, H): (n, suma_r, aciertos)} para una sesion, segun la seccion 0 del manifiesto."""
    out = {}
    for L in LS:
        for H in HS:
            for fam in FAMILIES:
                n = s = h = 0
                m = L
                while m + H <= RTH_MIN:
                    entry, exit_ = first[m], last[m + H - 1]
                    if fam == "A":
                        sig = last[m - 1] - first[m - L]
                    else:
                        sig = net[m - L:m].sum()
                    if np.isfinite(entry) and np.isfinite(exit_) and np.isfinite(sig) and sig != 0:
                        r = np.sign(sig) * (exit_ - entry)
                        n += 1
                        s += r
                        h += r > 0
                    m += H
                out[(fam, L, H)] = (n, float(s), int(h))
    return out


def stationary_idx(n_sessions, B=BOOT_B, mean_block=BOOT_BLOCK, seed=SEED):
    rng = np.random.default_rng(seed)
    idx = np.empty((B, n_sessions), dtype=np.int64)
    p = 1.0 / mean_block
    for b in range(B):
        i = int(rng.integers(n_sessions))
        for t in range(n_sessions):
            idx[b, t] = i
            i = int(rng.integers(n_sessions)) if rng.random() < p else (i + 1) % n_sessions
    return idx


def holm(pvals):
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * pvals[i])
        adj[i] = min(1.0, run)
    return adj


def read_sessions(root, asset, lo, hi):
    man = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
    rio.verify_asset_hash(root, asset)
    pf = pq.ParquetFile(root / man["assets"][asset]["file"])
    rio.preflight_footer(pf)
    cols = ["ts_utc_ns", "price_ticks", "volume", "aggressor", "outside_regular", "trade_date"]
    buf = {"td": None, "c": []}
    out = []

    def flush():
        if buf["td"] is None:
            return
        td = buf["td"]
        ts = np.concatenate([c[0] for c in buf["c"]]); px = np.concatenate([c[1] for c in buf["c"]])
        vol = np.concatenate([c[2] for c in buf["c"]]); ag = np.concatenate([c[3] for c in buf["c"]]); oo = np.concatenate([c[4] for c in buf["c"]])
        buf["td"], buf["c"] = None, []
        day = pd.Timestamp(f"{td // 10000:04d}-{td // 100 % 100:02d}-{td % 100:02d} 08:30", tz="America/Chicago")
        start = day.tz_convert("UTC").value
        mk = (~oo) & (ts >= start) & (ts < start + RTH_MIN * 60_000_000_000)
        if mk.sum() < 50:
            return
        o = np.argsort(ts[mk], kind="stable")
        out.append((td, session_cells(*minute_arrays(ts[mk][o], px[mk][o], vol[mk][o], ag[mk][o], start))))

    for g in range(pf.metadata.num_row_groups):
        st = pf.metadata.row_group(g).column(pf.schema_arrow.names.index("trade_date")).statistics
        if int(st.max) < lo or int(st.min) > hi:
            continue
        if int(st.max) >= rio.HOLDOUT_FIRST_TRADE_DATE:
            raise rio.ReleaseStop("el row group alcanza el holdout")
        t = pf.read_row_group(g, columns=cols)
        td = int(t.column("trade_date")[0].as_py())
        if td < lo or td > hi:
            continue
        if buf["td"] is not None and td != buf["td"]:
            flush()
        buf["td"] = td
        buf["c"].append((t.column("ts_utc_ns").to_numpy(), t.column("price_ticks").to_numpy().astype(np.float64), t.column("volume").to_numpy().astype(np.float64),
                         t.column("aggressor").to_numpy().astype(np.float64), t.column("outside_regular").to_numpy(zero_copy_only=False)))
    flush()
    return out


def friction(repo, asset):
    d = json.loads((repo / "docs/research/r2_recorrido_vs_friccion_20261014" / f"R2_{asset}.json").read_text(encoding="utf-8"))["friction_rt_ticks"]
    return d["low"], d["high"]


def analyze(sessions, f_lo, f_hi, idx=None):
    """Por celda: media bruta/neta, acierto, IC bootstrap de sesiones y p unilateral de la media neta (F alta)."""
    res = {}
    S = len(sessions)
    if S == 0:
        return res
    if idx is None:
        idx = stationary_idx(S)
    for key in sessions[0][1]:
        n = np.array([s[1][key][0] for s in sessions], float)
        sr = np.array([s[1][key][1] for s in sessions])
        hh = np.array([s[1][key][2] for s in sessions], float)
        if n.sum() == 0:
            continue
        bn, bs = n[idx].sum(1), sr[idx].sum(1)
        ok = bn > 0
        boot = bs[ok] / bn[ok] - f_hi
        gross = sr.sum() / n.sum()
        res[key] = {"windows": int(n.sum()), "sessions": S, "hit_rate": float(hh.sum() / n.sum()), "gross_mean_ticks": float(gross),
                    "net_mean_F_low": float(gross - f_lo), "net_mean_F_high": float(gross - f_hi),
                    "ci95_net_F_high": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                    "p_one_sided": float((1 + (boot <= 0).sum()) / (len(boot) + 1))}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--partition", choices=list(PARTITIONS), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cells", help="JSON de celdas sobrevivientes (obligatorio en replicacion)")
    a = ap.parse_args()
    root, out = Path(a.release), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[1]
    lo, hi = PARTITIONS[a.partition]
    only = None
    if a.partition == "replication":
        guard = out / "REPLICATION_OPENED.json"
        if guard.exists():
            raise SystemExit("la replicacion ya se abrio una vez (REPLICATION_OPENED.json): no se repite")
        if not a.cells:
            raise SystemExit("la replicacion exige --cells con las sobrevivientes del descubrimiento")
        only = {tuple(c) if not isinstance(c, str) else tuple(c.split("|")) for c in json.loads(Path(a.cells).read_text(encoding="utf-8"))["survivors"]}
        guard.write_text(json.dumps({"opened_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cells": sorted("|".join(map(str, c)) for c in only),
                                     "release_manifest_sha256": rio.manifest_sha256(root)}, indent=1), encoding="utf-8")
    allres = {}
    for asset in ASSETS:
        t0 = time.time()
        sessions = read_sessions(root, asset, lo, hi)
        f_lo, f_hi = friction(repo, asset)
        r = analyze(sessions, f_lo, f_hi)
        for k, v in r.items():
            v["asset"] = asset
            v["friction"] = [f_lo, f_hi]
            allres[f"{asset}|{k[0]}|{k[1]}|{k[2]}"] = v
        print(asset, len(sessions), "sesiones", round(time.time() - t0, 1), "s", flush=True)
    keys = sorted(allres)
    if a.partition == "discovery":
        adj = holm(np.array([allres[k]["p_one_sided"] for k in keys]))
        for k, p in zip(keys, adj):
            allres[k]["p_holm_90"] = float(p)
        prim = [k for k in keys if k.startswith("NQ|") and k.endswith("|15|15")]
        for k in keys:
            allres[k]["primary"] = k in prim
            allres[k]["survives"] = bool((k in prim and allres[k]["ci95_net_F_high"][0] > 0) or allres[k]["p_holm_90"] < 0.05)
        surv = [k for k in keys if allres[k]["survives"]]
        (out / "R3_survivors_discovery.json").write_text(json.dumps({"survivors": surv}, indent=1), encoding="utf-8")
    else:
        sel = {k: v for k, v in allres.items() if tuple(k.split("|")) in only}
        for k, v in sel.items():
            v["confirmed"] = bool(v["ci95_net_F_high"][0] > 0 and v["net_mean_F_high"] > 0)
        allres = sel
    (out / f"R3_{a.partition}.json").write_text(json.dumps({"partition": a.partition, "range": [lo, hi], "release_manifest_sha256": rio.manifest_sha256(root), "cells": allres}, indent=1), encoding="utf-8")
    print(f"{len(allres)} celdas escritas")


if __name__ == "__main__":
    main()
