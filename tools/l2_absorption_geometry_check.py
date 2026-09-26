#!/usr/bin/env python3
r"""Chequeo de construcción de SUG-ABS-BARRIER antes de gastar la partición reservada (2026-09-24).

El atlas (`tools/l2_atlas_absorption.py`) comparó la ruptura del nivel absorbido contra un control cuyo nivel es el
mejor ask/bid EN EL MOMENTO DEL CONTROL (distancia 0 al toque). El nivel absorbido, al cierre de la ventana, puede
estar lejos del toque (el precio se alejó dentro de la ventana). Si es así, "se rompe menos" puede ser solo "está
más lejos" — la trampa de F2.8 (BigTrap2). Esta herramienta:

1. mide la distancia del nivel absorbido al toque en t0 (eventos) — dato target-free;
2. repite el perfil de ruptura con DOS controles: el del atlas (toque) y uno con la MISMA DISTANCIA al toque que el
   evento (geometría emparejada), que es lo que la regla 5 del atlas pedía y el código no hacía;
3. publica las diferencias por sesión (para potencia/split).

SOLO lee sesiones de la partición EXPLORATION declarada en el Brain; la reservada se rechaza por código.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from edgelab.edge_brain.hippocampus_store import DurableHippocampus  # noqa: E402
from edgelab.research.l2_manipulation_heuristics import ASK  # noqa: E402
from edgelab.research.l2_phase0 import defect_reasons, process_session  # noqa: E402
from tools.l2_atlas_absorption import (CTRL_SPAN_S, EXCL_S, HORIZONS, LAT, N_CTRL, US, boot_ci,  # noqa: E402
                                       quotes_trades_absorption, response)

BASE = Path(r"E:\DatosNT8\gc_aug26_canonical_parquets")
LEDGER = REPO / "artifacts" / "hippocampus" / "atlas_l2_20260924.jsonl"
SEED = 20260925


def load(s):
    l1 = pq.read_table(BASE / "l1_quotes" / f"{s}.parquet", columns=["side", "price_tick", "size", "ts_us", "source_row"]).to_pandas()
    l2 = pq.read_table(BASE / "l2_depth" / f"{s}.parquet", columns=["side", "operation", "level", "price_tick", "size", "ts_us", "source_row"]).to_pandas()
    return l1.sort_values("source_row", kind="stable"), l2.sort_values("source_row", kind="stable")


def touch(Q, t, dirn):
    j = np.searchsorted(Q["ts"], t, side="right") - 1
    if j < 0:
        return None
    return int(Q["ask"][j]) if dirn == -1 else int(Q["bid"][j])


def dist_to_touch(level, tch, dirn):
    """Ticks del nivel al toque, positivo = el nivel está MÁS ALLÁ del toque (hay que recorrerlo para romper)."""
    return (level - tch) if dirn == -1 else (tch - level)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--partition", default="P-GC0826-EXP")
    ap.add_argument("--out", type=Path, default=REPO / "artifacts" / "l2_atlas" / "barrier_geometry_check_GC_08-26.json")
    a = ap.parse_args(argv)
    brain = DurableHippocampus(LEDGER)
    part = brain.partitions.get(a.partition)
    if part is None or part["role"] != "EXPLORATION":
        raise SystemExit(f"refusing: {a.partition} is not a declared EXPLORATION partition")
    rng = np.random.default_rng(SEED)
    per_session, dist_ev = [], []
    for s in part["sessions"]:
        l1, l2 = load(s)
        res = process_session(l2, l1)
        if defect_reasons(res.qa):
            continue
        Q, T, ev = quotes_trades_absorption(l1)
        last = int(Q["ts"][-1]); evt = np.array([e["available_ts_us"] for e in ev])
        acc = {k: {h: [] for h in HORIZONS} for k in ("event", "ctrl_touch", "ctrl_dist")}
        for e in ev:
            dirn = -1 if e["side"] == ASK else 1
            t0 = e["available_ts_us"] + LAT
            tch = touch(Q, t0, dirn)
            if tch is None:
                continue
            dist = dist_to_touch(e["tick"], tch, dirn)
            r = response(Q, T, t0, dirn, e["tick"], last)
            if r is None:
                continue
            dist_ev.append(dist)
            for h in HORIZONS:
                acc["event"][h].append(r[f"break{h}"])
            got = {"ctrl_touch": 0, "ctrl_dist": 0}
            for _try in range(50 * N_CTRL):
                if min(got.values()) >= N_CTRL:
                    break
                tc = int(t0 + rng.integers(-CTRL_SPAN_S, CTRL_SPAN_S) * US)
                if np.min(np.abs(evt - tc)) < EXCL_S * US:
                    continue
                tt = touch(Q, tc, dirn)
                if tt is None:
                    continue
                for kind, lvl in (("ctrl_touch", tt), ("ctrl_dist", tt + dist if dirn == -1 else tt - dist)):
                    if got[kind] >= N_CTRL:
                        continue
                    rc = response(Q, T, tc, dirn, lvl, last)
                    if rc is None:
                        continue
                    got[kind] += 1
                    for h in HORIZONS:
                        acc[kind][h].append(rc[f"break{h}"])
        row = dict(session=s, n_events=len(acc["event"][HORIZONS[0]]))
        for h in HORIZONS:
            me = float(np.mean(acc["event"][h])) if acc["event"][h] else np.nan
            for kind in ("ctrl_touch", "ctrl_dist"):
                mc = float(np.mean(acc[kind][h])) if acc[kind][h] else np.nan
                row[f"diff_{kind}_{h}"] = me - mc
            row[f"event_{h}"] = me
            row[f"ctrl_dist_{h}"] = float(np.mean(acc["ctrl_dist"][h])) if acc["ctrl_dist"][h] else np.nan
            row[f"ctrl_touch_{h}"] = float(np.mean(acc["ctrl_touch"][h])) if acc["ctrl_touch"][h] else np.nan
        per_session.append(row)
        print(json.dumps(dict(session=s, events=row["n_events"])), flush=True)
    d = np.array(dist_ev)
    summary = dict(distance_to_touch_ticks=dict(p10=float(np.percentile(d, 10)), p25=float(np.percentile(d, 25)),
                                                p50=float(np.percentile(d, 50)), p75=float(np.percentile(d, 75)),
                                                p90=float(np.percentile(d, 90)), share_zero=float((d == 0).mean()),
                                                share_positive=float((d > 0).mean()), share_negative=float((d < 0).mean())),
                   break_diff={})
    for h in HORIZONS:
        summary["break_diff"][str(h)] = {k: dict(ci=boot_ci([r[f"diff_{k}_{h}"] for r in per_session]),
                                                  sd_between_sessions=float(np.nanstd([r[f"diff_{k}_{h}"] for r in per_session], ddof=1)))
                                         for k in ("ctrl_touch", "ctrl_dist")}
    body = dict(schema="EDGELAB_ATLAS_GEOMETRY_CHECK_V1", partition=a.partition, sessions=len(per_session),
                note="nivel del control: 'touch' = mejor precio del lado (atlas); 'dist' = misma distancia al toque que el evento",
                summary=summary, per_session=per_session)
    raw = json.dumps(body, indent=1, default=float)
    a.out.write_text(raw, encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print("sha256", hashlib.sha256(raw.encode()).hexdigest()[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
