#!/usr/bin/env python3
"""FASE 8: la frontera de barra no parte un grupo de ticks del mismo timestamp.

F7 localizo el residuo del mejor mecanismo (p=0, L=-1, filtro ON, 15,27% exacto):
  corte 1  el error es CHICO -- 3,5 celdas difieren de 93,6 por bloque (3,8%), y
           41% de los bloques fallan por dos celdas o menos.
  corte 2  las celdas que difieren estan EN EL MEDIO del rango (76.003) y no en
           los extremos (3.839). El filtro Low/High no es donde vive el residuo.
  corte 3  el error es PLANO a lo largo de la sesion (3,8 a 4,7 celdas, sin
           tendencia). No hay deriva acumulativa: el defecto es local a la barra.

Chico, local, sin deriva, y de asignacion (no de filtro). Esa firma la produce
una sola cosa: la frontera de barra cae en un lugar distinto en cada barra, por
poco, y se recupera sola. Que el 51% de los ticks de NQ comparta timestamp con
el anterior da el mecanismo: NT8 no corta una barra en el MEDIO de un grupo de
ticks simultaneos. El parquet, contado como 120 filas consecutivas, si lo corta.

VARIANTES sobre el corte de 120 ticks, todas dentro de la sesion:
  crudo      corta exactamente en 120 (lo que hace el kernel hoy)
  extiende   si el corte cae dentro de un grupo de igual timestamp, cierra al
             TERMINAR el grupo (la barra queda larga)
  trunca     cierra ANTES de que empiece el grupo (la barra queda corta)
cada una cruzada con lag de perfil 0 / -1 y filtro Low/High on/off.

PREDICCION FALSABLE: si el mecanismo es correcto, alguna variante snapped debe
superar netamente el 15,27% de F6. Si ninguna lo mueve, el corte por timestamp
queda refutado y la conclusion es que la paridad no se alcanza desde el parquet:
hace falta que NT8 exporte su perfil por barra. Eso ya no es una hipotesis mas,
es un pedido concreto de instrumentacion.

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
OUT = Path("/kaggle/working/avolcluster_tsgroup")


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










SNAPS = ("crudo", "extiende", "trunca")
LAGS = (0, -1)


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
    sess_end = np.concatenate((fs[1:], [n]))
    span = int(px.max() - px.min()) + 1
    base = int(px.min())
    ts_arr = np.array([x["ts"] for x in nt8], dtype=np.int64)

    # inicio de cada grupo de ticks con timestamp identico
    gstart = np.flatnonzero(np.concatenate(([True], ts_ns[1:] != ts_ns[:-1])))
    frac_same = 1.0 - len(gstart) / n
    print("ticks=", n, "fraccion con timestamp repetido=", round(frac_same, 4), flush=True)

    def cuts_for(snap):
        """Indices de inicio de barra, por sesion, con el corte ajustado al grupo."""
        out = []
        for s0, s1 in zip(fs, sess_end):
            c = s0
            out.append(c)
            while True:
                c = c + TICKS_PER_BAR
                if c >= s1:
                    break
                if snap != "crudo":
                    g = int(np.searchsorted(gstart, c, side="right") - 1)
                    gs = int(gstart[g])
                    ge = int(gstart[g + 1]) if g + 1 < len(gstart) else n
                    if gs < c < ge:                      # el corte parte un grupo
                        c = ge if snap == "extiende" else gs
                    if c <= out[-1] or c >= s1:
                        break
                out.append(c)
        return np.array(sorted(set(int(x) for x in out)), dtype=np.int64)

    results = {}
    for snap in SNAPS:
        bstart = cuts_for(snap)
        nb = len(bstart)
        bidx = np.repeat(np.arange(nb, dtype=np.int64),
                         np.diff(np.concatenate((bstart, [n]))))
        bend = ts_ns[np.concatenate((bstart[1:] - 1, [n - 1]))]
        low = np.full(nb, np.iinfo(np.int64).max, np.int64)
        high = np.full(nb, np.iinfo(np.int64).min, np.int64)
        np.minimum.at(low, bidx, px)
        np.maximum.at(high, bidx, px)
        pos = np.searchsorted(bend, ts_arr)
        print(snap, "barras=", nb, "t=", round(time.time() - t0, 1), flush=True)

        for lag in LAGS:
            if lag == 0:
                assign = bidx
            else:
                k = -lag
                assign = np.concatenate((bidx[k:], np.repeat(bidx[-1], k)))
            for use_filter in (False, True):
                keep = ((px >= low[assign]) & (px <= high[assign])) if use_filter \
                    else np.ones(n, bool)
                key = assign[keep] * span + (px[keep] - base)
                o = np.argsort(key, kind="stable")
                ks, vs = key[o], vol[keep][o]
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
                name = "%s_L%d_%s" % (snap, lag, "filtro" if use_filter else "sinfiltro")
                results[name] = {"barras": int(nb), "matched": matched, "exact_cells": ex,
                                 "exact_cells_pct": round(ex / matched, 6) if matched else None,
                                 "exact_volume": exv, "sum_abs_diff": round(sad, 1),
                                 "nt8_over_py_volume": round(nv / pv, 6) if pv else None}
                print(name, results[name], "t=", round(time.time() - t0, 1), flush=True)

    best = max(results, key=lambda z: results[z]["exact_cells"])
    report = {
        "schema": "avolclusterpoi_ts_group_boundary_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "code_commit": commit, "nt8_csv_sha256": sha256(csv_path),
        "fraccion_ticks_con_timestamp_repetido": round(frac_same, 6),
        "referencia_F6_mejor_conocido": {"variante": "p0_L-1_filtro", "exact_cells_pct": 0.152664},
        "best_variant": best, "best": results[best],
        "variants": results,
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tsgroup_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
