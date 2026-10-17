# -*- coding: utf-8 -*-
"""F0 Fase 0C — cola real con el feed L1 del NT8 (l1_quotes: Ask/Bid/Last en el mismo reloj).
Manifiesto: docs/research/F0_EJECUCION_PASIVA_ES_MANIFIESTO_20261017.md, seccion 13.
No usa el L2 profundo ni el agresor heuristico. Solo sesiones 2026-07-01..2026-09-30.
"""
from __future__ import annotations

import json
import math
import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from numba import njit

NS_PER_US = 1000
TAU_US = 60 * 1_000_000
HS_US = {10: 10_000_000, 60: 60_000_000, 300: 300_000_000}
START, END = "20260701", "20260930"
MODELS = ("TT", "TOUCH", "Q_NOCANCEL", "Q_PRORATA")      # PRIMARIO = Q_PRORATA (indice 3)
PRIMARY_MODEL = 3
SIDE_BID, SIDE_ASK, SIDE_LAST = 1, 0, 2                   # MarketDataType de NT8


def find_root():
    root = Path("/kaggle/input")
    if root.exists():
        for m in root.rglob("L2_RELEASE_MANIFEST.json"):
            return m.parent
    local = os.environ.get("L2_LOCAL_ROOT")
    if local:
        return Path(local)
    raise FileNotFoundError("L2_RELEASE_MANIFEST.json no encontrado")


@njit(cache=False)
def scan_queue(ev_ts, ev_side, ev_px, ev_sz, k_dec, bid_px, bid_sz, ask_px, ask_sz, tau_us):
    """Por decision y lado, primer fill (indice de evento) bajo 4 modelos. -1 = sin fill.
    lado 0 = compra al mejor bid B; lado 1 = venta al mejor ask A. Orden de 1 contrato al final de la cola."""
    n = len(k_dec)
    out = -np.ones((n, 2, 4), dtype=np.int64)
    N = len(ev_ts)
    for d in range(n):
        k0 = k_dec[d]
        t_lim = ev_ts[k0] + tau_us
        for side in range(2):
            if side == 0:
                L = bid_px[k0]
                q0 = float(bid_sz[k0])
            else:
                L = ask_px[k0]
                q0 = float(ask_sz[k0])
            q_nc = q0            # cola por delante sin cancelaciones por delante
            q_pr = q0            # cola por delante con cancelaciones a prorrata
            sz = q0              # tamano esperado del nivel
            track = True
            f_tt = -1
            f_to = -1
            f_nc = -1
            f_pr = -1
            j = k0 + 1
            while j < N and ev_ts[j] <= t_lim:
                s = ev_side[j]
                p = ev_px[j]
                if s == 2:  # Last
                    v = float(ev_sz[j])
                    if side == 0:
                        through = p < L
                        at = p == L
                    else:
                        through = p > L
                        at = p == L
                    if through:
                        if f_tt < 0:
                            f_tt = j
                        if f_to < 0:
                            f_to = j
                        if f_nc < 0:
                            f_nc = j
                        if f_pr < 0:
                            f_pr = j
                    elif at:
                        if f_to < 0:
                            f_to = j
                        if track:
                            if f_nc < 0:
                                q_nc -= v
                                if q_nc <= -1.0 + 1e-9:      # ejecuciones >= cola por delante + 1 contrato propio
                                    f_nc = j
                            if f_pr < 0:
                                q_pr -= v
                                if q_pr <= -1.0 + 1e-9:
                                    f_pr = j
                            sz -= v
                            if sz < 0.0:
                                sz = 0.0
                else:
                    want = 1 if side == 0 else 0     # el lado del libro que contiene nuestro nivel
                    if s == want:
                        if p == L:
                            if not track:
                                track = True
                                sz = float(ev_sz[j])
                            else:
                                s_new = float(ev_sz[j])
                                if s_new < sz:
                                    c = sz - s_new
                                    if f_pr < 0 and sz > 0.0:
                                        q_pr -= c * (q_pr / sz) if q_pr > 0.0 else 0.0
                                sz = s_new
                        else:
                            track = False
                if f_tt >= 0 and f_to >= 0 and f_nc >= 0 and f_pr >= 0:
                    break
                j += 1
            out[d, side, 0] = f_tt
            out[d, side, 1] = f_to
            out[d, side, 2] = f_nc
            out[d, side, 3] = f_pr
    return out


