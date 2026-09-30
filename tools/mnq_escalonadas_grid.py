#!/usr/bin/env python3
r"""MNQ-ESCALONADAS-ESCALAS — docs/research/MANIFIESTO_MNQ_ESCALONADAS_ESCALAS_20260930.md (+ enmienda 1).

    python tools/mnq_escalonadas_grid.py --fase descubrimiento     # ago-2025..ene-2026 (sin feb)
    python tools/mnq_escalonadas_grid.py --fase replica --celdas C1,C2   # mar-2026, sólo celdas pre-elegidas

108 celdas = escala (25/150/500t) × SL (×1, ×2, ×4 del SL base 5/14/26 ticks) × TP (1,2,3,5,10R) × BE (0/1/2R si TP > BE).
Replay tick a tick con bid/ask y 3 ticks de comisión; control con la misma mecánica stop; max-T por sesión.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import escalonadas_posicion_visual as PV  # noqa: E402  (ticks_sim; verificación de velas)
import nq_cruce25_clima as NC  # noqa: E402

VIEW = REPO / "viewer" / "nt8_bridge"
TICK, RT, HZ, N_CTRL, SEED, TOD_WIN = 0.25, 3.0, 1500, 3, 20260930, 1800
ESCALAS = {1: 5, 6: 14, 20: 26}                     # k → SL base en ticks
MULT, TPS, BES = (1, 2, 4), (1, 2, 3, 5, 10), (0, 1, 2)
FASES = {
    "descubrimiento": [("MNQ_09-25_202508", None, None), ("MNQ_09-25_202509", None, "20250910"),
                       ("MNQ_12-25_202509", "20250911", None), ("MNQ_12-25_202510", None, None), ("MNQ_12-25_202511", None, None),
                       ("MNQ_12-25_202512", None, "20251210"), ("MNQ_03-26_202512", "20251211", None), ("MNQ_03-26_202601", None, None)],
    "replica": [("MNQ_03-26_202603", None, None)],
}


def celdas():
    out = []
    for k, base in ESCALAS.items():
        for m in MULT:
            for tp in TPS:
                for be in BES:
                    if be == 0 or tp > be:
                        out.append((k, base * m, tp, be))
    return out


def key(c):
    k, sl, tp, be = c
    return f"{25 * k}t|SL{sl}|TP{tp}R|BE{be}"


def load_asset(aid):
    b = json.loads((VIEW / "bundles" / f"{aid}_25T_HFT.json").read_text(encoding="utf-8"))
    c = b["bar_series"]["tick_25"]["candles"]; del b
    man = json.loads((VIEW / "bundles" / f"{aid}_25T_HFT.manifest.json").read_text(encoding="utf-8"))
    import pyarrow.parquet as pq
    f = pq.ParquetFile(man["source_path"])
    P, B, A, bt, bs, ids = [], [], [], [], [], []
    off = 0
    for si, s in enumerate(man["sessions"]):
        nb = int(s["tick25_bars"])
        rgs = [i for i in range(f.num_row_groups) if f.metadata.row_group(i).column(0).statistics.max >= s["start_utc_ns"]
               and f.metadata.row_group(i).column(0).statistics.min <= s["end_utc_ns"]]
        t = f.read_row_groups(rgs, columns=["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks"]).to_pandas()
        t = t[(t.ts_utc_ns >= s["start_utc_ns"]) & (t.ts_utc_ns <= s["end_utc_ns"])]
        assert (len(t) + 24) // 25 == nb or len(t) // 25 == nb, (aid, s["trade_date"], len(t), nb)
        P.append(t.price_ticks.to_numpy(np.float64)); B.append(t.bid_ticks.to_numpy(np.float64)); A.append(t.ask_ticks.to_numpy(np.float64))
        bt.append(off + np.arange(nb) * 25); bs.append(np.full(nb, si)); ids.append(str(s["trade_date"])); off += len(t); del t
    D = dict(px=np.concatenate(P), bid=np.concatenate(B), ask=np.concatenate(A), bar_tick=np.concatenate(bt), bar_ses=np.concatenate(bs), ses=ids)
    assert len(D["bar_tick"]) == len(c)
    D.update(h=np.array([x["high"] for x in c]) / TICK, l=np.array([x["low"] for x in c]) / TICK, c=np.array([x["close"] for x in c]) / TICK,
             o=np.array([x["open"] for x in c]) / TICK, t=np.array([x["time"] for x in c], float))
    chk = np.random.default_rng(1).choice(len(c) - 2, 1000, replace=False)
    assert sum(abs(D["px"][D["bar_tick"][i]:D["bar_tick"][i] + 25].max() - D["h"][i]) > 1e-9 for i in chk if D["bar_ses"][i] == D["bar_ses"][i + 1]) == 0
    return D


def agg(D, k):
    if k == 1:
        return dict(h=D["h"], l=D["l"], c=D["c"], o=D["o"], t=D["t"], bar_tick=D["bar_tick"], bar_ses=D["bar_ses"])
    first = []
    for s in np.unique(D["bar_ses"]):
        idx = np.flatnonzero(D["bar_ses"] == s); first.extend(idx[::k].tolist())
    first = np.array(first); nxt = np.r_[first[1:], len(D["bar_ses"])]
    return dict(h=np.maximum.reduceat(D["h"], first), l=np.minimum.reduceat(D["l"], first), c=D["c"][nxt - 1], o=D["o"][first],
                t=D["t"][first], bar_tick=D["bar_tick"][first], bar_ses=D["bar_ses"][first])


def vol_rms(c, k=20):
    d = np.diff(c, prepend=c[0]); out = np.full(len(c), np.nan)
    s2 = np.convolve(d ** 2, np.ones(k))[:len(d)]; out[k:] = np.sqrt(s2[k - 1:-1] / k)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--fase", default="descubrimiento", choices=list(FASES))
    ap.add_argument("--celdas", default=None); a = ap.parse_args()
    CELLS = celdas() if not a.celdas else [c for c in celdas() if key(c) in a.celdas.split(",")]
    rng = np.random.default_rng(SEED)
    rows = {key(c): [] for c in CELLS}
    ses_global = []
    desc = {}
    for aid, lo, hi in FASES[a.fase]:
        D = load_asset(aid); n_ticks = len(D["px"])
        base_ses = len(ses_global); ses_global += [f"{aid}:{s}" for s in D["ses"]]
        okses = np.array([(lo is None or s >= lo) and (hi is None or s <= hi) for s in D["ses"]])
        for k in ESCALAS:
            G = agg(D, k); nb = len(G["c"])
            layer = f"{aid}_25T_HFT__precio" if k == 1 else f"{aid}_{25 * k}T__precio"
            Z = json.loads((VIEW / "bundles" / "peaks_det" / f"{layer}.json").read_text(encoding="utf-8"))["zonas"]
            vol = vol_rms(G["c"]); cut = np.nanquantile(vol, [1 / 3, 2 / 3]); ter = np.where(np.isnan(vol), -1, np.digitize(vol, cut))
            tod = G["t"].astype(np.int64) % 86400
            same_next = np.r_[G["bar_ses"][1:], -1] == G["bar_ses"]
            ses21 = np.r_[G["bar_ses"][21:], np.full(21, -1)]
            cand = np.flatnonzero((np.arange(nb) > 25) & same_next & (ses21 == G["bar_ses"]))
            ses_last_tick = {s: G["bar_tick"][np.flatnonzero(G["bar_ses"] == s)[-1]] + 25 * k for s in np.unique(G["bar_ses"])}

            def end_tick(kb):
                kk = min(kb + HZ, nb - 1)
                e = G["bar_tick"][kk] if G["bar_ses"][kk] == G["bar_ses"][kb] else ses_last_tick[G["bar_ses"][kb]]
                return min(e, ses_last_tick[G["bar_ses"][kb]], n_ticks)

            def fill_stop(i0, i1, side, lvl):
                for i in range(i0, min(i1, n_ticks)):
                    if (side == 1 and D["px"][i] >= lvl) or (side == -1 and D["px"][i] <= lvl):
                        return i
                return -1

            ev = []
            for z in Z:
                kb = z["det_i"]; s = G["bar_ses"][kb]
                if not okses[s] or kb + 1 >= nb or not same_next[kb]:
                    continue
                side = -1 if z["kind"] == "H" else 1; lvl = z["det_precio"] / TICK; a0 = G["bar_tick"][kb]
                f = fill_stop(a0, a0 + 25 * k, side, lvl)
                if f < 0:
                    continue
                dist = max(1.0, abs(G["o"][kb] - lvl))
                dt = np.abs(tod[cand] - tod[kb]); dt = np.minimum(dt, 86400 - dt)
                pool = cand[(G["bar_ses"][cand] != s) & okses[G["bar_ses"][cand]] & (dt <= TOD_WIN) & (ter[cand] == ter[kb])]
                ctrl = []; tries = 0
                while len(ctrl) < N_CTRL and tries < 30 and len(pool):
                    q = int(rng.choice(pool)); tries += 1
                    t0 = G["bar_tick"][q + 1]; ref = D["px"][t0]
                    cf = fill_stop(t0, G["bar_tick"][min(q + 21, nb - 1)], side, ref + side * dist)
                    if cf >= 0:
                        ctrl.append((q, cf))
                if len(ctrl) == N_CTRL:
                    ev.append((kb, side, f, ctrl, s))
            desc[f"{aid}|{25 * k}t"] = dict(zonas=len(Z), eventos=len(ev))
            print(aid, 25 * k, "zonas", len(Z), "eventos", len(ev), flush=True)
            for c in CELLS:
                if c[0] != k:
                    continue
                _, sl, tp, be = c
                for kb, side, f, ctrl, s in ev:          # todas las detecciones (el manifiesto no limita superposición)
                    entry = D["bid"][f] if side == -1 else D["ask"][f]
                    e = end_tick(kb)
                    if f + 1 >= e:
                        continue
                    pnl, why = PV.ticks_sim(side, f + 1, e, entry, float(sl), float(tp), float(be), D["px"], D["bid"], D["ask"], 1)
                    cr = []
                    for q, cf in ctrl:
                        ce = D["bid"][cf] if side == -1 else D["ask"][cf]; e2 = end_tick(q)
                        if cf + 1 >= e2:
                            cr.append(np.nan); continue
                        p2, _ = PV.ticks_sim(side, cf + 1, e2, ce, float(sl), float(tp), float(be), D["px"], D["bid"], D["ask"], 1)
                        cr.append((p2 - RT) / sl)
                    if np.isnan(cr).any():
                        continue
                    rows[key(c)].append(dict(ses=base_ses + int(s), R=(pnl - RT) / sl, Rb=pnl / sl, why=int(why), ctrl=cr,
                                             ctrl_ses=[base_ses + int(G["bar_ses"][q]) for q, _ in ctrl]))
        del D
    info, fam = [], []
    for kk, X in rows.items():
        ns = len({x["ses"] for x in X}); d = dict(celda=kk, n=len(X), sesiones=ns)
        if X:
            d.update(R_neto=float(np.mean([x["R"] for x in X])), R_bruto=float(np.mean([x["Rb"] for x in X])),
                     R_control=float(np.mean([np.mean(x["ctrl"]) for x in X])), tasa_TP=float(np.mean([x["why"] == 1 for x in X])))
        if len(X) >= 30 and ns >= 8:
            fam.append((d, dict(ev=np.array([x["R"] for x in X]), ctrl=np.array([x["ctrl"] for x in X]),
                                ev_ses=np.array([x["ses"] for x in X]), ctrl_ses=np.array([x["ctrl_ses"] for x in X]))))
        else:
            d["inconclusa_por_potencia"] = True
        info.append(d)
    obs, se, crit, ic = NC.joint_maxT([c for _, c in fam], len(ses_global), n_boot=2000, seed=SEED + 7)
    for i, (d, _) in enumerate(fam):
        d.update(dif=float(obs[i]), t=float(obs[i] / se[i]), ic90=[float(ic[0, i]), float(ic[1, i])], mde80=2.8 * float(se[i]),
                 sobrevive_maxT=bool(abs(obs[i] / se[i]) >= crit))
    o = REPO / "docs" / "research" / "es_escalonadas"; o.mkdir(parents=True, exist_ok=True)
    (o / f"mnq_grid_{a.fase}.json").write_text(json.dumps(dict(fase=a.fase, t_critico=crit, sesiones=len(ses_global), descriptivo=desc, celdas=info),
                                                          indent=1, default=float), encoding="utf-8")
    for d in sorted(info, key=lambda d: -d.get("R_neto", -9))[:15]:
        print(d["celda"], d["n"], round(d.get("R_neto", 0), 3), round(d.get("R_control", 0), 3), round(d.get("t", 0), 2), d.get("sobrevive_maxT"))
    print("t crítico", crit, "sobreviven", sum(bool(d.get("sobrevive_maxT")) for d in info), "de", len(info))


if __name__ == "__main__":
    main()
