#!/usr/bin/env python3
r"""Exploración pedida por Nico (30/09): ¿los espejos que juzgó «con picos» antes de A tienen ventaja sobre los «sin picos»?

    python tools/blind_espejo_outcomes.py --asset ES_03-26_202601_25T_HFT

Recalcula exactamente los mismos 80 espejos que `blind_espejo_eventos.py` (misma semilla) para ubicar la vela de
decisión en los ticks. Operación: en el cierre de la vela 100t en que el precio vuelve a A, a mercado (bid/ask), en la
dirección de la vuelta (más allá de A, hacia donde estarían los picos). Grilla acotada: SL 0,5 W / 1 W × TP 1R / 2R.
Horizonte 150 velas 100t o fin de sesión; comisión ES 0,40 ticks. EXPLORATORIO: 80 eventos, juicios de Nico, sin
pre-registro formal; sirve para decidir si vale la pena entrenar el detector, no como evidencia.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
from edgelab.bridge.indicators import espejo_impulsos as K  # noqa: E402
import es_escalonadas_outcomes as V1  # noqa: E402

VIEW = REPO / "viewer" / "nt8_bridge"
M, SEED, HZ = 4, 20260930, 150


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--asset", default="ES_03-26_202601_25T_HFT"); a = ap.parse_args()
    mes = a.asset.split("_")[2]
    D = V1.load_month(mes)                               # ticks + velas 25t de ES 03-26 del mes
    man = json.loads((VIEW / "bundles" / f"{a.asset}.manifest.json").read_text(encoding="utf-8"))
    ses = np.concatenate([np.full(int(s["tick25_bars"]), str(s["trade_date"])) for s in man["sessions"]])
    Hs, Ls, Cs = D["h"], D["l"], D["c"]                  # en ticks
    T, O, H, L, C, V, S, last25 = [], [], [], [], [], [], [], []
    for sid in dict.fromkeys(ses):
        idx = np.flatnonzero(ses == sid)
        for j in range(0, len(idx) - len(idx) % M, M):
            g = idx[j:j + M]
            T.append(D["t"][g[-1]]); O.append(D["c"][g[0]]); H.append(Hs[g].max()); L.append(Ls[g].min()); C.append(Cs[g[-1]])
            V.append(0.0); S.append(sid); last25.append(g[-1])
    T, H, L, C, S, last25 = (np.array(x) for x in (T, H, L, C, S, last25))
    b = json.loads((VIEW / "bundles" / f"{a.asset}.json").read_text(encoding="utf-8"))
    c = b["bar_series"]["tick_25"]["candles"]; del b
    O = []; V = []
    for sid in dict.fromkeys(ses):
        idx = np.flatnonzero(ses == sid)
        for j in range(0, len(idx) - len(idx) % M, M):
            g = [c[i] for i in idx[j:j + M]]; O.append(g[0]["open"] / 0.25); V.append(sum(x.get("volume", 0) for x in g))
    res = K.run(T, np.array(O), H, L, C, np.array(V), S, params=dict(e_max=1.01, atr_k=None, min_w=17.0, max_bars=20))
    imps = {im["imp_id"]: im for im in res["impulses"]}
    comp = [e for e in res["events"] if e["kind"] == "MIRROR_COMPLETED"]
    pick = sorted(np.random.default_rng(SEED).choice(len(comp), min(80, len(comp)), replace=False))
    exp = {e["id"]: e for e in json.loads((VIEW / "bundles" / "blind" / f"espejo_{a.asset}.json").read_text(encoding="utf-8"))["eventos"]}
    for n_, i in enumerate(pick):                        # mismos espejos que se mostraron (A y B idénticos)
        im = imps[comp[i]["imp_id"]]; ex = exp[f"E{n_ + 1:03d}"]
        assert abs(im["A"] * 0.25 - ex["A"]) < 1e-9 and abs(im["B"] * 0.25 - ex["B"]) < 1e-9, f"E{n_ + 1:03d} no coincide"
    lab = json.loads((VIEW / "labels" / f"blind_espejo_{a.asset}.json").read_text(encoding="utf-8"))["juicios"]
    rows = []
    for n_, i in enumerate(pick):
        eid = f"E{n_ + 1:03d}"; e = comp[i]; im = imps[e["imp_id"]]
        v = lab.get(eid, {}).get("veredicto")
        if v not in ("picos", "sin_picos"):
            continue
        cut = int(e["bar"]); side = -int(im["dir"]); W = abs(im["B"] - im["A"])
        k25 = last25[cut]
        if k25 + 1 >= len(D["bar_tick"]) or D["bar_ses"][k25 + 1] != D["bar_ses"][k25]:
            continue
        ft = D["bar_tick"][k25 + 1]; entry = D["bid"][ft] if side == -1 else D["ask"][ft]
        kend = min(cut + HZ, len(C) - 1)
        end25 = last25[kend] if S[kend] == S[cut] else last25[np.flatnonzero(S == S[cut])[-1]]
        end = min(D["bar_tick"][end25] + 25, V1.ses_end_tick(D, k25))
        r = {}
        for slf in (0.5, 1.0):
            for tp in (1, 2):
                risk = max(2.0, slf * W)
                pnl, why, mfe, mae, ix = V1.sim(side, ft + 1, end, entry, entry - side * risk, entry + side * tp * risk, D["px"], D["bid"], D["ask"])
                r[f"SL{slf:g}W|TP{tp}R"] = ((pnl - V1.COMISION_TICKS) / risk, pnl / risk, int(why))
        rows.append(dict(id=eid, veredicto=v, n_picos=len(lab[eid].get("picos", [])), W=float(W), r=r))
    out = {}
    rng = np.random.default_rng(7)
    for cell in rows[0]["r"]:
        g = {v: np.array([x["r"][cell][0] for x in rows if x["veredicto"] == v]) for v in ("picos", "sin_picos")}
        gb = {v: np.array([x["r"][cell][1] for x in rows if x["veredicto"] == v]) for v in ("picos", "sin_picos")}
        diffs = [rng.choice(g["picos"], len(g["picos"])).mean() - rng.choice(g["sin_picos"], len(g["sin_picos"])).mean() for _ in range(4000)]
        out[cell] = dict(n_picos=len(g["picos"]), n_sin=len(g["sin_picos"]),
                         R_neto_picos=round(float(g["picos"].mean()), 3), R_neto_sin=round(float(g["sin_picos"].mean()), 3),
                         R_bruto_picos=round(float(gb["picos"].mean()), 3), R_bruto_sin=round(float(gb["sin_picos"].mean()), 3),
                         tasa_TP_picos=round(float(np.mean([x["r"][cell][2] == 1 for x in rows if x["veredicto"] == "picos"])), 2),
                         tasa_TP_sin=round(float(np.mean([x["r"][cell][2] == 1 for x in rows if x["veredicto"] == "sin_picos"])), 2),
                         dif=round(float(g["picos"].mean() - g["sin_picos"].mean()), 3),
                         ic90_dif=[round(float(np.quantile(diffs, .05)), 3), round(float(np.quantile(diffs, .95)), 3)])
    o = REPO / "docs" / "research" / "es_escalonadas"; o.mkdir(parents=True, exist_ok=True)
    (o / f"blind_espejo_outcomes_{a.asset}.json").write_text(json.dumps(dict(asset=a.asset, celdas=out, eventos=rows), indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
