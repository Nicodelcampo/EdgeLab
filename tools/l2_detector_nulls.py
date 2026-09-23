#!/usr/bin/env python3
r"""Plan L2 0.6: ¿los detectores provisionales (iceberg, spoof, absorcion) superan a su nulo? TARGET-FREE.

Cada detector se corre con la MISMA configuracion que el visor (`tools/build_l2_viewer_bundle.py`) sobre la sesion real
y sobre versiones nulas que destruyen exactamente el vinculo que el detector dice medir:

- ICEBERG y SPOOF dependen de que un trade toque el nivel en el momento justo. Nulo: trades DESPLAZADOS en el tiempo
  (circular dentro de la sesion, 120..1800 s), mismo libro. Si la cuenta nula ~= la real, el detector mide dinamica
  del libro, no consumo por trades.
- ABSORCION depende de que el volumen grande coincida con el precio que aguanta. Nulo: TAMAÑOS de trade permutados
  dentro de la sesion (precios y tiempos intactos).

Real y nulo usan el mismo orden de eventos (por ts_us; empates: trades antes que el libro del mismo instante) y la
misma distancia al toque, asi la comparacion es justa. Solo sesiones pre-holdout. No mira retornos.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from edgelab.research.holdout_guard import HOLDOUT_START_ISO  # noqa: E402
from edgelab.research.l2_manipulation_heuristics import (AbsorptionTracker, IcebergTracker,  # noqa: E402
                                                        SpoofTracker, large_size_thresholds)
from edgelab.research.l2_phase0 import apply_event  # noqa: E402
from tools.build_l2_viewer_bundle import (DEFAULT_ICEBERG_KWARGS, DEFAULT_LARGE_SIZE_PCTL,  # noqa: E402
                                          DEFAULT_SPOOF_KWARGS, ICEBERG_MIN_AVG_SIZE_PCTL)

HOLDOUT_YMD = int(HOLDOUT_START_ISO[:10].replace("-", ""))
ASK, BID = 0, 1


def _aggressor(tick, bid, ask):
    if ask is not None and tick >= ask:
        return 1
    if bid is not None and tick <= bid:
        return -1
    return 0


def run(l2, trades, *, detectors=("ice", "spoof")) -> dict:
    """`trades`: dict ts, tick, size (ya desplazados/permutados si es nulo). Devuelve conteos de candidatos."""
    side = l2["side"]; op = l2["operation"]; size = l2["size"].astype(float)
    thr = large_size_thresholds(side, op, size, DEFAULT_LARGE_SIZE_PCTL)
    ice = IcebergTracker(**dict(DEFAULT_ICEBERG_KWARGS,
                                min_avg_size=large_size_thresholds(side, op, size, ICEBERG_MIN_AVG_SIZE_PCTL)))
    spf = SpoofTracker(thr, **DEFAULT_SPOOF_KWARGS)
    ab = AbsorptionTracker()
    # merge por tiempo: trades (clave 0) antes que eventos de libro (clave 1) del mismo microsegundo
    ts = np.concatenate([trades["ts"], l2["ts_us"]])
    kind = np.concatenate([np.zeros(len(trades["ts"]), np.int8), np.ones(len(l2["ts_us"]), np.int8)])
    idx = np.concatenate([np.arange(len(trades["ts"])), np.arange(len(l2["ts_us"]))])
    order = np.lexsort((kind, ts))
    asks, bids = [], []
    tk2, lv2 = l2["price_tick"], l2["level"]
    for o in order:
        i = int(idx[o])
        if kind[o] == 0:
            t, tick, sz = int(trades["ts"][i]), int(trades["tick"][i]), float(trades["size"][i])
            d = _aggressor(tick, bids[0][0] if bids else None, asks[0][0] if asks else None)
            if "ice" in detectors: ice.on_trade(tick, t, sz, d)
            if "spoof" in detectors: spf.on_trade(tick, t, sz, d)
            if "abs" in detectors: ab.on_trade(tick, t, sz, d)
            continue
        s, tick = int(side[i]), int(tk2[i])
        book = asks if s == ASK else bids
        apply_event(book, int(op[i]), int(lv2[i]), tick, int(size[i]))
        best = book[0][0] if book else tick
        depth = abs(tick - best)
        t = int(l2["ts_us"][i])
        if "ice" in detectors: ice.on_l2_event(s, int(op[i]), tick, float(size[i]), t, depth)
        if "spoof" in detectors: spf.on_l2_event(s, int(op[i]), tick, float(size[i]), t, depth)
    out = {}
    if "ice" in detectors: out["iceberg"] = len(ice.candidates())
    if "spoof" in detectors: out["spoof"] = len(spf.candidates())
    if "abs" in detectors: out["absorption"] = len(ab.candidates())
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--sessions", nargs="+", required=True)
    ap.add_argument("--shifts", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260923)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    rng = np.random.default_rng(a.seed)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "a", encoding="utf-8") as f:
        for s in a.sessions:
            if int(s) >= HOLDOUT_YMD:
                continue
            t2 = pq.read_table(a.base / "l2_depth" / f"{s}.parquet",
                               columns=["side", "operation", "level", "price_tick", "size", "ts_us", "source_row"]).to_pandas()
            t2 = t2.sort_values("source_row", kind="stable")
            l2 = {c: t2[c].to_numpy() for c in t2.columns}
            t1 = pq.read_table(a.base / "l1_quotes" / f"{s}.parquet",
                               columns=["side", "price_tick", "size", "ts_us", "source_row"]).to_pandas()
            t1 = t1[t1.side == 2].sort_values("source_row", kind="stable")
            tr = dict(ts=t1.ts_us.to_numpy(np.int64), tick=t1.price_tick.to_numpy(), size=t1["size"].to_numpy())
            lo, hi = int(l2["ts_us"].min()), int(l2["ts_us"].max())
            span = hi - lo
            rec = dict(session=s, real=run(l2, tr, detectors=("ice", "spoof", "abs")), null_shift=[], null_permute=[])
            for _ in range(a.shifts):
                d = int(rng.integers(120, 1800)) * 1_000_000
                sh = dict(tr, ts=lo + (tr["ts"] - lo + d) % span)
                rec["null_shift"].append(dict(shift_s=d // 1_000_000, **run(l2, sh, detectors=("ice", "spoof"))))
                pm = dict(tr, size=rng.permutation(tr["size"]))
                rec["null_permute"].append(run(l2, pm, detectors=("abs",)))
            f.write(json.dumps(rec) + "\n"); f.flush()
            print(json.dumps(rec), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