def load_events(path):
    t = pq.read_table(path, columns=["ts_us", "side", "price_tick", "size"])
    ts = t["ts_us"].to_numpy().astype(np.int64)
    side = t["side"].to_numpy().astype(np.int8)
    px = t["price_tick"].to_numpy().astype(np.int64)
    sz = t["size"].to_numpy().astype(np.int64)
    return ts, side, px, sz


def ffill_quotes(ts, side, px, sz):
    n = len(ts)
    ar = np.arange(n)
    ib = np.maximum.accumulate(np.where(side == SIDE_BID, ar, -1))
    ia = np.maximum.accumulate(np.where(side == SIDE_ASK, ar, -1))
    bid_px = np.where(ib >= 0, px[np.maximum(ib, 0)], 0)
    bid_sz = np.where(ib >= 0, sz[np.maximum(ib, 0)], 0)
    ask_px = np.where(ia >= 0, px[np.maximum(ia, 0)], 0)
    ask_sz = np.where(ia >= 0, sz[np.maximum(ia, 0)], 0)
    return bid_px, bid_sz, ask_px, ask_sz


def process_session(path, acc, samples):
    ts, side, px, sz = load_events(path)
    n = len(ts)
    if n < 100000 or (np.diff(ts) < 0).any():
        return "skip_clock_or_small"
    bid_px, bid_sz, ask_px, ask_sz = ffill_quotes(ts, side, px, sz)
    last_idx = np.where(side == SIDE_LAST)[0]
    if len(last_idx) < 500:
        return "skip_few_last"
    k_all = last_idx[99::100][2:]                      # cada 100 prints Last; se descartan las 2 primeras
    ok = (bid_px[k_all] > 0) & (ask_px[k_all] > bid_px[k_all]) & (bid_sz[k_all] > 0) & (ask_sz[k_all] > 0)
    k_dec = k_all[ok]
    if len(k_dec) == 0:
        return "skip_no_decisions"
    prev_k = last_idx[np.searchsorted(last_idx, k_dec) - 100]       # print Last 100 antes
    prev_dir = np.sign(px[k_dec] - px[prev_k])
    fills = scan_queue(ts, side, px, sz, k_dec, bid_px, bid_sz, ask_px, ask_sz, TAU_US)
    t0 = ts[k_dec]
    t_end = ts[-1]
    B, A = bid_px[k_dec], ask_px[k_dec]
    spread = A - B
    win_ok = (t0 + TAU_US) <= t_end
    midx2 = (bid_px + ask_px).astype(np.float64)       # medios ticks, cotizacion continua
    smask_base = {"ALL": np.ones(len(k_dec), bool), "S2_spread1": spread == 1, "S2_spread2p": spread >= 2}
    for side_i in (0, 1):
        sgn = 1.0 if side_i == 0 else -1.0
        entry_aggr = (A if side_i == 0 else B).astype(np.float64)
        entry_pass = (B if side_i == 0 else A).astype(np.float64)
        with_dir = (prev_dir > 0) if side_i == 0 else (prev_dir < 0)
        against = (prev_dir < 0) if side_i == 0 else (prev_dir > 0)
        smask = dict(smask_base)
        smask["S1_with"], smask["S1_against"] = with_dir, against
        for mi in range(4):
            j = fills[:, side_i, mi]
            filled = (j >= 0) & win_ok
            tf = np.where(j >= 0, ts[np.maximum(j, 0)], 0)
            for hk, hus in HS_US.items():
                th_a, th_p = t0 + hus, tf + hus
                okh = filled & (th_a <= t_end) & (th_p <= t_end)
                ia_ = np.searchsorted(ts, th_a, side="right") - 1
                ip_ = np.searchsorted(ts, np.minimum(th_p, t_end), side="right") - 1
                Ma = sgn * (midx2[np.clip(ia_, 0, n - 1)] / 2.0 - entry_aggr)
                Mp = sgn * (midx2[np.clip(ip_, 0, n - 1)] / 2.0 - entry_pass)
                for sname, sm in smask.items():
                    if not (sname == "ALL" or (mi == PRIMARY_MODEL and hk == 60)):
                        continue
                    m_obs, m_fill = sm & win_ok, sm & filled
                    m_a, m_all = sm & okh, sm & (th_a <= t_end)
                    acc[(mi, hk, sname)].append(np.array([
                        m_obs.sum(), m_fill.sum(), m_a.sum(), 0.0, Mp[m_a].sum(), 0.0,
                        m_all.sum(), Ma[m_all].sum()], dtype=np.float64))
                if mi == PRIMARY_MODEL and hk == 60:
                    samples["Mp"].append(Mp[okh].astype(np.float32))
                    samples["MaAll"].append(Ma[th_a <= t_end].astype(np.float32))
    return "ok"


