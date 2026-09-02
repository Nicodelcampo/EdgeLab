#!/usr/bin/env python3
"""FASE 7: donde vive el residuo del mejor mecanismo conocido.

F6 confirmo el mecanismo: perfil con lag -1 MAS filtro Low/High lleva los bloques
con celdas exactas de 0,07% (16) a 15,27% (3.436) y reproduce el deficit de
volumen medido en F5 (0,9964 obtenido contra 0,9959 objetivo). Los dos efectos
son aditivos: el lag solo daba 9,4%, el filtro solo no daba nada.

Falta el 85%. Este kernel no propone un mecanismo nuevo: mide DONDE esta el error
que queda, con la configuracion p=0, L=-1, filtro ON fija. Tres cortes:

  1. ESTRUCTURA DEL ERROR -- cuantas celdas difieren por bloque. Si la mayoria de
     los bloques fallan por una o dos celdas, el residuo es un borde y queda un
     off-by-one mas fino. Si difieren en decenas, el perfil es otro.
  2. UBICACION EN PRECIO -- las celdas que difieren, caen en los extremos de la
     barra (donde muerde el filtro) o repartidas por todo el rango. Extremos =
     el filtro es casi correcto pero con la barra equivocada; repartidas = la
     asignacion tick->barra no es un lag constante.
  3. UBICACION EN LA SESION -- error contra posicion del bloque en la sesion. Si
     crece con la posicion, hay deriva acumulativa (la particion se separa y no
     vuelve). Si es plano, el defecto es local a cada barra.

Las tres respuestas son mutuamente excluyentes y cada una nombra el paso
siguiente. Si el error es diffuso en los tres cortes, la conclusion es que la
paridad no se alcanza desde el parquet y hace falta instrumentar NT8 para que
exporte su perfil por barra -- un pedido concreto, no una hipotesis mas.

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
OUT = Path("/kaggle/working/avolcluster_residual")


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










BAR_PHASE = 0
PROFILE_LAG = -1


def main() -> int:
    t0 = time.time()
    commit = checkout(EXPECTED_COMMIT)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod

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
        if c:
            nt8.append({"ts": ts, "cells": c, "vol": sum(c.values()),
                        "sess": r.get("session_index")})
    lo_ns, hi_ns = min(x["ts"] for x in nt8), max(x["ts"] for x in nt8)

    hits = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))
    full = ticks_mod.load_canonical_parquet(str(hits[0]))
    idx = np.flatnonzero((full.ts_ns >= lo_ns - 3 * 86400 * 10**9)
                         & (full.ts_ns <= hi_ns + 86400 * 10**9))
    ts_ns = full.ts_ns[idx]
    px = full.price_ticks[idx].astype(np.int64)
    vol = full.volume[idx].astype(np.float64)
    n = len(px)
    sess = bars_mod.session_ids(ts_ns).astype(np.int64)
    fs = np.flatnonzero(np.concatenate(([True], sess[1:] != sess[:-1])))
    rank = np.arange(n, dtype=np.int64) - np.repeat(fs, np.diff(np.concatenate((fs, [n]))))

    bucket = np.floor_divide(rank - BAR_PHASE, TICKS_PER_BAR)
    bid = sess * 10**9 + (bucket - bucket.min())
    newbar = np.concatenate(([True], bid[1:] != bid[:-1]))
    bstart = np.flatnonzero(newbar)
    nb = len(bstart)
    bidx = np.cumsum(newbar) - 1
    bend = ts_ns[np.concatenate((bstart[1:] - 1, [n - 1]))]
    low = np.full(nb, np.iinfo(np.int64).max, np.int64)
    high = np.full(nb, np.iinfo(np.int64).min, np.int64)
    np.minimum.at(low, bidx, px)
    np.maximum.at(high, bidx, px)

    L = -PROFILE_LAG
    assign = np.concatenate((bidx[L:], np.repeat(bidx[-1], L)))
    keep = (px >= low[assign]) & (px <= high[assign])
    span = int(px.max() - px.min()) + 1
    base = int(px.min())
    a, pk, vv = assign[keep], px[keep], vol[keep]
    key = a * span + (pk - base)
    o = np.argsort(key, kind="stable")
    ks, vs = key[o], vv[o]
    e = np.flatnonzero(np.concatenate(([True], ks[1:] != ks[:-1])))
    sums = np.add.reduceat(vs, e)
    ub = (ks[e] // span).astype(np.int64)
    up = (ks[e] % span + base).astype(np.int64)
    st = np.searchsorted(ub, np.arange(nb), side="left")
    en = np.searchsorted(ub, np.arange(nb), side="right")
    print("footprint listo t=", round(time.time() - t0, 1), flush=True)

    ts_arr = np.array([x["ts"] for x in nt8], dtype=np.int64)
    pos = np.searchsorted(bend, ts_arr)

    hist_ndiff = {}
    at_edge = 0
    in_middle = 0
    edge_only_blocks = 0
    by_pos = {}
    seen_sess = {}
    matched = 0
    exact = 0
    ndiff_total = 0
    ncells_total = 0
    for i in range(len(nt8)):
        q = int(pos[i])
        best = None
        bd = None
        for c in (q - 1, q, q + 1):
            if 0 <= c < nb:
                d = abs(int(bend[c]) - int(ts_arr[i]))
                if bd is None or d < bd:
                    bd, best = d, c
        if best is None or bd > 10**9 or best - WINDOW_BARS + 1 < 0:
            continue
        matched += 1
        first = best - WINDOW_BARS + 1
        pc = {}
        for b in range(first, best + 1):
            for j in range(st[b], en[b]):
                kk = int(up[j])
                pc[kk] = pc.get(kk, 0.0) + float(sums[j])
        nc = nt8[i]["cells"]
        allk = set(pc) | set(nc)
        diff = [k for k in allk if abs(pc.get(k, 0.0) - nc.get(k, 0.0)) > 1e-9]
        nd = len(diff)
        ncells_total += len(allk)
        ndiff_total += nd
        bkey = str(nd) if nd <= 10 else ("11-20" if nd <= 20 else ("21-50" if nd <= 50 else "50+"))
        hist_ndiff[bkey] = hist_ndiff.get(bkey, 0) + 1
        if nd == 0:
            exact += 1
            continue
        # corte 2: las celdas que difieren, estan en los extremos del rango del bloque?
        blo = int(low[first:best + 1].min())
        bhi = int(high[first:best + 1].max())
        edges = 0
        for k in diff:
            if k <= blo + 1 or k >= bhi - 1:
                edges += 1
        at_edge += edges
        in_middle += nd - edges
        if edges == nd:
            edge_only_blocks += 1
        # corte 3: posicion del bloque dentro de su sesion NT8
        s = nt8[i]["sess"]
        seen_sess[s] = seen_sess.get(s, 0) + 1
        d10 = by_pos.setdefault(str(min(9, seen_sess[s] // 50)), [0, 0])
        d10[0] += 1
        d10[1] += nd

    report = {
        "schema": "avolclusterpoi_residual_localization_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "code_commit": commit, "nt8_csv_sha256": sha256(csv_path),
        "config": {"bar_phase": BAR_PHASE, "profile_lag": PROFILE_LAG, "filter": True},
        "matched": matched, "exact_blocks": exact,
        "exact_pct": round(exact / matched, 6) if matched else None,
        "corte_1_celdas_que_difieren_por_bloque": hist_ndiff,
        "corte_1_media_celdas_diff": round(ndiff_total / max(matched, 1), 3),
        "corte_1_media_celdas_por_bloque": round(ncells_total / max(matched, 1), 3),
        "corte_2_celdas_diff_en_extremos": at_edge,
        "corte_2_celdas_diff_en_medio": in_middle,
        "corte_2_bloques_que_fallan_solo_en_extremos": edge_only_blocks,
        "corte_3_error_por_decil_de_posicion_en_sesion": {
            k: {"bloques": v[0], "celdas_diff_promedio": round(v[1] / v[0], 3)}
            for k, v in sorted(by_pos.items(), key=lambda z: int(z[0]))},
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "residual_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
