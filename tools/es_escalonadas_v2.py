#!/usr/bin/env python3
r"""ES-ESCALONADAS v2 — docs/research/MANIFIESTO_ES_ESCALONADAS_V2_20260930.md (OK de Nico 30/09, enmienda 100 celdas).

    python tools/es_escalonadas_v2.py --mes 202601

A: continuación (entrada stop a 2 ticks del pico, confirmación por precio) con stop zona+2 / 10 / 16 ticks.
B: V-shape: tras la detección, el precio supera el extremo de la zona en ≥ 2 ticks y en ≤ 20 velas vuelve a 1 tick del
   lado interno → entrada stop en la dirección original; stop = extremo del barrido + 2 / + 6 ticks.
Objetivos 1, 2, 3, 5, 8 R. Filtro de tendencia: todas / a favor. Control: misma mecánica stop a 2 ticks desde velas al
azar emparejadas (franja, tercil de volatilidad, estado de tendencia relativo a la dirección). max-T sobre las 100.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from numba import njit

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import es_escalonadas_outcomes as V1  # noqa: E402  (load_month, sim, vol_rms, ses_end_tick)
import nq_cruce25_clima as NC  # noqa: E402

VIEW = V1.VIEW
HZ, SEED, TOD_WIN, N_CTRL = 150, 20260930, 1800, 3
RS = (1, 2, 3, 5, 8)
A_STOPS = ("zona+2", "fijo10", "fijo16")
B_STOPS = (2, 6)
CAPAS = {"planas": "__precio", "empinadas": "__empinadas__precio"}


@njit(cache=True)
def stop_fill(px, i0, i1, side, lvl):
    """Primer tick en [i0, i1) que opera en o más allá de lvl en la dirección side (entrada stop). −1 si no llena."""
    for i in range(i0, i1):
        if (side == 1 and px[i] >= lvl) or (side == -1 and px[i] <= lvl):
            return i
    return -1


@njit(cache=True)
def vshape(px, i0, i1, side, ext, sweep_ticks, rec_ticks, max_ticks_after):
    """side = dirección original (−1 techo). Barrido: precio más allá de ext por sweep_ticks en contra (arriba de un techo).
    Recuperación: vuelve a ext − rec_ticks (techo) dentro de max_ticks_after ticks del barrido. Devuelve (i_barrido,
    i_entrada, extremo_barrido) o (−1, −1, 0)."""
    sw = -1; xtr = 0.0
    for i in range(i0, i1):
        p = px[i]
        if sw < 0:
            if (side == -1 and p >= ext + sweep_ticks) or (side == 1 and p <= ext - sweep_ticks):
                sw = i; xtr = p
        else:
            if (side == -1 and p > xtr) or (side == 1 and p < xtr):
                xtr = p
            if i - sw > max_ticks_after:
                return -1, -1, 0.0
            if (side == -1 and p <= ext - rec_ticks) or (side == 1 and p >= ext + rec_ticks):
                return sw, i, xtr
    return -1, -1, 0.0


def ema(x, n):
    a = 2 / (n + 1); out = np.empty_like(x); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mes", default="202601")
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "es_escalonadas"))
    a = ap.parse_args()
    D = V1.load_month(a.mes)
    nb = len(D["bar_tick"])
    print("ticks", D["n_ticks"], "velas", nb, "sesiones", len(D["ses"]), flush=True)
    e200 = ema(D["c"], 200); slope = e200 - np.r_[np.full(50, np.nan), e200[:-50]]
    trend = np.where((D["c"] > e200) & (slope > 0), 1, np.where((D["c"] < e200) & (slope < 0), -1, 0))
    vol = V1.vol_rms(D["c"]); cut = np.nanquantile(vol, [1 / 3, 2 / 3]); ter = np.where(np.isnan(vol), -1, np.digitize(vol, cut))
    tod = D["t"].astype(np.int64) % 86400
    same_next = np.r_[D["bar_ses"][1:], -1] == D["bar_ses"]
    cand = np.flatnonzero((np.arange(nb) > 250) & same_next)
    bar_of_tick = np.repeat(np.arange(nb), np.diff(np.r_[D["bar_tick"], D["n_ticks"]]))
    rng = np.random.default_rng(SEED)
    px, bid, ask = D["px"], D["bid"], D["ask"]

    def end_tick(k):
        kk = min(k + HZ, nb - 1)
        return V1.ses_end_tick(D, k) if D["bar_ses"][kk] != D["bar_ses"][k] else min(D["bar_tick"][kk], V1.ses_end_tick(D, k))

    def ctrl_fills(k, side):
        """3 entradas de control con la misma mecánica: vela al azar emparejada, stop a 2 ticks en la dirección."""
        tr = trend[k] * side
        dt = np.abs(tod[cand] - tod[k]); dt = np.minimum(dt, 86400 - dt)
        pool = cand[(D["bar_ses"][cand] != D["bar_ses"][k]) & (dt <= TOD_WIN) & (ter[cand] == ter[k]) & (trend[cand] * side == tr)]
        out = []; tries = 0
        while len(out) < N_CTRL and tries < 30 and len(pool):
            q = int(rng.choice(pool)); tries += 1
            t0 = D["bar_tick"][q + 1]; ref = px[t0]
            f = stop_fill(px, t0, min(D["bar_tick"][min(q + 21, nb - 1)], V1.ses_end_tick(D, q)), side, ref + side * 2)
            if f >= 0:
                out.append((q, int(f)))
        return out if len(out) == N_CTRL else None

    def run(side, fill, stop_lvl, k_bar, R):
        entry = bid[fill] if side == -1 else ask[fill]
        risk = abs(entry - stop_lvl)
        if risk < 1:
            return None
        end = end_tick(k_bar)
        if fill + 1 >= end:
            return None
        pnl, why, mfe, mae, ix = V1.sim(side, fill + 1, end, entry, stop_lvl, entry + side * R * risk, px, bid, ask)
        return ((pnl - V1.COMISION_TICKS) / risk, pnl / risk, int(why), float(risk), int(ix))

    rows = {}; desc = {}
    for fam, suf in CAPAS.items():
        Z = json.loads((VIEW / "bundles" / "peaks_det" / f"ES_03-26_{a.mes}_25T_HFT{suf}.json").read_text(encoding="utf-8"))["zonas"]
        evA, evB = [], []
        nsw = nrec = 0
        for z in Z:
            k = z["det_i"]; side = -1 if z["kind"] == "H" else 1
            if k + 1 >= nb or not same_next[k]:
                continue
            known = [p[2] / V1.TICK for p in z["picos"][: z.get("det_idx", len(z["picos"]) - 1) + 1]]
            ext = max(known) if side == -1 else min(known)                  # extremo de la zona conocido al detectar
            lvl = z["det_precio"] / V1.TICK; a0 = D["bar_tick"][k]
            f = stop_fill(px, a0, min(a0 + 25, D["n_ticks"]), side, lvl)
            end = end_tick(k)
            if f >= 0:
                evA.append(dict(k=k, side=side, fill=int(f), ext=ext, ses=int(D["bar_ses"][k]), tr=int(trend[k] * side)))
            sw, fe, xtr = vshape(px, (f if f >= 0 else a0) + 1, end, side, ext, 2.0, 1.0, 20 * 25)
            if sw >= 0:
                nsw += 1
            if fe >= 0:
                nrec += 1
                kb = int(bar_of_tick[fe])
                evB.append(dict(k=kb, side=side, fill=int(fe), xtr=float(xtr), ses=int(D["bar_ses"][kb]), tr=int(trend[kb] * side)))
        desc[fam] = dict(zonas=len(Z), entradas_A=len(evA), barridas=nsw, recuperadas_B=nrec)
        print(fam, desc[fam], flush=True)
        for E in (evA, evB):
            for e in E:
                e["ctrl"] = ctrl_fills(e["k"], e["side"])
        specs = [("A", s, R) for s in A_STOPS for R in RS] + [("B", s, R) for s in B_STOPS for R in RS]
        for tipo, s, R in specs:
            E = evA if tipo == "A" else evB
            for filt in ("todas", "a_favor"):
                key = f"{fam}|{tipo}|{'stop=' + str(s)}|{R}R|{filt}"
                out = []; last = {1: -1, -1: -1}
                for e in E:
                    if e["ctrl"] is None or e["fill"] <= last[e["side"]] or (filt == "a_favor" and e["tr"] != 1):
                        continue
                    side = e["side"]
                    if tipo == "A":
                        entry0 = bid[e["fill"]] if side == -1 else ask[e["fill"]]
                        stop_lvl = (e["ext"] - side * 2) if s == "zona+2" else (entry0 - side * (10 if s == "fijo10" else 16))
                    else:
                        stop_lvl = e["xtr"] - side * s
                    r = run(side, e["fill"], stop_lvl, e["k"], R)
                    if r is None:
                        continue
                    cr = []
                    for q, cf in e["ctrl"]:
                        ce = bid[cf] if side == -1 else ask[cf]
                        rc = run(side, cf, ce - side * r[3], q, R)
                        cr.append(rc[0] if rc else np.nan)
                    if np.isnan(cr).any():
                        continue
                    out.append(dict(ses=e["ses"], R=r[0], Rb=r[1], why=r[2], risk=r[3], ctrl=cr, ctrl_ses=[int(D["bar_ses"][q]) for q, _ in e["ctrl"]]))
                    last[side] = r[4]
                rows[key] = out
        del evA, evB
    info, fam_cells = [], []
    for key, X in rows.items():
        ns = len({x["ses"] for x in X})
        d = dict(celda=key, n=len(X), sesiones=ns)
        if X:
            d.update(R_neto=float(np.mean([x["R"] for x in X])), R_bruto=float(np.mean([x["Rb"] for x in X])),
                     R_control=float(np.mean([np.mean(x["ctrl"]) for x in X])), tasa_objetivo=float(np.mean([x["why"] == 1 for x in X])),
                     riesgo_ticks_mediano=float(np.median([x["risk"] for x in X])))
        if len(X) >= 30 and ns >= 8:
            fam_cells.append((d, dict(ev=np.array([x["R"] for x in X]), ctrl=np.array([x["ctrl"] for x in X]),
                                      ev_ses=np.array([x["ses"] for x in X]), ctrl_ses=np.array([x["ctrl_ses"] for x in X]))))
        else:
            d["inconclusa_por_potencia"] = True
        info.append(d)
    obs, se, crit, ic = NC.joint_maxT([c for _, c in fam_cells], len(D["ses"]), n_boot=2000, seed=SEED + 7)
    for i, (d, _) in enumerate(fam_cells):
        d.update(dif=float(obs[i]), se=float(se[i]), t=float(obs[i] / se[i]), ic90=[float(ic[0, i]), float(ic[1, i])],
                 mde80=2.8 * float(se[i]), sobrevive_maxT=bool(abs(obs[i] / se[i]) >= crit))
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    (o / f"resultado_v2_{a.mes}.json").write_text(json.dumps(dict(mes=a.mes, t_critico=crit, descriptivo=desc, celdas=info), indent=1, default=float), encoding="utf-8")
    for d in info:
        print(d.get("celda"), d.get("n"), round(d.get("R_neto", 0), 3), round(d.get("R_control", 0), 3), round(d.get("t", 0), 2), d.get("sobrevive_maxT"))
    print("t crítico", crit)


if __name__ == "__main__":
    main()
