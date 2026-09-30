#!/usr/bin/env python3
r"""ES-ESCALONADAS outcomes — docs/research/MANIFIESTO_ES_ESCALONADAS_OUTCOMES_20260930.md (OK de Nico 30/09).

    python tools/es_escalonadas_outcomes.py --mes 202602 [--out docs/research/es_escalonadas/]

Replay tick a tick (ticks NT8 con bid/ask). Vela k de una sesión = operaciones [25k, 25k+25) desde su inicio (verificado
contra el bundle). 32 celdas = familia (planas/empinadas) × confirmación (velas/precio) × objetivo (4/8/12/16) × stop
(pico +1/+2). Control empírico emparejado (3 por evento), bootstrap conjunto por sesión, max-T sobre las 32.
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
sys.path.insert(0, str(REPO / "tools"))
import nq_cruce25_clima as NC  # noqa: E402  (joint_maxT / cell_stat ya testeados)

VIEW = REPO / "viewer" / "nt8_bridge"
TICKS = Path(r"E:\EdgeLab\data\nt8_research_v2\ES_parquet\ES_03-26_ticks.parquet")
TICK = 0.25
COMISION_TICKS = 0.40            # US$ 2,50 por lado = 5 US$ ida y vuelta / 12,5 US$ por tick
HZ, N_CTRL, SEED, TOD_WIN = 150, 3, 20260930, 1800
TGTS, STOPS = (4, 8, 12, 16), (1, 2)
CAPAS = {("planas", "velas"): "", ("planas", "precio"): "__precio",
         ("empinadas", "velas"): "__empinadas", ("empinadas", "precio"): "__empinadas__precio"}


@njit(cache=True)
def sim(side, i0, i_end, entry, stop_lvl, tgt_lvl, px, bid, ask):
    """side +1 compra / −1 venta. Desde el tick i0 (posterior al llenado). Stop: stop de mercado al peor lado cuando opera en
    o más allá del nivel. Objetivo: límite, llena sólo si opera 1 tick más allá (conservador). Devuelve (salida, motivo,
    mfe, mae) en ticks; motivo 1 objetivo, −1 stop, 0 horizonte."""
    mfe = 0.0; mae = 0.0
    for i in range(i0, i_end):
        p = px[i]
        fav = (p - entry) * side; mfe = max(mfe, fav); mae = max(mae, -fav)
        if side == 1:
            if p <= stop_lvl:
                return bid[i] - entry, -1, mfe, mae, i
            if p >= tgt_lvl + 1:
                return tgt_lvl - entry, 1, mfe, mae, i
        else:
            if p >= stop_lvl:
                return entry - ask[i], -1, mfe, mae, i
            if p <= tgt_lvl - 1:
                return entry - tgt_lvl, 1, mfe, mae, i
    j = i_end - 1
    return ((bid[j] - entry) if side == 1 else (entry - ask[j])), 0, mfe, mae, j


def load_month(mes):
    b = json.loads((VIEW / "bundles" / f"ES_03-26_{mes}_25T_HFT.json").read_text(encoding="utf-8"))
    c = b["bar_series"]["tick_25"]["candles"]; del b
    man = json.loads((VIEW / "bundles" / f"ES_03-26_{mes}_25T_HFT.manifest.json").read_text(encoding="utf-8"))
    f = pq.ParquetFile(TICKS)
    cols = ["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks"]
    P, B, A, T, bar_tick, bar_ses, ses_ids = [], [], [], [], [], [], []
    off_t = 0; gi = 0
    for s in man["sessions"]:
        nb = int(s["tick25_bars"])
        rgs = [i for i in range(f.num_row_groups) if f.metadata.row_group(i).column(0).statistics.max >= s["start_utc_ns"]
               and f.metadata.row_group(i).column(0).statistics.min <= s["end_utc_ns"]]
        t = f.read_row_groups(rgs, columns=cols).to_pandas()
        t = t[(t.ts_utc_ns >= s["start_utc_ns"]) & (t.ts_utc_ns <= s["end_utc_ns"])]
        n = len(t)
        assert n // 25 == nb or (n + 24) // 25 == nb, (s["trade_date"], n, nb)
        P.append(t.price_ticks.to_numpy(np.float64)); B.append(t.bid_ticks.to_numpy(np.float64)); A.append(t.ask_ticks.to_numpy(np.float64))
        T.append(t.ts_utc_ns.to_numpy(np.int64))
        bar_tick.append(off_t + np.arange(nb) * 25); bar_ses.append(np.full(nb, len(ses_ids)))
        ses_ids.append(str(s["trade_date"])); off_t += n; gi += nb
        del t
    px, bid, ask = np.concatenate(P), np.concatenate(B), np.concatenate(A)
    bar_tick = np.concatenate(bar_tick); bar_ses = np.concatenate(bar_ses)
    assert len(bar_tick) == len(c), (len(bar_tick), len(c))
    # verificación: máximos de las primeras velas de cada sesión = bundle
    chk = np.random.default_rng(1).choice(len(c) - 2, 2000, replace=False)
    bad = sum(abs(px[bar_tick[k]:bar_tick[k] + 25].max() * TICK - c[k]["high"]) > 1e-9 for k in chk if bar_ses[k] == bar_ses[k + 1])
    assert bad == 0, f"{bad} velas no coinciden con el bundle"
    h = np.array([x["high"] for x in c]) / TICK; l = np.array([x["low"] for x in c]) / TICK; cl = np.array([x["close"] for x in c]) / TICK
    tt = np.array([x["time"] for x in c], float)
    return dict(px=px, bid=bid, ask=ask, bar_tick=bar_tick, bar_ses=bar_ses, ses=ses_ids, h=h, l=l, c=cl, t=tt, n_ticks=len(px))


def vol_rms(c, k=20):
    d = np.diff(c, prepend=c[0]); out = np.full(len(c), np.nan)
    s2 = np.convolve(d ** 2, np.ones(k))[:len(d)]          # s2[i] = suma de d[i-k+1..i]
    out[k:] = np.sqrt(s2[k - 1:-1] / k)                    # velas previas, sin la actual
    return out


def ses_end_tick(D, k):
    s = D["bar_ses"][k]; last = np.searchsorted(D["bar_ses"], s, side="right") - 1
    return min(D["bar_tick"][last] + 25, D["n_ticks"])


def trade(D, side, fill_tick, entry, stop_lvl, tgt, k_bar):
    """Evalúa una operación desde fill_tick+1. Devuelve R neto, R bruto, motivo, mfe, mae, riesgo."""
    risk = abs(entry - stop_lvl)
    if risk <= 0:
        return None
    end = min(D["bar_tick"][min(k_bar + HZ, len(D["bar_tick"]) - 1)], ses_end_tick(D, k_bar))
    if D["bar_ses"][min(k_bar + HZ, len(D["bar_tick"]) - 1)] != D["bar_ses"][k_bar]:
        end = ses_end_tick(D, k_bar)
    if fill_tick + 1 >= end:
        return None
    pnl, why, mfe, mae, ix = sim(side, fill_tick + 1, end, entry, stop_lvl, entry + side * tgt, D["px"], D["bid"], D["ask"])
    return ((pnl - COMISION_TICKS) / risk, pnl / risk, int(why), float(mfe), float(mae), float(risk), int(ix))


def eventos(D, zonas, conf):
    """Entrada de cada zona. velas: mercado en el primer tick de la vela siguiente. precio: stop en det_precio dentro de la
    vela de detección (primer tick que opera en/through el nivel)."""
    E = []
    for z in zonas:
        k = z["det_i"]; side = -1 if z["kind"] == "H" else 1
        if k + 1 >= len(D["bar_tick"]) or D["bar_ses"][k + 1] != D["bar_ses"][k]:
            continue
        peak = z["det_nivel"] / TICK
        if conf == "velas":
            ft = D["bar_tick"][k + 1]; entry = D["bid"][ft] if side == -1 else D["ask"][ft]
        else:
            lvl = z["det_precio"] / TICK; a = D["bar_tick"][k]; ft = None
            for i in range(a, min(a + 25, D["n_ticks"])):
                if (side == -1 and D["px"][i] <= lvl) or (side == 1 and D["px"][i] >= lvl):
                    ft = i; break
            if ft is None:
                continue
            entry = D["bid"][ft] if side == -1 else D["ask"][ft]
        E.append(dict(k=k, side=side, fill=int(ft), entry=float(entry), peak=float(peak), ses=int(D["bar_ses"][k])))
    return E


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mes", default="202602")
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "es_escalonadas"))
    a = ap.parse_args()
    D = load_month(a.mes)
    print("ticks", D["n_ticks"], "velas", len(D["bar_tick"]), "sesiones", len(D["ses"]), flush=True)
    vol = vol_rms(D["c"]); ok = ~np.isnan(vol); cut = np.quantile(vol[ok], [1 / 3, 2 / 3])
    ter = np.where(np.isnan(vol), -1, np.digitize(vol, cut))
    tod = (D["t"].astype(np.int64)) % 86400
    cand = np.flatnonzero((np.arange(len(D["t"])) > 20) & (np.r_[D["bar_ses"][1:], -1] == D["bar_ses"]))
    rng = np.random.default_rng(SEED)
    cells, detail = [], {}
    for (fam, conf), suf in CAPAS.items():
        Z = json.loads((VIEW / "bundles" / "peaks_det" / f"ES_03-26_{a.mes}_25T_HFT{suf}.json").read_text(encoding="utf-8"))["zonas"]
        E = eventos(D, Z, conf)
        # controles: 3 velas de otras sesiones, misma franja ±30 min, mismo tercil, misma dirección y geometría
        for e in E:
            dt = np.abs(tod[cand] - tod[e["k"]]); dt = np.minimum(dt, 86400 - dt)
            m = cand[(D["bar_ses"][cand] != e["ses"]) & (dt <= TOD_WIN) & (ter[cand] == ter[e["k"]])]
            e["ctrl"] = [int(x) for x in rng.choice(m, N_CTRL, replace=False)] if len(m) >= N_CTRL else None
        for tgt in TGTS:
            for sp in STOPS:
                rows = []
                last_exit = {1: -1, -1: -1}
                for e in E:
                    if e["ctrl"] is None or e["fill"] <= last_exit[e["side"]]:
                        continue
                    stop_lvl = e["peak"] - e["side"] * sp
                    r = trade(D, e["side"], e["fill"], e["entry"], stop_lvl, tgt, e["k"])
                    if r is None:
                        continue
                    cr = []
                    for q in e["ctrl"]:
                        ft = D["bar_tick"][q + 1]; en = D["bid"][ft] if e["side"] == -1 else D["ask"][ft]
                        rc = trade(D, e["side"], ft, en, en - e["side"] * r[5], tgt, q)
                        cr.append(rc[0] if rc else np.nan)
                    if np.isnan(cr).any():
                        continue
                    rows.append(dict(ses=e["ses"], R=r[0], Rb=r[1], why=r[2], mfe=r[3], mae=r[4], risk=r[5], ctrl=cr,
                                     ctrl_ses=[int(D["bar_ses"][q]) for q in e["ctrl"]]))
                    # una operación a la vez por dirección dentro de la celda
                    last_exit[e["side"]] = r[6]
                key = f"{fam}|{conf}|T{tgt}|S{sp}"
                detail[key] = rows
                print(key, "n", len(rows), "R neto medio", round(float(np.mean([x["R"] for x in rows])), 4) if rows else None, flush=True)
                cells.append(key)
    # inferencia: diferencia pareada R_evento − media(R_controles), max-T conjunto
    fam_cells, info = [], []
    for key in cells:
        X = detail[key]
        n_ses = len({x["ses"] for x in X})
        d = dict(celda=key, n=len(X), sesiones=n_ses,
                 R_neto=float(np.mean([x["R"] for x in X])) if X else None, R_bruto=float(np.mean([x["Rb"] for x in X])) if X else None,
                 R_control=float(np.mean([np.mean(x["ctrl"]) for x in X])) if X else None,
                 tasa_objetivo=float(np.mean([x["why"] == 1 for x in X])) if X else None,
                 riesgo_ticks_mediano=float(np.median([x["risk"] for x in X])) if X else None)
        if len(X) >= 30 and n_ses >= 8:
            fam_cells.append((d, dict(ev=np.array([x["R"] for x in X]), ctrl=np.array([x["ctrl"] for x in X]),
                                      ev_ses=np.array([x["ses"] for x in X]), ctrl_ses=np.array([x["ctrl_ses"] for x in X]))))
        else:
            d["inconclusa_por_potencia"] = True
        info.append(d)
    obs, se, crit, ic = NC.joint_maxT([c for _, c in fam_cells], len(D["ses"]), n_boot=2000, seed=SEED + 7)
    for i, (d, _) in enumerate(fam_cells):
        d.update(dif=float(obs[i]), se=float(se[i]), t=float(obs[i] / se[i]), ic90=[float(ic[0, i]), float(ic[1, i])],
                 mde80=2.8 * float(se[i]), sobrevive_maxT=bool(abs(obs[i] / se[i]) >= crit))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / f"resultado_{a.mes}.json").write_text(json.dumps(dict(mes=a.mes, t_critico=crit, celdas=info, comision_ticks=COMISION_TICKS,
                                                                 sesiones=D["ses"]), indent=1, default=float), encoding="utf-8")
    for d in info:
        print(d)
    print("t crítico", crit)


if __name__ == "__main__":
    main()
