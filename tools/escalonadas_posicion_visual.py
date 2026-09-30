#!/usr/bin/env python3
r"""Posición visual del visor (SL fijo en ticks, TP en R, BE en R) sobre las zonas escalonadas — exploración de Nico 30/09.

    python tools/escalonadas_posicion_visual.py --inst MNQ --mes 202602 --capa __precio --sl 5 --tp 10 --be 2 [--rt 3]

Tres cálculos de la MISMA regla, para ver qué se come qué:
  1. velas  — réplica exacta del tablero del visor (posCompute en index.html): entrada en det_precio, SL gana si la
              vela toca SL y TP, BE desde la vela siguiente a la que tocó el nivel, horizonte 1.500 velas.
  2. ticks sin costos — mismo orden real de los precios: entrada en det_precio en el primer tick que opera el nivel,
              salidas exactamente en los niveles.
  3. ticks con costos — entrada stop al bid/ask del tick que dispara, SL/BE stop al peor lado (bid/ask), TP límite con
              1 tick de penetración, + comisión ida y vuelta (--rt ticks).
No es un test: sin control ni corrección por multiplicidad. Es la cuenta de un caso elegido mirando el gráfico.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from numba import njit

REPO = Path(__file__).resolve().parents[1]
VIEW = REPO / "viewer" / "nt8_bridge"
TICK = 0.25
HZ = 1500


def load(inst, mes):
    b = json.loads((VIEW / "bundles" / f"{inst}_03-26_{mes}_25T_HFT.json").read_text(encoding="utf-8"))
    c = b["bar_series"]["tick_25"]["candles"]; del b
    man = json.loads((VIEW / "bundles" / f"{inst}_03-26_{mes}_25T_HFT.manifest.json").read_text(encoding="utf-8"))
    f = pq.ParquetFile(man["source_path"])
    P, B, A, bt, bs = [], [], [], [], []
    off = 0
    for si, s in enumerate(man["sessions"]):
        nb = int(s["tick25_bars"])
        rgs = [i for i in range(f.num_row_groups) if f.metadata.row_group(i).column(0).statistics.max >= s["start_utc_ns"]
               and f.metadata.row_group(i).column(0).statistics.min <= s["end_utc_ns"]]
        t = f.read_row_groups(rgs, columns=["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks"]).to_pandas()
        t = t[(t.ts_utc_ns >= s["start_utc_ns"]) & (t.ts_utc_ns <= s["end_utc_ns"])]
        assert (len(t) + 24) // 25 == nb or len(t) // 25 == nb, (s["trade_date"], len(t), nb)
        P.append(t.price_ticks.to_numpy(np.float64)); B.append(t.bid_ticks.to_numpy(np.float64)); A.append(t.ask_ticks.to_numpy(np.float64))
        bt.append(off + np.arange(nb) * 25); bs.append(np.full(nb, si)); off += len(t); del t
    D = dict(px=np.concatenate(P), bid=np.concatenate(B), ask=np.concatenate(A), bar_tick=np.concatenate(bt), bar_ses=np.concatenate(bs))
    assert len(D["bar_tick"]) == len(c)
    D.update(h=np.array([x["high"] for x in c]), l=np.array([x["low"] for x in c]), c=np.array([x["close"] for x in c]))
    k = np.random.default_rng(1).choice(len(c) - 2, 2000, replace=False)
    bad = sum(abs(D["px"][D["bar_tick"][i]:D["bar_tick"][i] + 25].max() * TICK - c[i]["high"]) > 1e-9 for i in k if D["bar_ses"][i] == D["bar_ses"][i + 1])
    assert bad == 0, f"{bad} velas no coinciden"
    return D


def velas(D, z, sl, tp, be):
    """Réplica de posCompute del visor."""
    sd = -1 if z["kind"] == "H" else 1; en = z["det_precio"]
    slP = en - sd * sl * TICK; tpP = en + sd * sl * tp * TICK; beP = en + sd * sl * be * TICK if be > 0 else None
    stp = slP; beOn = False; n = len(D["c"])
    for k in range(z["det_i"] + 1, min(n, z["det_i"] + HZ)):
        hS = D["h"][k] >= stp if sd == -1 else D["l"][k] <= stp
        hT = D["l"][k] <= tpP if sd == -1 else D["h"][k] >= tpP
        if hS:
            return 0.0 if beOn else -1.0, "BE" if beOn else "SL"
        if hT:
            return float(tp), "TP"
        if beP is not None and not beOn and (D["l"][k] <= beP if sd == -1 else D["h"][k] >= beP):
            beOn = True; stp = en
    ex = min(n - 1, z["det_i"] + HZ - 1)
    return (D["c"][ex] - en) * sd / (sl * TICK), "fin"


@njit(cache=True)
def ticks_sim(side, i0, i1, entry, sl, tp, be, px, bid, ask, costos):
    """Precios en ticks. costos=0: salidas en los niveles exactos. costos=1: SL/BE al peor lado, TP con 1 tick de penetración."""
    stp = entry - side * sl; tgt = entry + side * sl * tp; bel = entry + side * sl * be; on = False
    for i in range(i0, i1):
        p = px[i]
        if (side == 1 and p <= stp) or (side == -1 and p >= stp):
            if costos == 0:
                return (stp - entry) * side, 2 if on else -1
            return ((bid[i] - entry) if side == 1 else (entry - ask[i])), 2 if on else -1
        if costos == 0:
            if (side == 1 and p >= tgt) or (side == -1 and p <= tgt):
                return (tgt - entry) * side, 1
        else:
            if (side == 1 and p >= tgt + 1) or (side == -1 and p <= tgt - 1):
                return (tgt - entry) * side, 1
        if be > 0 and not on and ((side == 1 and p >= bel) or (side == -1 and p <= bel)):
            on = True; stp = entry
    j = i1 - 1
    if costos == 0:
        return (px[j] - entry) * side, 0
    return ((bid[j] - entry) if side == 1 else (entry - ask[j])), 0


def stats(R, why):
    R = np.array(R); n = len(R)
    eq = np.cumsum(R); dd = float(np.max(np.maximum.accumulate(eq) - eq)) if n else 0.0
    gp = R[R > 0].sum(); gl = -R[R < 0].sum()
    c = {k: int(sum(w == k for w in why)) for k in ("TP", "SL", "BE", "fin")}
    return dict(n=n, **c, ganadoras=round(float(np.mean(R > 0)), 3), R_total=round(float(R.sum()), 1),
                R_por_op=round(float(R.mean()), 3), profit_factor=round(float(gp / gl), 2) if gl else None, max_dd_R=round(dd, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inst", default="MNQ"); ap.add_argument("--mes", default="202602"); ap.add_argument("--capa", default="__precio")
    ap.add_argument("--sl", type=float, default=5); ap.add_argument("--tp", type=float, default=10); ap.add_argument("--be", type=float, default=2)
    ap.add_argument("--rt", type=float, default=3.0, help="comisión+fees ida y vuelta en ticks")
    a = ap.parse_args()
    D = load(a.inst, a.mes)
    Z = json.loads((VIEW / "bundles" / "peaks_det" / f"{a.inst}_03-26_{a.mes}_25T_HFT{a.capa}.json").read_text(encoding="utf-8"))["zonas"]
    Z = sorted([z for z in Z if z.get("det_i") is not None], key=lambda z: z["det_i"])
    nb = len(D["c"]); out = {}
    r1 = [velas(D, z, a.sl, a.tp, a.be) for z in Z]
    out["1_velas_como_el_visor"] = stats([r for r, _ in r1], [w for _, w in r1])
    names = {1: "TP", -1: "SL", 2: "BE", 0: "fin"}
    for costos, rt in ((0, 0.0), (1, a.rt)):
        R, W, spread_in = [], [], []
        for z in Z:
            side = -1 if z["kind"] == "H" else 1; k = z["det_i"]; lvl = z["det_precio"] / TICK
            a0 = D["bar_tick"][k]; fill = None
            for i in range(a0, min(a0 + 25, len(D["px"]))):
                if (side == -1 and D["px"][i] <= lvl) or (side == 1 and D["px"][i] >= lvl):
                    fill = i; break
            if fill is None:
                continue
            entry = lvl if costos == 0 else (D["bid"][fill] if side == -1 else D["ask"][fill])
            spread_in.append((lvl - entry) * side if side == -1 else (entry - lvl))
            kk = min(k + HZ, nb - 1)
            end = D["bar_tick"][kk] if D["bar_ses"][kk] == D["bar_ses"][k] else D["bar_tick"][np.searchsorted(D["bar_ses"], D["bar_ses"][k], side="right") - 1] + 25
            end = min(end, len(D["px"]))
            pnl, w = ticks_sim(side, fill + 1, end, entry, a.sl, a.tp, a.be, D["px"], D["bid"], D["ask"], costos)
            R.append((pnl - rt) / a.sl); W.append(names[int(w)])
        key = "2_ticks_sin_costos" if costos == 0 else f"3_ticks_con_costos_rt{a.rt:g}"
        out[key] = stats(R, W)
        if costos:
            out[key]["deslizamiento_entrada_medio_ticks"] = round(float(np.mean(spread_in)), 2)
    print(json.dumps(dict(config=vars(a), zonas=len(Z), **out), indent=1, ensure_ascii=False))
    o = REPO / "docs" / "research" / "es_escalonadas"; o.mkdir(parents=True, exist_ok=True)
    (o / f"posicion_visual_{a.inst}_{a.mes}_sl{a.sl:g}_tp{a.tp:g}_be{a.be:g}.json").write_text(json.dumps(dict(config=vars(a), **out), indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
