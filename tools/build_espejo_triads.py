#!/usr/bin/env python3
r"""Tandas de a tres espejos para que Nico los ORDENE por semejanza (target-free, a ciegas). Pedido de Nico, 28/09.

- Censo del kernel ESPEJO-IND sobre ES febrero 2026, velas de 25t, parámetros de investigación (e_min 0,3).
- Se muestran sólo impulsos confirmados cuya vuelta llegó al 50 % (así hay vuelta que comparar); cada gráfico termina en
  la vela en que la vuelta cruza el 50 %: lo que pasó después (si llegó a A o no) NO está en el archivo.
- Estratos: 60 «tipo TBZ» (eficiencia ≥ 0,6, config de Nico: 20 velas, 17 t, retroceso 0,3) y 40 del resto
  (eficiencia 0,3–0,6), mezclados por velocidad y volumen por tick. El visor no muestra el estrato.
- 33 tandas de 3, al azar con semilla fija. Estrato y métricas en artifacts/espejo/triadas/ (no lo lee el visor).

    .venv\Scripts\python tools\build_espejo_triads.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from edgelab.bridge.indicators import espejo_impulsos as K  # noqa: E402

ASSETS = ["ES_03-26_202601_25T_HFT", "ES_03-26_202602_25T_HFT", "ES_03-26_202603_25T_HFT"]   # ene–mar (descubrimiento)
ASSET = "ES_03-26_2026Q1"
VIEW = REPO / "viewer" / "nt8_bridge"
TICK = 0.25
SEED = 20260928
N_TBZ, N_OTROS, LOOK = 60, 40, 30
MULT = 4                     # 100t = 4 velas de 25t agrupadas dentro de la sesión (exacto: cada 25t tiene 25 ticks)
CUT_X = 0.75                 # el gráfico termina donde la vuelta cruza el 75 % (a 25t y 50 % casi no había vuelta: 28/09)
KPARAMS = dict(e_max=1.01, atr_k=None, min_w=34.0, max_bars=20)   # impulso ≥ 34 t (2 × los 17 t de Nico en 25t) en ≤ 20 velas; 3·ATR daba mediana 12 t
NAME = "espejo_triads_ES_2026Q1_100t"


def census(asset):
    b = json.loads((VIEW / "bundles" / f"{asset}.json").read_text(encoding="utf-8"))
    c = b["bar_series"]["tick_25"]["candles"]
    t0 = np.array([x["time"] for x in c], float)
    O0, H0, L0, C0 = (np.array([x[k] / TICK for x in c]) for k in ("open", "high", "low", "close"))
    V0 = np.array([x["volume"] for x in c], float)
    del b, c
    ses0 = np.cumsum(np.r_[0, np.diff(t0) > 1800])
    grp = np.zeros(len(t0), int); g = -1; prev = None; cnt = MULT
    for i in range(len(t0)):
        if ses0[i] != prev or cnt == MULT:
            g += 1; cnt = 0; prev = ses0[i]
        grp[i] = g; cnt += 1
    first = np.r_[0, np.flatnonzero(np.diff(grp)) + 1]; last = np.r_[first[1:] - 1, len(t0) - 1]
    t = t0[last]; O = O0[first]; C = C0[last]
    H = np.maximum.reduceat(H0, first); L = np.minimum.reduceat(L0, first); V = np.add.reduceat(V0, first)
    ses = ses0[first].astype(str)
    res = K.run(t, O, H, L, C, V, ses, params=KPARAMS)
    ev = {e["imp_id"]: e for e in res["events"] if e["kind"] in ("MIRROR_CANDIDATE", "MIRROR_PROGRESS") and e.get("x") == CUT_X}
    pool = [dict(im=im, e=ev[im["imp_id"]], tbz=bool(im["eff"] >= 0.6), vel=(im["bar_B"] - im["bar_A"] + 1), asset=asset, O=O, H=H, L=L, C=C)
            for im in res["impulses"] if im["imp_id"] in ev]
    return res, pool


def main():
    pool, n_imp, params = [], 0, None
    for a in ASSETS:
        res, p_ = census(a); pool += p_; n_imp += len(res["impulses"]); params = res["params"]
    res = dict(impulses=[None] * n_imp, params=params)
    rng = np.random.default_rng(SEED)
    tbz = [p for p in pool if p["tbz"]]; otros = [p for p in pool if not p["tbz"]]
    # los «otros» estratificados: 4 celdas (rápido/lento × poco/mucho volumen por tick), 10 de cada una
    if otros:
        vmed = np.median([p["vel"] for p in otros]); qmed = np.median([p["im"]["vol_por_tick"] for p in otros])
        cells = {}
        for p in otros:
            cells.setdefault((p["vel"] <= vmed, p["im"]["vol_por_tick"] <= qmed), []).append(p)
        sel_o = []
        for k_, v_ in sorted(cells.items()):
            sel_o += [v_[int(i)] for i in rng.permutation(len(v_))[:N_OTROS // 4]]
    else:
        sel_o = []
    sel = [tbz[int(i)] for i in rng.permutation(len(tbz))[:N_TBZ]] + sel_o
    rng.shuffle(sel)
    n3 = len(sel) // 3 * 3
    items, meta = [], []
    for j, p in enumerate(sel[:n3]):
        im, e = p["im"], p["e"]; O, H, L, C = p["O"], p["H"], p["L"], p["C"]
        lo = max(0, im["bar_A"] - LOOK); hi = e["bar"]                       # termina donde la vuelta cruza el 75 %
        candles = [dict(time=i - lo, open=float(O[i]), high=float(H[i]), low=float(L[i]), close=float(C[i])) for i in range(lo, hi + 1)]
        items.append(dict(id=j, candles=candles, A=float(im["A"]), B=float(im["B"]), iA=int(im["bar_A"] - lo),
                          iB=int(im["bar_B"] - lo), dir=int(im["dir"])))
        meta.append(dict(id=j, asset=p["asset"], imp_id=im["imp_id"], estrato="TBZ" if p["tbz"] else "otros", eff=im["eff"], velas_ida=p["vel"],
                         vol_por_tick=im["vol_por_tick"], W=im["W"], S=e.get("S"), sim_vel=e.get("sim_vel"),
                         sim_t=e.get("sim_t"), vel=e.get("vel"), forma=e.get("forma"), estado_final=im["estado_final"]))
    triads = [[3 * k, 3 * k + 1, 3 * k + 2] for k in range(n3 // 3)]
    out = dict(schema="EDGELAB_ESPEJO_TRIADS_V1", asset=ASSET, tick=TICK, velas="100t", corte=CUT_X, items=items, triads=triads,
               nota="ciego: cada gráfico termina al 75 % de la vuelta; no incluye estrato ni desenlace")
    (VIEW / "bundles" / f"{NAME}.json").write_text(json.dumps(out, separators=(",", ":"), default=float), encoding="utf-8")
    d = REPO / "artifacts" / "espejo" / "triadas"; d.mkdir(parents=True, exist_ok=True)
    (d / f"meta_{NAME}.json").write_text(json.dumps(dict(seed=SEED, params=res["params"], meta=meta,
                                                           censo=dict(impulsos=len(res["impulses"]), llegan_50=len(pool),
                                                                      tbz=len(tbz), otros=len(otros))), default=float, indent=1), encoding="utf-8")
    print(json.dumps(dict(impulsos=len(res["impulses"]), llegan_al_50=len(pool), tbz=len(tbz), otros=len(otros),
                          en_tandas=n3, tandas=len(triads))))


if __name__ == "__main__":
    main()