def cluster_ratio(rows, num_col, den_col):
    R = np.asarray(rows, dtype=np.float64)
    N = R[:, den_col].sum()
    if N <= 0 or len(R) < 2:
        return float("nan"), float("nan")
    m = R[:, num_col].sum() / N
    c = (R[:, num_col] - m * R[:, den_col]) / N
    G = len(R)
    return float(m), math.sqrt((G / (G - 1.0)) * float(np.sum(c * c)))


def astar(rows):
    R = np.asarray(rows, dtype=np.float64)
    nF, sMp, nAll, sMa = R[:, 2], R[:, 4], R[:, 6], R[:, 7]
    NF, NA = nF.sum(), nAll.sum()
    if NF <= 0 or NA <= 0 or len(R) < 2:
        return float("nan"), float("nan"), np.zeros(len(R))
    mMp, mMa = sMp.sum() / NF, sMa.sum() / NA
    c = (sMp - mMp * nF) / NF - (sMa - mMa * nAll) / NA
    G = len(R)
    return float(mMp - mMa), math.sqrt((G / (G - 1.0)) * float(np.sum(c * c))), c


def contrast(r1, r2):
    a1, _, c1 = astar(r1)
    a2, _, c2 = astar(r2)
    c = c1 - c2
    G = len(c)
    se = math.sqrt((G / (G - 1.0)) * float(np.sum(c * c)))
    return float(a1 - a2), se


def summarize(acc):
    out = {}
    for (mi, hk, sname), rows in acc.items():
        F, seF = cluster_ratio(rows, 1, 0)
        Mp, _ = cluster_ratio(rows, 4, 2)
        MaAll, _ = cluster_ratio(rows, 7, 6)
        A, seA, _ = astar(rows)
        out["%s_h%d_%s" % (MODELS[mi], hk, sname)] = {
            "F_fill": F, "se_F": seF, "Mp_ticks": Mp, "MaAll_ticks": MaAll,
            "Astar_ticks": A, "se_Astar": seA,
            "Astar_lo975_onesided": A - 1.96 * seA, "Astar_hi975_onesided": A + 1.96 * seA,
            "value_per_intent_passive_ticks": F * Mp, "n_sessions": len(rows)}
    return out


def causality_test(files, n_cases=300):
    """Perturbar eventos posteriores a t0+tau no cambia el fill (4 modelos)."""
    rng = np.random.default_rng(20261017)
    checked = 0
    ts, side, px, sz = load_events(files[0])
    bid_px, bid_sz, ask_px, ask_sz = ffill_quotes(ts, side, px, sz)
    last_idx = np.where(side == SIDE_LAST)[0]
    k_all = last_idx[99::100][2:]
    ok = (bid_px[k_all] > 0) & (ask_px[k_all] > bid_px[k_all]) & (bid_sz[k_all] > 0) & (ask_sz[k_all] > 0)
    k_all = k_all[ok]
    for k in rng.choice(k_all, size=min(n_cases, len(k_all)), replace=False):
        a = scan_queue(ts, side, px, sz, np.array([k], dtype=np.int64), bid_px, bid_sz, ask_px, ask_sz, TAU_US)
        m = ts > ts[k] + TAU_US
        px2, sz2 = px.copy(), sz.copy()
        px2[m] = -10 ** 6
        sz2[m] = 10 ** 6
        b = scan_queue(ts, side, px2, sz2, np.array([k], dtype=np.int64), bid_px, bid_sz, ask_px, ask_sz, TAU_US)
        assert np.array_equal(a, b), "FILL L2 NO CAUSAL k=%d" % k
        checked += 1
    return {"n_cases": checked, "max_abs_diff": 0.0}


def select_files(root, man):
    by_date = defaultdict(list)
    flagged = {(f["contract"], f["session"]) for f in man.get("flagged_sessions", [])}
    for s in man["sessions"]:
        d = s["session"]
        if not (START <= d <= END):
            continue
        if (s["contract"], d) in flagged or s["qa"].get("fast_book_status") != "PASS":
            continue
        by_date[d].append(s)
    files = []
    for d in sorted(by_date):
        s = max(by_date[d], key=lambda x: x["qa"].get("l2_events", 0))
        files.append((d, s["contract"], root / s["files"]["l1_quotes"]))
    return files


