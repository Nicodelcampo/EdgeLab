#!/usr/bin/env python3
"""FASE 1-2: la paridad de aVolClusterPOI, atacada por ALINEACION DE BARRAS.

Estado previo: el cruce completo mostro que solo 16 de 22.200 bloques tienen
celdas identicas, que el 82% tiene ruido de valor y que hay 9.479 celdas que
NT8 tiene y Python no. Esa ultima cifra NO la explica el filtro Low/High, que
solo puede QUITAR celdas del lado NT8.

HIPOTESIS DOMINANTE: las barras de 120 ticks estan DESALINEADAS entre NT8 y
Python. Si el bloque de Python cubre las barras 10-19 y el de NT8 cubre 11-20,
las celdas difieren masivamente aunque el timestamp de cierre quede a menos de
2 s -- que es la tolerancia con la que se emparejo antes. Eso explicaria a la
vez el ruido de valor generalizado, las celdas en ambos sentidos y que casi
ningun bloque coincida, sin necesidad de ningun bug de logica.

QUE HACE:
  A. Empareja por `bar_index` del CSV de NT8, no por timestamp: el CSV trae el
     indice de barra exacto y los saltos entre bloques son 10 en 22.460 de
     22.506 casos, asi que el particionado de NT8 es limpio y direccionable.
  B. Para cada bloque prueba un rango de OFFSETS de barra y elige el que
     minimiza la diferencia de celdas. Si existe un offset dominante, la
     desalineacion es la causa y queda identificada.
  C. Mide tambien la alineacion por VOLUMEN TOTAL de bloque, que es
     independiente de la distribucion por precio y por lo tanto un test
     limpio de "estas mirando las mismas barras".

No modifica el .cs ni el kernel Python. Target-free.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "484c5e7b5f175151a64efec8aba16a440f0173a5"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
DIAG_CSV = "data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv"
ART_TO_UTC_NS = 3 * 3600 * 10**9
TICKS_PER_BAR = 120
WINDOW_BARS = 10
OFFSETS = list(range(-6, 7))          # desfases de barra a probar
SAMPLE_BLOCKS = 4000                  # muestra para el barrido de offsets
OUT = Path("/kaggle/working/avolcluster_alignment")


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
    subprocess.run(["git", "checkout", "-B", "align", commit], cwd=REPO_DIR, check=True)
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

    # ---------- NT8 ----------
    csv_path = REPO_DIR / DIAG_CSV
    with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = [l for l in f if not l.startswith("# meta")]
    nt8 = []
    for r in csv.DictReader(lines):
        try:
            ts = parse_iso_ns(r["bar_close_time"]) + ART_TO_UTC_NS
        except ValueError:
            continue
        nt8.append({
            "bar_index": int(r["bar_index"]), "ts": ts,
            "session_index": int(r["session_index"]),
            "n_cells": int(r["n_cells"]),
            "cells": parse_cells(r.get("cells")),
        })
    for x in nt8:
        x["block_volume"] = sum(x["cells"].values())
    print("NT8 bloques=", len(nt8), "t=", round(time.time() - t0, 1), flush=True)
    lo_ns = min(x["ts"] for x in nt8)
    hi_ns = max(x["ts"] for x in nt8)

    # ---------- Python: barras sobre la ventana del oraculo ----------
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
    print("ticks=", len(t.ts_ns), "bars=", nb, "t=", round(time.time() - t0, 1), flush=True)

    # footprint por barra, vectorizado (nada de loops de 33M)
    px = t.price_ticks.astype(np.int64)
    vol = t.volume.astype(np.float64)
    bidx = bars.tick_bar_idx.astype(np.int64)
    span = int(px.max() - px.min()) + 1
    base = int(px.min())
    key = bidx * span + (px - base)
    order = np.argsort(key, kind="stable")
    ks = key[order]
    vs = vol[order]
    edges = np.flatnonzero(np.concatenate(([True], ks[1:] != ks[:-1])))
    sums = np.add.reduceat(vs, edges)
    uk = ks[edges]
    ub = (uk // span).astype(np.int64)
    up = (uk % span + base).astype(np.int64)
    bar_start = np.searchsorted(ub, np.arange(nb), side="left")
    bar_end = np.searchsorted(ub, np.arange(nb), side="right")
    bar_volume = np.zeros(nb)
    np.add.at(bar_volume, ub, sums)
    print("footprint vectorizado listo t=", round(time.time() - t0, 1), flush=True)

    def block_cells(first_bar):
        out = {}
        if first_bar < 0 or first_bar + WINDOW_BARS > nb:
            return out
        for b in range(first_bar, first_bar + WINDOW_BARS):
            s, e = bar_start[b], bar_end[b]
            for j in range(s, e):
                k = int(up[j])
                out[k] = out.get(k, 0.0) + float(sums[j])
        return out

    # ---------- A: alineacion por timestamp de cierre de barra ----------
    # se mapea cada bloque NT8 a la barra de Python cuyo end_ns esta mas cerca
    end_ns = bars.end_ns
    ts_arr = np.array([x["ts"] for x in nt8], dtype=np.int64)
    pos = np.searchsorted(end_ns, ts_arr)
    mapped, dt_ns = [], []
    for i, p in enumerate(pos):
        best, bd = None, None
        for k in (p - 1, p, p + 1):
            if 0 <= k < nb:
                d = abs(int(end_ns[k]) - int(ts_arr[i]))
                if bd is None or d < bd:
                    bd, best = d, k
        mapped.append(best if best is not None else -1)
        dt_ns.append(bd if bd is not None else -1)
    mapped = np.array(mapped)
    dt_ns = np.array(dt_ns, dtype=np.int64)
    ok = mapped >= 0
    print("mapeo por ts: |dt| p50 =", int(np.median(dt_ns[ok])),
          "ns, <1s:", int((dt_ns[ok] < 10**9).sum()), "/", int(ok.sum()), flush=True)

    # ---------- B: barrido de offsets sobre una muestra ----------
    step = max(1, len(nt8) // SAMPLE_BLOCKS)
    sample = list(range(0, len(nt8), step))
    off_best = Counter()
    off_score = {o: 0 for o in OFFSETS}
    exact_by_off = {o: 0 for o in OFFSETS}
    vol_exact_by_off = {o: 0 for o in OFFSETS}
    evaluated = 0
    for i in sample:
        if not ok[i]:
            continue
        nc = nt8[i]["cells"]
        nvol = nt8[i]["block_volume"]
        end_bar = int(mapped[i])
        best_o, best_diff = None, None
        for o in OFFSETS:
            first = end_bar - WINDOW_BARS + 1 + o
            pc = block_cells(first)
            if not pc:
                continue
            keys = set(pc) | set(nc)
            diff = sum(abs(pc.get(k, 0.0) - nc.get(k, 0.0)) for k in keys)
            off_score[o] += diff
            if diff == 0:
                exact_by_off[o] += 1
            if abs(sum(pc.values()) - nvol) < 1e-9:
                vol_exact_by_off[o] += 1
            if best_diff is None or diff < best_diff:
                best_diff, best_o = diff, o
        if best_o is not None:
            off_best[best_o] += 1
            evaluated += 1
    print("offsets evaluados sobre", evaluated, "bloques t=", round(time.time() - t0, 1), flush=True)
    for o in OFFSETS:
        print(f"  offset {o:+d}: mejor_en={off_best.get(o,0):5d} "
              f"celdas_exactas={exact_by_off[o]:5d} volumen_exacto={vol_exact_by_off[o]:5d} "
              f"suma_abs_diff={off_score[o]:.0f}", flush=True)

    dominant = off_best.most_common(1)[0] if off_best else (None, 0)
    report = {
        "schema": "avolclusterpoi_alignment_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "hypothesis": "las barras de 120 ticks estan desalineadas entre NT8 y Python",
        "code_commit": commit, "nt8_csv_sha256": sha256(csv_path),
        "n_nt8_blocks": len(nt8), "n_python_bars": int(nb),
        "n_evaluated": evaluated, "offsets_tested": OFFSETS,
        "ts_mapping": {"median_abs_dt_ns": int(np.median(dt_ns[ok])),
                       "under_1s": int((dt_ns[ok] < 10**9).sum()),
                       "mapped": int(ok.sum())},
        "best_offset_histogram": {str(k): v for k, v in sorted(off_best.items())},
        "cells_exact_by_offset": {str(k): v for k, v in exact_by_off.items()},
        "volume_exact_by_offset": {str(k): v for k, v in vol_exact_by_off.items()},
        "sum_abs_diff_by_offset": {str(k): round(v, 3) for k, v in off_score.items()},
        "dominant_offset": dominant[0], "dominant_share":
            round(dominant[1] / evaluated, 6) if evaluated else None,
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "alignment_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
