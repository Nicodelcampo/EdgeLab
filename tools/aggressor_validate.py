#!/usr/bin/env python3
r"""Valida la columna `aggressor` de research-v2 contra el agresor por cotización del L2 (target-free).
Requisito de TBZ-E2 (§7 I6) y de TREND-MICRO (§7 T1). Solapamiento pre-holdout: NQ 09-26 del 25 al 30/06 y
ES 09-26 del 29 y 30/06.

Para cada día:
1. Trades del L2 (`nq_l2_explore.load_l1`: agresor = el precio contra la cotización vigente ANTES del trade).
   Hora de pared ART guardada como UTC.
2. Trades de research-v2 en la misma ventana (UTC real), leyendo sólo los row groups que caen en la ventana.
3. Desfase de reloj: se prueban desfases en pasos de 30 min y se elige el que más trades empareja (mismo precio y
   tamaño, a ≤ 50 ms).
4. Acuerdo de signo sobre los emparejados. Los trades del L2 sin agresor definido (a mitad de spread) se excluyen.

Umbral fijado en los manifiestos: acuerdo ≥ 90 %.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import nq_l2_explore as X  # noqa: E402

RV2 = Path(r"E:\EdgeLab\data\nt8_research_v2")
L2 = Path(r"E:\l2_parquet")
CASES = [("NQ", "NQ_09-26", RV2 / "NQ_parquet" / "NQ_09-26_ticks.parquet", d) for d in ("20260625", "20260626", "20260629", "20260630")] + \
        [("ES", "ES_09-26", RV2 / "ES_parquet" / "ES_09-26_ticks.parquet", d) for d in ("20260629", "20260630")]
TOL_US = 50_000
OUT = REPO / "artifacts" / "aggressor_validation.json"


def read_rv2(path, t0_ns, t1_ns):
    tbl = pq.read_table(path, columns=["ts_utc_ns", "price_ticks", "volume", "aggressor", "bid_ticks", "ask_ticks"],
                        filters=[("ts_utc_ns", ">=", int(t0_ns)), ("ts_utc_ns", "<", int(t1_ns))])
    df = tbl.to_pandas()
    df["rv2_aggr"] = df.aggressor.map({"buy": 1, "sell": -1}).fillna(0).astype(int)
    return df


def one(inst, base, rv2, day):
    X.BASE = L2 / base
    _, T = X.load_l1(day)
    T = T.sort_values("ts", kind="stable").reset_index(drop=True)
    lo, hi = int(T.ts.min()), int(T.ts.max())
    best = None
    for off_h in np.arange(-6, 6.5, 0.5):                     # L2 (pared ART como UTC) + off = UTC real
        off = int(off_h * 3600e6)
        R = read_rv2(rv2, (lo + off) * 1000, (lo + off + 3600e6) * 1000)   # 1 h de prueba
        if len(R) < 100:
            continue
        a = T[(T.ts >= lo) & (T.ts < lo + 3600e6)].copy()
        a["ts_u"] = a.ts + off
        R["ts_u"] = R.ts_utc_ns // 1000
        m = pd.merge_asof(a.sort_values("ts_u"), R.sort_values("ts_u")[["ts_u", "price_ticks", "volume", "rv2_aggr"]],
                          on="ts_u", direction="nearest", tolerance=TOL_US)
        hit = float(((m.price_ticks == m.px) & (m.volume == m.sz)).mean())
        if best is None or hit > best[1]:
            best = (off, hit)
    if best is None:
        return dict(inst=inst, day=day, status="SIN_SOLAPAMIENTO")
    off, _ = best
    R = read_rv2(rv2, (lo + off) * 1000, (hi + off + 1) * 1000)
    R["ts_u"] = R.ts_utc_ns // 1000
    a = T.copy(); a["ts_u"] = a.ts + off
    m = pd.merge_asof(a.sort_values("ts_u"), R.sort_values("ts_u")[["ts_u", "price_ticks", "volume", "rv2_aggr"]],
                      on="ts_u", direction="nearest", tolerance=TOL_US)
    ok = (m.price_ticks == m.px) & (m.volume == m.sz)
    mm = m[ok & (m.aggr != 0)]
    agree = float((mm["rv2_aggr"] == mm["aggr"]).mean()) if len(mm) else None
    return dict(inst=inst, day=day, offset_h=off / 3600e6, trades_l2=int(len(T)), emparejados=int(ok.sum()),
                frac_emparejados=float(ok.mean()), con_agresor_l2=int(len(mm)), acuerdo=agree,
                rv2_sin_agresor=float((m.loc[ok, "rv2_aggr"] == 0).mean()) if ok.any() else None,
                l2_mitad_spread=float((m.loc[ok, "aggr"] == 0).mean()) if ok.any() else None)


def main():
    res = [one(*c) for c in CASES]
    tot = {}
    for inst in ("NQ", "ES"):
        rs = [r for r in res if r["inst"] == inst and r.get("acuerdo") is not None]
        n = sum(r["con_agresor_l2"] for r in rs)
        tot[inst] = dict(dias=len(rs), n=n, acuerdo=(sum(r["acuerdo"] * r["con_agresor_l2"] for r in rs) / n) if n else None)
    verdict = {k: ("PASA" if v["acuerdo"] is not None and v["acuerdo"] >= 0.90 else "NO_PASA") for k, v in tot.items()}
    body = dict(schema="EDGELAB_AGGRESSOR_VALIDATION_V1", umbral=0.90, por_dia=res, total=tot, veredicto=verdict,
                code_commit=X._git("rev-parse", "HEAD"))
    OUT.write_text(json.dumps(body, indent=1, default=float), encoding="utf-8")
    print(json.dumps(dict(total=tot, veredicto=verdict), indent=1, default=float))
    for r in res:
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


if __name__ == "__main__":
    main()
