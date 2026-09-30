#!/usr/bin/env python3
r"""Eventos de espejo para la calibración A CIEGAS «¿hay picos acumulados antes de A?» (idea de Nico, 30/09).

    python tools/blind_espejo_eventos.py --asset ES_03-26_202601_25T_HFT --n 80

Velas 100t (4 × 25t dentro de cada sesión) y kernel ESPEJO-IND nivel N3 del visor (min_w 17 ticks, 20 velas). Por cada
espejo completado (el precio vuelve a A) se exporta SÓLO el pasado: desde 150 velas antes de A hasta la vela en que se
completa el espejo (momento de decidir). El futuro no sale del archivo. Muestra aleatoria con semilla, entre sesiones.
Salida: viewer/nt8_bridge/bundles/blind/espejo_<asset>.json  (la página blind_espejo.html la muestra).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from edgelab.bridge.indicators import espejo_impulsos as K  # noqa: E402

VIEW = REPO / "viewer" / "nt8_bridge"
M, PRE, SEED = 4, 150, 20260930


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--asset", required=True); ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--min-w", type=float, default=17); ap.add_argument("--max-bars", type=int, default=20); a = ap.parse_args()
    b = json.loads((VIEW / "bundles" / f"{a.asset}.json").read_text(encoding="utf-8"))
    c = b["bar_series"]["tick_25"]["candles"]; tick = float(b["meta"]["tick_size"]); del b
    man = json.loads((VIEW / "bundles" / f"{a.asset}.manifest.json").read_text(encoding="utf-8"))
    ses = np.concatenate([np.full(int(s["tick25_bars"]), str(s["trade_date"])) for s in man["sessions"]])
    assert len(ses) == len(c)
    T, O, H, L, C, V, S = [], [], [], [], [], [], []
    for sid in dict.fromkeys(ses):
        idx = np.flatnonzero(ses == sid)
        for j in range(0, len(idx) - len(idx) % M, M):
            g = [c[i] for i in idx[j:j + M]]
            T.append(g[-1]["time"]); O.append(g[0]["open"]); H.append(max(x["high"] for x in g)); L.append(min(x["low"] for x in g))
            C.append(g[-1]["close"]); V.append(sum(x.get("volume", 0) for x in g)); S.append(sid)
    T, O, H, L, C, V, S = (np.array(x) for x in (T, O, H, L, C, V, S))
    res = K.run(T, O / tick, H / tick, L / tick, C / tick, V, S, params=dict(e_max=1.01, atr_k=None, min_w=a.min_w, max_bars=a.max_bars))
    imps = {im["imp_id"]: im for im in res["impulses"]}
    comp = [e for e in res["events"] if e["kind"] == "MIRROR_COMPLETED"]
    rng = np.random.default_rng(SEED)
    pick = sorted(rng.choice(len(comp), min(a.n, len(comp)), replace=False))
    out = []
    for n_, i in enumerate(pick):
        e = comp[i]; im = imps[e["imp_id"]]; cut = int(e["bar"]); a_bar = int(im["bar_A"])
        s0 = a_bar - PRE
        while s0 < 0 or S[s0] != S[cut]:
            s0 += 1
        rng_i = range(s0, cut + 1)
        out.append(dict(id=f"E{n_ + 1:03d}", sesion=str(S[cut]), dir=int(im["dir"]), A=float(im["A"] * tick), B=float(im["B"] * tick),
                        iA=a_bar - s0, iB=int(im["bar_B"]) - s0, iCorte=cut - s0,
                        velas=[[float(T[k]), float(O[k]), float(H[k]), float(L[k]), float(C[k])] for k in rng_i]))
    o = VIEW / "bundles" / "blind"; o.mkdir(parents=True, exist_ok=True)
    (o / f"espejo_{a.asset}.json").write_text(json.dumps(dict(asset=a.asset, tick=tick, velas="100t", nivel="N3 (min_w 17, 20 velas)",
                                                            total_espejos=len(comp), eventos=out), separators=(",", ":")), encoding="utf-8")
    print("espejos completados", len(comp), "muestra", len(out))


if __name__ == "__main__":
    main()
