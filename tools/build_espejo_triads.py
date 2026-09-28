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

ASSET = "ES_03-26_202602_25T_HFT"
VIEW = REPO / "viewer" / "nt8_bridge"
TICK = 0.25
SEED = 20260928
N_TBZ, N_OTROS, LOOK = 60, 40, 30


def main():
    b = json.loads((VIEW / "bundles" / f"{ASSET}.json").read_text(encoding="utf-8"))
    c = b["bar_series"]["tick_25"]["candles"]
    t = np.array([x["time"] for x in c], float)
    O, H, L, C = (np.array([x[k] / TICK for x in c]) for k in ("open", "high", "low", "close"))
    V = np.array([x["volume"] for x in c], float)
    ses = np.cumsum(np.r_[0, np.diff(t) > 1800]).astype(str)
    res = K.run(t, O, H, L, C, V, ses, params=dict(e_max=1.01))
    ev50 = {}
    for e in res["events"]:
        if e["kind"] in ("MIRROR_CANDIDATE", "MIRROR_PROGRESS") and e.get("x") == 0.5:
            ev50[e["imp_id"]] = e
    pool = []
    for im in res["impulses"]:
        e = ev50.get(im["imp_id"])
        if e is None:
            continue
        pool.append(dict(im=im, e=e, tbz=bool(im["eff"] >= 0.6), vel=(im["bar_B"] - im["bar_A"] + 1)))
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
        im, e = p["im"], p["e"]
        lo = max(0, im["bar_A"] - LOOK); hi = e["bar"]                       # termina donde la vuelta cruza el 50 %
        candles = [dict(time=i - lo, open=float(O[i]), high=float(H[i]), low=float(L[i]), close=float(C[i])) for i in range(lo, hi + 1)]
        items.append(dict(id=j, candles=candles, A=float(im["A"]), B=float(im["B"]), iA=int(im["bar_A"] - lo),
                          iB=int(im["bar_B"] - lo), dir=int(im["dir"])))
        meta.append(dict(id=j, imp_id=im["imp_id"], estrato="TBZ" if p["tbz"] else "otros", eff=im["eff"], velas_ida=p["vel"],
                         vol_por_tick=im["vol_por_tick"], W=im["W"], S=e.get("S"), sim_vel=e.get("sim_vel"),
                         sim_t=e.get("sim_t"), vel=e.get("vel"), forma=e.get("forma"), estado_final=im["estado_final"]))
    triads = [[3 * k, 3 * k + 1, 3 * k + 2] for k in range(n3 // 3)]
    out = dict(schema="EDGELAB_ESPEJO_TRIADS_V1", asset=ASSET, tick=TICK, items=items, triads=triads,
               nota="ciego: cada gráfico termina al 50 % de la vuelta; no incluye estrato ni desenlace")
    (VIEW / "bundles" / "espejo_triads_ES_202602.json").write_text(json.dumps(out, separators=(",", ":"), default=float), encoding="utf-8")
    d = REPO / "artifacts" / "espejo" / "triadas"; d.mkdir(parents=True, exist_ok=True)
    (d / "meta_ES_202602.json").write_text(json.dumps(dict(seed=SEED, params=res["params"], meta=meta,
                                                           censo=dict(impulsos=len(res["impulses"]), llegan_50=len(pool),
                                                                      tbz=len(tbz), otros=len(otros))), default=float, indent=1), encoding="utf-8")
    print(json.dumps(dict(impulsos=len(res["impulses"]), llegan_al_50=len(pool), tbz=len(tbz), otros=len(otros),
                          en_tandas=n3, tandas=len(triads))))


if __name__ == "__main__":
    main()
