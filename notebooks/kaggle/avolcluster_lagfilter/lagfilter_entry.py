#!/usr/bin/env python3
"""FASE 6: perfil desfasado MAS filtro Low/High. Mecanismo unico candidato.

Cadena hasta aca:
  F2 desalineacion de barras REFUTADA (offset 0 al 99,98%, dt mediano 0 ns).
  F3 filtro Low/High refutado BAJO EL SUPUESTO de que el perfil coincide con la
     barra -- el rango de una barra derivado de sus propios ticks los contiene a
     todos, asi que el filtro descartaba 0. Ese supuesto acaba de caerse.
  F4 fase de particion: pico nitido en k=-1 (9,01% contra 0,07%), real y parcial.
  F5 conservacion por sesion: NT8 tiene 99,59% del volumen del parquet, con
     DEFICIT SISTEMATICO en las 51 sesiones (ratio 0,9937-0,9972, signo siempre
     negativo, 120.830 contratos). No es ruido ni fuente distinta: es una
     PERDIDA, y el .cs tiene exactamente un lugar donde se pierde volumen.

MECANISMO PROPUESTO, el unico compatible con las cinco observaciones:
  el perfil de NT8 se acumula DESFASADO respecto de la barra que lo cierra, y
  aVolClusterPOI.cs (~319-330) descarta sin reasignar todo lo que cae fuera de
  [Low[0], High[0]] de esa barra. El desfasaje redistribuye -- explica el 21,5%
  de bloques donde NT8 tiene MAS volumen -- y el filtro pierde -- explica el
  deficit sistematico. Ninguno de los dos por separado explica ambas cosas.

BARRIDO: fase de barra p x lag del perfil L x filtro on/off.
  p  define las fronteras de barra, y por lo tanto Low/High
  L  el tick i aporta a la barra de i-L
  filtro on -> se descarta el tick que cae fuera del rango de esa barra

PREDICCION FALSABLE: si el mecanismo es correcto, alguna combinacion con filtro
ON y L != 0 debe subir los bloques exactos MUY por encima del 9% de F4 y
reproducir un ratio de volumen cercano a 0,9959. Si el mejor sigue en ~9%, o si
el filtro no genera deficit, el mecanismo se descarta y vuelve a abrirse la
hipotesis de fuente de datos.

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
OUT = Path("/kaggle/working/avolcluster_lagfilter")


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








BAR_PHASES = (0, -1, -2)
PROFILE_LAGS = (0, -1, -2, 1, 2)


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
            nt8.append({"ts": ts, "cells": c, "vol": sum(c.values())})
    print("NT8 bloques=", len(nt8), flush=True)
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
    span = int(px.max() - px.min()) + 1
    base = int(px.min())
    ts_arr = np.array([x["ts"] for x in nt8], dtype=np.int64)
    print("ticks=", n, flush=True)

    def bars_for_phase(p):
        bucket = np.floor_divide(rank - p, TICKS_PER_BAR)
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
        return bidx, nb, bend, low, high

    out = {}
    for p in BAR_PHASES:
        bidx, nb, bend, low, high = bars_for_phase(p)
        pos = np.searchsorted(bend, ts_arr)
        for L in PROFILE_LAGS:
            if L == 0:
                assign = bidx
            elif L > 0:
                assign = np.concatenate((bidx[:L], bidx[:-L]))
            else:
                assign = np.concatenate((bidx[-L:], np.repeat(bidx[-1], -L)))
            for use_filter in (False, True):
                if use_filter:
                    keep = (px >= low[assign]) & (px <= high[assign])
                else:
                    keep = np.ones(n, bool)
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

                ex = exv = matched = 0
                sad = 0.0
                pv = 0.0
                nv = 0.0
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
                    pc = {}
                    for b in range(best - WINDOW_BARS + 1, best + 1):
                        for j in range(st[b], en[b]):
                            kk = int(up[j])
                            pc[kk] = pc.get(kk, 0.0) + float(sums[j])
                    nc = nt8[i]["cells"]
                    sad += sum(abs(pc.get(x, 0.0) - nc.get(x, 0.0)) for x in (set(pc) | set(nc)))
                    pv += sum(pc.values())
                    nv += nt8[i]["vol"]
                    if abs(sum(pc.values()) - nt8[i]["vol"]) < 1e-9:
                        exv += 1
                    if set(pc) == set(nc) and all(abs(pc[x] - nc[x]) < 1e-9 for x in pc):
                        ex += 1
                name = "p%d_L%d_%s" % (p, L, "filtro" if use_filter else "sinfiltro")
                out[name] = {"matched": matched, "exact_cells": ex,
                             "exact_cells_pct": round(ex / matched, 6) if matched else None,
                             "exact_volume": exv, "sum_abs_diff": round(sad, 1),
                             "nt8_over_py_volume": round(nv / pv, 6) if pv else None,
                             "ticks_dropped": int((~keep).sum())}
                print(name, out[name], "t=", round(time.time() - t0, 1), flush=True)

    best = max(out, key=lambda z: out[z]["exact_cells"])
    report = {
        "schema": "avolclusterpoi_lag_plus_lowhigh_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "code_commit": commit, "nt8_csv_sha256": sha256(csv_path),
        "baseline_p0_L0_sinfiltro": out.get("p0_L0_sinfiltro"),
        "best_variant": best, "best": out[best],
        "target_volume_ratio_from_F5": 0.995882,
        "variants": out,
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lagfilter_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "variants"},
                     indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