def main():
    t0 = time.time()
    root = find_root()
    man = json.loads((root / "L2_RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    assert man["instrument"] == "ES"
    sel = select_files(root, man)
    assert all(d < "20261001" for d, _, _ in sel), "HOLDOUT"
    print("F0C sesiones candidatas:", len(sel), flush=True)
    paths = [p for _, _, p in sel]
    caus = causality_test(paths[:1])
    print("F0C_CAUSALITY_PASS", json.dumps(caus), flush=True)

    # hora de inicio de sesion (modo) para descartar relojes corridos
    starts = []
    for d, c, p in sel:
        tcol = pq.read_table(p, columns=["ts_us"])["ts_us"]
        # sesiones vacias o casi vacias (feriados/fines de semana marcados PASS): sin hora de inicio, se saltean
        starts.append(int(tcol[0].as_py()) % 86_400_000_000 if len(tcol) >= 100000 else -1)
    valid_starts = np.asarray([x for x in starts if x >= 0])
    modal = int(np.bincount((valid_starts // 60_000_000).astype(int)).argmax()) * 60_000_000
    acc, samples = defaultdict(list), {"Mp": [], "MaAll": []}
    statuses = defaultdict(int)
    used = []
    for (d, c, p), st in zip(sel, starts):
        if st < 0:
            statuses["skip_empty_session"] += 1
            continue
        if abs(st - modal) > 600_000_000:
            statuses["skip_clock_shifted"] += 1
            continue
        r = process_session(p, acc, samples)
        statuses[r] += 1
        if r == "ok":
            used.append((d, c))
        if len(used) % 20 == 0 and r == "ok":
            print("F0C sesiones", len(used), "t=%.0fs" % (time.time() - t0), flush=True)
    print("F0C estados", dict(statuses), flush=True)
    if len(used) < 50:
        print("F0C_ABORT_SESSIONS_INSUFFICIENT", len(used), flush=True)
        return

    S = summarize(acc)
    pk = "Q_PRORATA_h60_ALL"
    prim = S[pk]
    cont, pv = {}, []
    for nm, a, b in (("S1_against_vs_with", "S1_against", "S1_with"), ("S2_spread1_vs_2p", "S2_spread1", "S2_spread2p")):
        d_, se_ = contrast(acc[(PRIMARY_MODEL, 60, a)], acc[(PRIMARY_MODEL, 60, b)])
        z = d_ / se_ if se_ > 0 else float("nan")
        p = float(math.erfc(abs(z) / math.sqrt(2.0))) if z == z else float("nan")
        cont[nm] = {"diff_Astar": d_, "se": se_, "z": z, "p_raw": p}
        pv.append((nm, p))
    for rank, (nm, p) in enumerate(sorted([x for x in pv if x[1] == x[1]], key=lambda x: x[1])):
        cont[nm]["p_holm"] = min(1.0, p * (len(pv) - rank))
    F, lo, hi = prim["F_fill"], prim["Astar_lo975_onesided"], prim["Astar_hi975_onesided"]
    verdict = "PASIVO_RECUPERA_L2" if (F >= 0.30 and lo > 0.25) else (
        "PASIVO_NO_CONVIENE_L2" if (hi < 0.25 or F < 0.10) else "ABSTENCION")
    qs = (5, 25, 50, 75, 95)
    Mp_all = np.concatenate(samples["Mp"]) if samples["Mp"] else np.zeros(0)
    Ma_all = np.concatenate(samples["MaAll"]) if samples["MaAll"] else np.zeros(0)
    summary = {
        "spec_id": "EXP-F0C-EJECUCION-PASIVA-ES-L1COLA-V1", "manifest_section": 13,
        "window": [START, END], "n_sessions_used": len(used), "session_status": dict(statuses),
        "holdout_touched": False, "causality": caus, "VERDICT_PRIMARY": verdict,
        "primary_Q_PRORATA_tau60_h60": prim, "conservative_Q_NOCANCEL_tau60_h60": S["Q_NOCANCEL_h60_ALL"],
        "consistency_TT": S["TT_h60_ALL"], "bound_TOUCH": S["TOUCH_h60_ALL"],
        "contrasts_holm2": cont,
        "dist_primary": {"Mp_q": [float(np.percentile(Mp_all, q)) for q in qs] if len(Mp_all) else [],
                         "MaAll_q": [float(np.percentile(Ma_all, q)) for q in qs] if len(Ma_all) else []},
        "grid": S, "elapsed_seconds": round(time.time() - t0, 1)}
    print("=== EXP_F0C_SUMMARY_START ===", flush=True)
    print(json.dumps(summary, indent=1, default=float), flush=True)
    print("=== EXP_F0C_SUMMARY_END ===", flush=True)
    out = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "EXP_F0C_L1COLA_RESULTS.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
