#!/usr/bin/env python3
"""FASE 3: replicar en Python el filtro Low/High de NT8 y medir si converge.

Estado tras FASE 1-2 (docs/research/avolcluster_alignment_20260902/):
la desalineacion de barras quedo REFUTADA -- offset 0 con 99,98%, timestamps
identicos al nanosegundo. El problema esta acotado a: mismas barras, mismos
timestamps, DISTINTO VOLUMEN POR CELDA. Y el volumen TOTAL del bloque coincide
solo en 13,8% de los casos, o sea hay ticks de mas o de menos.

QUE HACE NT8 (nt8/aVolClusterPOI.cs, lineas ~319-330), por cada barra primaria:
    lowTick  = PriceToTick(Low[0]);
    highTick = PriceToTick(High[0]);
    foreach (kv in tickProfile)
        if (kv.Key < lowTick || kv.Key > highTick) continue;   // descarta, no reasigna
        blockCells[kv.Key] += kv.Value;

Python (build_footprints) no tiene ese filtro: suma todo tick a su precio.

VARIANTES QUE COMPARA, todas sobre las MISMAS barras (offset 0 ya validado):
  A_sin_filtro        : lo que hace Python hoy
  B_filtro_por_barra  : replica exacta del filtro de NT8, barra por barra
  C_filtro_por_bloque : filtro con el rango [minLow, maxHigh] de las 10 barras
                        (control: distingue "filtro por barra" de "filtro por bloque")

Y ademas DIAGNOSTICA la direccion del desvio: si NT8 tiene menos volumen que
Python el filtro lo explicaria; si tiene MAS, hay una segunda fuente.

Target-free. No modifica el .cs ni el kernel Python.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "706c4fe261eec3f856cf84cc66f6d3d31f0f6680"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
DIAG_CSV = "data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv"
ART_TO_UTC_NS = 3 * 3600 * 10**9
TICKS_PER_BAR = 120
WINDOW_BARS = 10
OUT = Path("/kaggle/working/avolcluster_lowhigh")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def checkout(commit: str) -> str:
    if len(commit) != 40:
        raise SystemExit("EXPECTED_COMMIT debe ser SHA de 40 chars")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    if not (REPO_DIR / ".git").exists():
        last = None
        for attempt in range(4):
            r = subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                                REPO_URL, str(REPO_DIR)], env=env)
            if r.returncode == 0:
                break
            last = r.returncode
            subprocess.run(["rm", "-rf", str(REPO_DIR)])
            time.sleep(5 * (attempt + 1))
        else:
            raise SystemExit(f"git clone fallo tras 4 intentos (rc={last})")
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                        "edgelab/**", "data/nt8_oracles/**"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "lowhigh", commit], cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    if actual != commit:
        raise SystemExit("code provenance gate failed")
    sys.path.insert(0, str(REPO_DIR))
    return actual


def parse_cells(text):
    out = {}
    for part in (text or "").split("|"):
        if not part:
            continue
        t, _, v = part.partition(":")
        try:
            out[int(t)] = float(v)
        except ValueError:
            pass
    return out


def parse_iso_ns(s):
    import datetime as dt
    s = s.strip().replace("/", "-")
    for f in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
              "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return int(dt.datetime.strptime(s, f).replace(
                tzinfo=dt.timezone.utc).timestamp() * 10**9)
        except ValueError:
            continue
    raise ValueError(s)


def main() -> int:
    t0 = time.time()
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, "cpu=", os.cpu_count(), flush=True)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries

    csv_path = REPO_DIR / DIAG_CSV
    with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = [l for l in f if not l.startswith("# meta")]
    nt8 = []
    for r in csv.DictReader(lines):
        try:
            ts = parse_iso_ns(r["bar_close_time"]) + ART_TO_UTC_NS
        except ValueError:
            continue
        c = parse_cells(r.get("cells"))
        nt8.append({"ts": ts, "cells": c, "vol": sum(c.values())})
    print("NT8 bloques=", len(nt8), "t=", round(time.time() - t0, 1), flush=True)
    lo_ns, hi_ns = min(x["ts"] for x in nt8), max(x["ts"] for x in nt8)

    hits = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))
    full = ticks_mod.load_canonical_parquet(str(hits[0]))
    idx = np.flatnonzero((full.ts_ns >= lo_ns - 3 * 86400 * 10**9)
                         & (full.ts_ns <= hi_ns + 86400 * 10**9))
    t = TickSeries(ts_ns=full.ts_ns[idx], price_ticks=full.price_ticks[idx],
                   volume=full.volume[idx],
                   bid_ticks=full.bid_ticks[idx] if full.bid_ticks is not None else None,
                   ask_ticks=full.ask_ticks[idx] if full.ask_ticks is not None else None,
                   sequence=full.sequence[idx], tick_size=full.tick_size,
                   instrument=full.instrument, contract=full.contract, source=full.source)
    bars = bars_mod.build_tick_bars(t, TICKS_PER_BAR)
    nb = len(bars.close_t)
    px = t.price_ticks.astype(np.int64)
    vol = t.volume.astype(np.float64)
    bidx = bars.tick_bar_idx.astype(np.int64)
    print("ticks=", len(t.ts_ns), "bars=", nb, "t=", round(time.time() - t0, 1), flush=True)

    # Low/High por barra, en TICKS, tal como los ve NT8
    bar_low = np.full(nb, np.iinfo(np.int64).max, dtype=np.int64)
    bar_high = np.full(nb, np.iinfo(np.int64).min, dtype=np.int64)
    np.minimum.at(bar_low, bidx, px)
    np.maximum.at(bar_high, bidx, px)

    # el filtro de NT8 usa Low[0]/High[0] de la BARRA, que en el .cs vienen de la
    # serie primaria; aca se derivan de los mismos ticks, que es el caso favorable
    keep_bar = (px >= bar_low[bidx]) & (px <= bar_high[bidx])
    print("ticks que el filtro por barra descarta:", int((~keep_bar).sum()), flush=True)

    span = int(px.max() - px.min()) + 1
    base = int(px.min())

    def footprint(mask, bi):
        k = bi[mask] * span + (px[mask] - base)
        o = np.argsort(k, kind="stable")
        ks, vs = k[o], vol[mask][o]
        e = np.flatnonzero(np.concatenate(([True], ks[1:] != ks[:-1])))
        s = np.add.reduceat(vs, e)
        uk = ks[e]
        return (uk // span).astype(np.int64), (uk % span + base).astype(np.int64), s

    # D/E: la asignacion tick->barra corrida un tick. NT8 acumula el perfil en un
    # handler distinto del que cierra la barra, asi que un tick de frontera puede
    # caer del otro lado. Es la unica familia de causa que mueve el volumen por
    # celda SIN mover casi el total, que es exactamente lo observado.
    bidx_lag = np.empty_like(bidx); bidx_lag[0] = bidx[0]; bidx_lag[1:] = bidx[:-1]
    bidx_lead = np.empty_like(bidx); bidx_lead[-1] = bidx[-1]; bidx_lead[:-1] = bidx[1:]

    fpA = footprint(np.ones(len(px), bool), bidx)
    fpB = footprint(keep_bar, bidx)
    fpD = footprint(np.ones(len(px), bool), bidx_lag)
    fpE = footprint(np.ones(len(px), bool), bidx_lead)
    print("footprints listos t=", round(time.time() - t0, 1), flush=True)

    def indexer(fp):
        ub, up, s = fp
        st = np.searchsorted(ub, np.arange(nb), side="left")
        en = np.searchsorted(ub, np.arange(nb), side="right")
        return ub, up, s, st, en

    IA, IB, ID, IE = (indexer(f) for f in (fpA, fpB, fpD, fpE))

    def block_cells(I, first):
        _ub, up, s, st, en = I
        out = {}
        if first < 0 or first + WINDOW_BARS > nb:
            return out
        for b in range(first, first + WINDOW_BARS):
            for j in range(st[b], en[b]):
                kk = int(up[j])
                out[kk] = out.get(kk, 0.0) + float(s[j])
        return out

    end_ns = bars.end_ns
    ts_arr = np.array([x["ts"] for x in nt8], dtype=np.int64)
    pos = np.searchsorted(end_ns, ts_arr)

    names = ("A_sin_filtro", "B_filtro_por_barra", "C_filtro_por_bloque",
             "D_tick_a_barra_anterior", "E_tick_a_barra_siguiente")
    stats = {n: {"exact_cells": 0, "exact_volume": 0, "sum_abs_diff": 0.0,
                 "only_py": 0, "only_nt8": 0, "val_diff": 0} for n in names}
    dir_counts = {"nt8_menos_volumen": 0, "nt8_mas_volumen": 0, "igual": 0}
    matched = 0

    for i in range(len(nt8)):
        p = int(pos[i])
        best, bd = None, None
        for k in (p - 1, p, p + 1):
            if 0 <= k < nb:
                d = abs(int(end_ns[k]) - int(ts_arr[i]))
                if bd is None or d < bd:
                    bd, best = d, k
        if best is None or bd > 10**9:
            continue
        first = best - WINDOW_BARS + 1
        if first < 0:
            continue
        matched += 1
        nc = nt8[i]["cells"]
        nvol = nt8[i]["vol"]

        cA = block_cells(IA, first)
        cB = block_cells(IB, first)
        # C: filtro con el rango del BLOQUE entero
        lo_b = int(bar_low[first:first + WINDOW_BARS].min())
        hi_b = int(bar_high[first:first + WINDOW_BARS].max())
        cC = {k: v for k, v in cA.items() if lo_b <= k <= hi_b}
        cD = block_cells(ID, first)
        cE = block_cells(IE, first)

        pvol = sum(cA.values())
        if nvol < pvol - 1e-9:
            dir_counts["nt8_menos_volumen"] += 1
        elif nvol > pvol + 1e-9:
            dir_counts["nt8_mas_volumen"] += 1
        else:
            dir_counts["igual"] += 1

        for name, pc in zip(names, (cA, cB, cC, cD, cE)):
            only_py = set(pc) - set(nc)
            only_nt8 = set(nc) - set(pc)
            shared = set(pc) & set(nc)
            dv = [k for k in shared if abs(pc[k] - nc[k]) > 1e-9]
            st_ = stats[name]
            st_["only_py"] += len(only_py)
            st_["only_nt8"] += len(only_nt8)
            st_["val_diff"] += len(dv)
            st_["sum_abs_diff"] += sum(abs(pc.get(k, 0.0) - nc.get(k, 0.0))
                                       for k in (set(pc) | set(nc)))
            if abs(sum(pc.values()) - nvol) < 1e-9:
                st_["exact_volume"] += 1
            if not only_py and not only_nt8 and not dv:
                st_["exact_cells"] += 1

    for n in names:
        stats[n]["sum_abs_diff"] = round(stats[n]["sum_abs_diff"], 3)
        stats[n]["exact_cells_pct"] = round(stats[n]["exact_cells"] / matched, 6) if matched else None
        stats[n]["exact_volume_pct"] = round(stats[n]["exact_volume"] / matched, 6) if matched else None

    report = {
        "schema": "avolclusterpoi_lowhigh_filter_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "question": "replicar el filtro Low/High de NT8 hace converger el footprint",
        "code_commit": commit, "nt8_csv_sha256": sha256(csv_path),
        "n_matched": matched,
        "ticks_discarded_by_bar_filter": int((~keep_bar).sum()),
        "volume_direction": dir_counts,
        "variants": stats,
        "interpretation": (
            "B usa el rango de la propia barra derivado de los mismos ticks, asi que "
            "si ticks_discarded_by_bar_filter == 0 el filtro Low/High NO PUEDE ser la "
            "causa bajo barras alineadas: queda refutado sin necesidad de mas datos. "
            "D y E prueban la unica familia que mueve volumen por celda casi sin mover "
            "el total: el tick de frontera asignado a la barra vecina. Si D o E bajan "
            "sum_abs_diff frente a A, la causa es un off-by-one de asignacion. Si "
            "ninguna baja y nt8_mas_volumen es alto, NT8 ve ticks que el parquet no "
            "tiene y el problema es de fuente de datos, no de kernel."),
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lowhigh_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
