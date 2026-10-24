#!/usr/bin/env python3
r"""EURUSD-ESCALONADAS-ESCALAS — docs/research/eurusd_escalonadas_20261021/MANIFIESTO_EURUSD_ESCALONADAS_ESCALAS_20261021.md

    python tools/eurusd_escalonadas_grid.py --fase descubrimiento     # ago-2025..ene-2026
    python tools/eurusd_escalonadas_grid.py --fase replica --celdas C1,C2   # abr-jun 2026, solo celdas pre-elegidas

Misma grilla, mecanica, control y max-T que tools/mnq_escalonadas_grid.py (se reutilizan sus funciones). Diferencias:
datos Dukascopy (mid/bid/ask, tick 0,00001, velas 25t = 25 cotizaciones, sesion desde 17:00 ET), detectores calculados en
memoria (familia PLANAS escalada como en MNQ) y comision RT 3,5 ticks. Un bloque por mes calendario de sesion.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import escalonadas_det as E  # noqa: E402
import escalonadas_posicion_visual as PV  # noqa: E402
import mnq_escalonadas_grid as M  # noqa: E402
import nq_cruce25_clima as NC  # noqa: E402

SRC = "E:/EdgeLab/data/eurusd_ticks.parquet"
PIP = 0.00001
RT, HZ, N_CTRL, SEED, TOD_WIN = 3.5, M.HZ, M.N_CTRL, M.SEED, M.TOD_WIN
ESCALA = {1: 4.5, 6: 12.42, 20: 23.49}                 # mismas que MNQ (ES -> MNQ); EURUSD en ticks de 0,00001 ~ NQ
FASES = {"descubrimiento": ["2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01"],
         "replica": ["2026-04", "2026-05", "2026-06"]}


def load_month(mes):
    a = pd.Timestamp(mes + "-01", tz="America/New_York") - pd.Timedelta(days=2); b = a + pd.Timedelta(days=36)
    f = pq.ParquetFile(SRC); parts = []
    for i in range(f.num_row_groups):
        st = f.metadata.row_group(i).column(0).statistics
        if pd.Timestamp(st.max).tz_localize("UTC") < a or pd.Timestamp(st.min).tz_localize("UTC") > b: continue
        parts.append(f.read_row_group(i, columns=["timestamp", "last", "bid", "ask"]).to_pandas())
    t = pd.concat(parts, ignore_index=True).sort_values("timestamp", kind="stable").reset_index(drop=True)
    et = t.timestamp.dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    ses = (et + pd.Timedelta(hours=7)).dt.strftime("%Y%m%d")                     # sesion FX desde 17:00 ET
    m = (ses.str.slice(0, 6) == mes.replace("-", "")).to_numpy(); t = t[m].reset_index(drop=True); ses = ses[m].reset_index(drop=True)
    D = dict(px=np.round(t["last"].to_numpy() / PIP), bid=np.round(t["bid"].to_numpy() / PIP), ask=np.round(t["ask"].to_numpy() / PIP))
    ts = t.timestamp.astype("datetime64[ns]").astype("int64").to_numpy() // 10**9
    sv = ses.to_numpy(); starts = np.flatnonzero(np.r_[True, sv[1:] != sv[:-1]]); ends = np.r_[starts[1:], len(sv)]
    bt, bs, ids, H, L, C, O, T = [], [], [], [], [], [], [], []
    for si, (s0, s1) in enumerate(zip(starts, ends)):
        nb = (s1 - s0) // 25
        if nb < 50: continue
        k = len(ids); ids.append(sv[s0]); first = s0 + np.arange(nb) * 25
        px = D["px"][s0:s0 + nb * 25].reshape(nb, 25)
        bt.append(first); bs.append(np.full(nb, k)); H.append(px.max(1)); L.append(px.min(1)); C.append(px[:, -1]); O.append(px[:, 0]); T.append(ts[first].astype(float))
    D.update(bar_tick=np.concatenate(bt), bar_ses=np.concatenate(bs), ses=ids, h=np.concatenate(H), l=np.concatenate(L), c=np.concatenate(C),
             o=np.concatenate(O), t=np.concatenate(T))
    return D


def capas_para(G, esc):
    E.TICK = 1.0
    f = dict(E.FAMILIAS["planas"])
    for kk in ("max_step", "min_pull", "total_min", "step_min"): f[kk] = int(round(f[kk] * esc))
    conf = int(round(2 * esc)); cd = dict(t=G["t"], h=G["h"], l=G["l"], c=G["c"])
    zp = E.detectar_px(cd, f, conf); zv = E.detectar(cd, f); f1 = dict(f, w=1); zw1 = E.detectar(cd, f1)
    return {"__precio": {"zonas": zp}, "": {"zonas": zv, "candidatas": E.candidatas(cd, f, zv)}, "__w1": {"zonas": zw1}}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--fase", default="descubrimiento", choices=list(FASES)); ap.add_argument("--celdas", default=None)
    a = ap.parse_args()
    CELLS = M.celdas() if not a.celdas else [c for c in M.celdas() if M.key(c) in a.celdas.split(",")]
    rng = np.random.default_rng(SEED); rows = {M.key(c): [] for c in CELLS}; ses_global = []; desc = {}
    for mes in FASES[a.fase]:
        D = load_month(mes); n_ticks = len(D["px"]); base_ses = len(ses_global); ses_global += [f"{mes}:{s}" for s in D["ses"]]
        okses = np.ones(len(D["ses"]), bool)
        for k in M.ESCALAS:
            G = M.agg(D, k); nb = len(G["c"]); capas = capas_para(G, ESCALA[k])
            vol = M.vol_rms(G["c"]); cut = np.nanquantile(vol, [1 / 3, 2 / 3]); ter = np.where(np.isnan(vol), -1, np.digitize(vol, cut))
            tod = G["t"].astype(np.int64) % 86400
            same_next = np.r_[G["bar_ses"][1:], -1] == G["bar_ses"]; ses21 = np.r_[G["bar_ses"][21:], np.full(21, -1)]
            cand = np.flatnonzero((np.arange(nb) > 25) & same_next & (ses21 == G["bar_ses"]))
            ses_last_tick = {s: G["bar_tick"][np.flatnonzero(G["bar_ses"] == s)[-1]] + 25 * k for s in np.unique(G["bar_ses"])}

            def end_tick(kb):
                kk = min(kb + HZ, nb - 1)
                e = G["bar_tick"][kk] if G["bar_ses"][kk] == G["bar_ses"][kb] else ses_last_tick[G["bar_ses"][kb]]
                return min(e, ses_last_tick[G["bar_ses"][kb]], n_ticks)

            def win_end(kb, nbars):
                kk = min(kb + nbars, nb - 1); return min(G["bar_tick"][kk], ses_last_tick[G["bar_ses"][kb]], n_ticks)

            def fill_stop(i0, i1, side, lvl):
                for i in range(i0, min(i1, n_ticks)):
                    if (side == 1 and D["px"][i] >= lvl) or (side == -1 and D["px"][i] <= lvl): return i
                return -1

            def fill_limit(i0, i1, side, lvl, through):
                for i in range(i0, min(i1, n_ticks)):
                    if (side == 1 and D["px"][i] <= lvl - through) or (side == -1 and D["px"][i] >= lvl + through): return i
                return -1

            def pool_for(kb, s):
                dt = np.abs(tod[cand] - tod[kb]); dt = np.minimum(dt, 86400 - dt)
                return cand[(G["bar_ses"][cand] != s) & okses[G["bar_ses"][cand]] & (dt <= TOD_WIN) & (ter[cand] == ter[kb])]

            def controles(kb, s, side, modo, dist, vig, through):
                pool = pool_for(kb, s); out = []; tries = 0
                while len(out) < N_CTRL and tries < 30 and len(pool):
                    q = int(rng.choice(pool)); tries += 1; t0 = G["bar_tick"][q + 1]; ref = D["px"][t0]
                    if modo == "mercado": out.append((q, t0, D["bid"][t0] if side == -1 else D["ask"][t0])); continue
                    if modo == "stop":
                        cf = fill_stop(t0, win_end(q, 21), side, ref + side * dist)
                        if cf >= 0: out.append((q, cf, D["bid"][cf] if side == -1 else D["ask"][cf]))
                    else:
                        lv = ref - side * dist; cf = fill_limit(t0, win_end(q, vig + 1), side, lv, through)
                        if cf >= 0: out.append((q, cf, lv))
                return out if len(out) == N_CTRL else None

            ev = {e: [] for e in M.ENTRADAS}
            for z in capas["__precio"]["zonas"]:
                kb = z["det_i"]; s = G["bar_ses"][kb]
                if kb + 1 >= nb or not same_next[kb]: continue
                side = -1 if z["kind"] == "H" else 1; Tq = z["det_precio"]; Pq = z["det_nivel"]; a0 = G["bar_tick"][kb]
                f = fill_stop(a0, a0 + 25 * k, side, Tq)
                if f < 0: continue
                c0 = controles(kb, s, side, "stop", max(1.0, abs(G["o"][kb] - Tq)), 20, 0)
                if c0: ev["precio_stop"].append((kb, side, f, D["bid"][f] if side == -1 else D["ask"][f], c0, s))
                for nm, x in (("precio_lim50", 0.5), ("precio_lim25", 0.75)):
                    Lq = float(np.round(Tq + (Pq - Tq) * x)); fl = fill_limit(f + 1, win_end(kb, 21), side, Lq, 1)
                    if fl >= 0:
                        cl = controles(kb, s, side, "limite", max(1.0, abs(Lq - Tq)), 20, 1)
                        if cl: ev[nm].append((kb, side, fl, Lq, cl, s))
            for suf, nm in (("", "velas_w2"), ("__w1", "velas_w1")):
                for z in capas[suf]["zonas"]:
                    kb = z["det_i"]; s = G["bar_ses"][kb]
                    if kb + 1 >= nb or not same_next[kb]: continue
                    side = -1 if z["kind"] == "H" else 1; f = G["bar_tick"][kb + 1]; cm = controles(kb, s, side, "mercado", 0, 0, 0)
                    if cm: ev[nm].append((kb, side, f, D["bid"][f] if side == -1 else D["ask"][f], cm, s))
            for cnd in capas[""].get("candidatas", []):
                kb = cnd["cand_i"]; s = G["bar_ses"][kb]
                if kb + 1 >= nb or not same_next[kb]: continue
                side = -1 if cnd["kind"] == "H" else 1; N = cnd["nivel"]; Lq = N + side
                fl = fill_limit(G["bar_tick"][kb + 1], win_end(kb, 16), side, Lq, 1)
                if fl >= 0:
                    cl = controles(kb, s, side, "limite", max(1.0, abs(G["c"][kb] - Lq)), 15, 1)
                    if cl: ev["anticipada_2p"].append((kb, side, fl, Lq, cl, s))
            desc[f"{mes}|{25 * k}t"] = {e: len(v) for e, v in ev.items()}; print(mes, 25 * k, desc[f"{mes}|{25 * k}t"], flush=True)
            for c in CELLS:
                ent, kc, sl, tp, be = c
                if kc != k: continue
                for kb, side, f, entry, ctrl, s in ev[ent]:
                    e = end_tick(kb)
                    if f + 1 >= e: continue
                    pnl, why = PV.ticks_sim(side, f + 1, e, entry, float(sl), float(tp), float(be), D["px"], D["bid"], D["ask"], 1)
                    cr = []
                    for q, cf, ce in ctrl:
                        e2 = end_tick(q)
                        if cf + 1 >= e2: cr.append(np.nan); continue
                        p2, _ = PV.ticks_sim(side, cf + 1, e2, ce, float(sl), float(tp), float(be), D["px"], D["bid"], D["ask"], 1)
                        cr.append((p2 - RT) / sl)
                    if np.isnan(cr).any(): continue
                    rows[M.key(c)].append(dict(ses=base_ses + int(s), R=(pnl - RT) / sl, Rb=pnl / sl, why=int(why), ctrl=cr,
                                               ctrl_ses=[base_ses + int(G["bar_ses"][q]) for q, _, _ in ctrl]))
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
    o = REPO / "docs" / "research" / "eurusd_escalonadas_20261021"; o.mkdir(parents=True, exist_ok=True)
    (o / f"eurusd_grid_{a.fase}.json").write_text(json.dumps(dict(fase=a.fase, t_critico=crit, sesiones=len(ses_global), descriptivo=desc, celdas=info),
                                                             indent=1, default=float), encoding="utf-8")
    for d in sorted(info, key=lambda d: -d.get("R_neto", -9))[:15]:
        print(d["celda"], d["n"], round(d.get("R_neto", 0), 3), round(d.get("R_control", 0), 3), round(d.get("t", 0), 2), d.get("sobrevive_maxT"))
    print("t critico", crit, "sobreviven", sum(bool(d.get("sobrevive_maxT")) for d in info), "de", len(info))


if __name__ == "__main__":
    main()
