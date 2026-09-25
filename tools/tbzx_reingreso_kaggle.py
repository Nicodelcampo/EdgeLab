#!/usr/bin/env python3
r"""TBZX-R3: se crea la zona -> se aleja D -> vuelve -> se introduce p -> retrocede r -> entrada con TP 3 ticks.

Manifiesto: docs/research/MANIFIESTO_TBZX_REINGRESO_3T_20260925.md (escrito antes de medir).
Autocontenido para correr como kernel de Kaggle sobre nicolasbuttaro/edgelab-ticks-es-preholdout.
Variables: R3_MAXSESS (prueba corta), R3_OUT (carpeta de salida).
"""
from __future__ import annotations

import glob
import json
import os
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from numba import njit

NS = 1_000_000_000
INST = "ES"
# exploración: sesiones con trade_date 2025-07-01 .. 2026-03-31 (17:00 ET = 21:00Z en marzo, EDT)
T_LO = int(pd.Timestamp("2025-06-30 22:00", tz="UTC").value)
T_HI = int(pd.Timestamp("2026-03-31 21:00", tz="UTC").value)
TD_LO, TD_HI = "20250701", "20260331"
HOLDOUT_NS = int(pd.Timestamp("2026-04-01", tz="UTC").value)  # nada de confirmación ni holdout
ET = "America/New_York"

GRID = [(mb, mw) for mb in (10, 20, 40) for mw in (8, 12, 17, 24)]
E0, R_END = 0.6, 0.3
DS = np.array([2, 4, 8, 12, 20], np.int64)
P_TICKS = [0, 1, 2, 3, 4, 6, 8, 12]
P_FRAC = [0.25, 0.5, 0.75]
NP = len(P_TICKS) + len(P_FRAC)
RS = np.array([0, 1, 2, 3, 4], np.int64)
SLS = np.array([2, 3, 4, 6, 8], np.int64)
TP = 3
HZ_S = 7200          # horizonte para alejarse y volver
WAIT_S = 30          # espera del retroceso
HOLD_S = 300         # salida por tiempo
LAT_NS = 250_000_000
PASS_T_S = 30        # ventana de la límite pasiva
COMM = 0.2           # ticks por lado (ES)
EXECS = ("perfecta", "realista", "agresiva")
MIN_ZONES_PER_SESS = 2.0
MIN_N = 100
N_BOOT = 1000
SEED = 20260925
TOD_TOL_S = 900

NC, NSIDE, ND, NR, NDIR, NSL, NEX, NNULL = len(GRID), 2, len(DS), len(RS), 2, len(SLS), len(EXECS), 2
SHAPE = (NC, NSIDE, ND, NP, NR, NDIR, NSL, NEX, NNULL)
NCELL = int(np.prod(SHAPE))


# ------------------------------------------------------------------ datos
def find_files():
    fs = sorted(glob.glob("/kaggle/input/**/ES_*_ticks.parquet", recursive=True))
    if not fs:
        fs = sorted(glob.glob(os.environ.get("R3_DATA", "data") + "/ES_*_ticks.parquet"))
    return [f for f in fs if "_09-26_" not in f]   # contrato sin sesiones de exploración


def trade_dates(ts):
    """trade_date CME (sesión 18:00 ET -> 17:00 ET) y segundos ET del día, por minuto único."""
    m = ts // (60 * NS)
    um, inv = np.unique(m, return_inverse=True)
    t = pd.to_datetime(um * 60 * NS, utc=True).tz_convert(ET)
    nxt = (t + pd.Timedelta(hours=6)).strftime("%Y%m%d").astype(int).to_numpy()   # 18:00 ET -> día siguiente
    off = (t.tz_localize(None) - pd.to_datetime(um * 60 * NS)).total_seconds().to_numpy().astype(np.int64)
    return nxt[inv], off[inv]


def load_sessions(maxsess):
    best = {}
    for f in find_files():
        tb = pq.read_table(f, columns=["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "contract"],
                           filters=[("ts_utc_ns", ">=", T_LO), ("ts_utc_ns", "<", T_HI)])
        if tb.num_rows == 0:
            continue
        ts = tb.column("ts_utc_ns").to_numpy().astype(np.int64)
        if ts.max() >= HOLDOUT_NS:
            raise ValueError("fuera de la partición de exploración")
        cc = tb.column("contract").dictionary_encode().combine_chunks()
        names = [str(x) for x in cc.dictionary.to_pylist()]
        code = cc.indices.to_numpy().astype(np.int64)
        px = tb.column("price_ticks").to_numpy().astype(np.int64)
        vol = tb.column("volume").to_numpy().astype(np.float64)
        bid = tb.column("bid_ticks").to_numpy().astype(np.int64)
        ask = tb.column("ask_ticks").to_numpy().astype(np.int64)
        del tb
        td, off = trade_dates(ts)
        key = td * 64 + code
        order = np.argsort(key, kind="stable")
        uk, cnt = np.unique(key[order], return_counts=True)
        pos = np.concatenate(([0], np.cumsum(cnt)))
        for i, k in enumerate(uk):
            d, c = str(k // 64), names[k % 64]
            if not (TD_LO <= d <= TD_HI) or cnt[i] < 5000:
                continue
            if d in best and best[d]["n"] >= cnt[i]:
                continue
            ix = order[pos[i]:pos[i + 1]]
            ix = ix[np.argsort(ts[ix], kind="stable")]
            best[d] = dict(td=d, contract=c, n=int(cnt[i]), ts=ts[ix], px=px[ix], vol=vol[ix], bid=bid[ix],
                           ask=ask[ix], off=int(off[ix[0]]))
        print(f, "leido", len(best), "sesiones", flush=True)
        del ts, code, px, vol, bid, ask, td, off, key, order
    ss = [best[d] for d in sorted(best)]
    if maxsess:
        ss = ss[:maxsess]
    return ss


def bars25(s):
    n = len(s["px"]); nb = (n + 24) // 25
    idx = np.arange(n) // 25
    end = np.minimum(np.arange(1, nb + 1) * 25, n) - 1
    H = np.maximum.reduceat(s["px"], np.arange(0, n, 25)).astype(np.float64)
    L = np.minimum.reduceat(s["px"], np.arange(0, n, 25)).astype(np.float64)
    C = s["px"][end].astype(np.float64)
    V = np.bincount(idx, weights=s["vol"], minlength=nb)
    t = s["ts"][end] / NS
    return t, H, L, C, V, end


# ------------------------------------------------------------------ detector (port exacto del visor, EDGELAB_TBZX_DESIGNER_V1)
@njit(cache=True)
def detect(t, H, L, C, V, W, minW, e0, r):
    n = len(C)
    path = np.zeros(n)
    for i in range(1, n):
        path[i] = path[i - 1] + abs(C[i] - C[i - 1])
    out = np.zeros((n // 2 + 1, 9))
    m = 0
    active = False
    floorI = 0
    d = 0; i0 = 0; a = 0.0; ext = 0.0; iext = 0; itrig = 0; vol = 0.0
    for j in range(W, n):
        if t[j] - t[j - 1] > 1800:
            active = False
        if not active:
            w0 = max(j - W, floorI)
            if w0 >= j:
                continue
            thr = max(float(minW), 2.0)
            ia = w0; ib = w0
            for q in range(w0, j + 1):
                if L[q] < L[ia]:
                    ia = q
                if H[q] > H[ib]:
                    ib = q
            found = False; bnet = 0.0
            if ia < j:
                net = C[j] - L[ia]; pp = path[j] - path[ia]
                if net >= thr and pp > 0 and (C[j] - C[ia]) / pp >= e0:
                    found = True; bnet = net; d = 1; i0 = ia; a = L[ia]; ext = H[j]
            if ib < j:
                net2 = H[ib] - C[j]; pp2 = path[j] - path[ib]
                if net2 >= thr and pp2 > 0 and (C[ib] - C[j]) / pp2 >= e0 and ((not found) or net2 > bnet):
                    found = True; d = -1; i0 = ib; a = H[ib]; ext = L[j]
            if found:
                active = True; iext = j; itrig = j; vol = 0.0
                for q in range(i0 + 1, j + 1):
                    vol += V[q]
            continue
        if d == 1 and H[j] > ext:
            ext = H[j]; iext = j
        elif d == -1 and L[j] < ext:
            ext = L[j]; iext = j
        vol += V[j]
        tot = abs(ext - a)
        retr = (ext - L[j]) if d == 1 else (H[j] - ext)
        why = 0
        if retr >= max(2.0, r * tot):
            why = 1
        elif j - i0 >= W:
            why = 2
        if why == 0:
            continue
        if tot >= minW:
            out[m, 0] = d; out[m, 1] = a; out[m, 2] = ext; out[m, 3] = i0; out[m, 4] = iext; out[m, 5] = j
            out[m, 6] = itrig; out[m, 7] = vol; out[m, 8] = why
            m += 1
        floorI = iext
        active = False
    return out[:m]


# ------------------------------------------------------------------ secuencia: alejarse D, volver, penetrar p, retroceder r
@njit(cache=True)
def zone_triggers(ts, px, k0, lo, hi, dimp, depth, Ds, Rs, hz_ns, wait_ns):
    """Devuelve filas (iD, ip, ir, side_B, up, k_trigger, precio_disparo). depth[ip] < 0 = nivel no válido."""
    n = len(px)
    nD = len(Ds); nP = len(depth); nR = len(Rs)
    out = np.zeros((nD * nP * nR, 7), np.int64)
    m = 0
    tend = ts[k0] + hz_ns
    W = hi - lo
    for iD in range(nD):
        D = Ds[iD]
        kx = -1; up = False
        for k in range(k0 + 1, n):
            if ts[k] > tend:
                break
            if px[k] >= hi + D:
                kx = k; up = True; break
            if px[k] <= lo - D:
                kx = k; up = False; break
        if kx < 0:
            continue
        sideB = 1 if (up == (dimp == 1)) else 0
        # primeros toques de cada profundidad; el borde opuesto corta
        kp = np.full(nP, -1, np.int64)
        left = 0
        for ip in range(nP):
            if depth[ip] >= 0:
                left += 1
        for k in range(kx + 1, n):
            if ts[k] > tend or left == 0:
                break
            dep = (hi - px[k]) if up else (px[k] - lo)
            if dep >= W:
                break
            for ip in range(nP):
                if depth[ip] >= 0 and kp[ip] < 0 and dep >= depth[ip]:
                    kp[ip] = k; left -= 1
        for ip in range(nP):
            k1 = kp[ip]
            if k1 < 0:
                continue
            lvl = (hi - depth[ip]) if up else (lo + depth[ip])
            for ir in range(nR):
                r = Rs[ir]
                if r == 0:
                    out[m, 0] = iD; out[m, 1] = ip; out[m, 2] = ir; out[m, 3] = sideB; out[m, 4] = 1 if up else 0
                    out[m, 5] = k1; out[m, 6] = lvl; m += 1
                    continue
                deep = px[k1]
                for k in range(k1 + 1, n):
                    if ts[k] - ts[k1] > wait_ns:
                        break
                    if (up and px[k] <= lo) or ((not up) and px[k] >= hi):
                        break
                    if up:
                        if px[k] < deep:
                            deep = px[k]
                        if px[k] >= deep + r:
                            out[m, 0] = iD; out[m, 1] = ip; out[m, 2] = ir; out[m, 3] = sideB; out[m, 4] = 1
                            out[m, 5] = k; out[m, 6] = deep + r; m += 1
                            break
                    else:
                        if px[k] > deep:
                            deep = px[k]
                        if px[k] <= deep - r:
                            out[m, 0] = iD; out[m, 1] = ip; out[m, 2] = ir; out[m, 3] = sideB; out[m, 4] = 0
                            out[m, 5] = k; out[m, 6] = deep - r; m += 1
                            break
    return out[:m]


@njit(cache=True)
def exits(ts, px, bid, ask, k0, E, q, SLs, tp, hold_ns, perfect, comm, pnl, hit, ie, idir):
    n = len(px)
    nS = len(SLs)
    done = np.zeros(nS, np.bool_)
    left = nS
    tlim = ts[k0] + hold_ns
    k = k0
    last = k0
    while k + 1 < n and left > 0:
        k += 1
        if ts[k] > tlim:
            break
        last = k
        mv = q * (px[k] - E)
        for i in range(nS):
            if done[i]:
                continue
            if (perfect and mv >= tp) or ((not perfect) and mv >= tp + 1):
                pnl[i, idir, ie] = tp; hit[i, idir, ie] = 1; done[i] = True; left -= 1
            elif mv <= -SLs[i]:
                if perfect:
                    pnl[i, idir, ie] = -SLs[i]
                else:
                    xp = bid[k] if q > 0 else ask[k]
                    pnl[i, idir, ie] = q * (xp - E)
                done[i] = True; left -= 1
    for i in range(nS):
        if not done[i]:
            if perfect:
                pnl[i, idir, ie] = q * (px[last] - E)
            else:
                xp = bid[last] if q > 0 else ask[last]
                pnl[i, idir, ie] = q * (xp - E)
    if not perfect:
        for i in range(nS):
            pnl[i, idir, ie] -= 2 * comm


@njit(cache=True)
def simulate(ts, px, bid, ask, k_t, lvl, up, SLs, tp, hold_ns, lat_ns, pass_ns, comm):
    """pnl/hit [nSL, dir(0=sigue,1=rebota), exec(0=perfecta,1=realista,2=agresiva)]."""
    nS = len(SLs)
    pnl = np.zeros((nS, 2, 3)); hit = np.zeros((nS, 2, 3))
    n = len(px)
    ka = k_t
    while ka + 1 < n and ts[ka] < ts[k_t] + lat_ns:
        ka += 1
    for idir in range(2):
        q = (-1 if up else 1) if idir == 0 else (1 if up else -1)
        # perfecta = sin slippage al precio del trade que dispara (no al nivel: si el trade lo saltó, entrar en el
        # nivel regala ticks; detectado en la prueba sintética)
        exits(ts, px, bid, ask, k_t, px[k_t], q, SLs, tp, hold_ns, True, 0.0, pnl, hit, 0, idir)
        Ea = ask[ka] if q > 0 else bid[ka]
        exits(ts, px, bid, ask, ka, Ea, q, SLs, tp, hold_ns, False, comm, pnl, hit, 2, idir)
        L = bid[ka] if q > 0 else ask[ka]
        kf = -1; k = ka
        while k + 1 < n:
            k += 1
            if ts[k] - ts[ka] > pass_ns:
                break
            if (q > 0 and px[k] < L) or (q < 0 and px[k] > L):
                kf = k; break
        if kf >= 0:
            exits(ts, px, bid, ask, kf, L, q, SLs, tp, hold_ns, False, comm, pnl, hit, 1, idir)
        else:
            kc = min(k, n - 1)
            Ec = ask[kc] if q > 0 else bid[kc]
            exits(ts, px, bid, ask, kc, Ec, q, SLs, tp, hold_ns, False, comm, pnl, hit, 1, idir)
    return pnl, hit


@njit(cache=True)
def simulate_many(ts, px, bid, ask, TR, SLs, tp, hold_ns, lat_ns, pass_ns, comm):
    m = len(TR)
    P = np.zeros((m, len(SLs), 2, 3)); Hh = np.zeros((m, len(SLs), 2, 3))
    for i in range(m):
        pnl, hit = simulate(ts, px, bid, ask, TR[i, 5], TR[i, 6], TR[i, 4] == 1, SLs, tp, hold_ns, lat_ns, pass_ns, comm)
        P[i] = pnl; Hh[i] = hit
    return P, Hh


def depths(W):
    d = [p if p < W else -1 for p in P_TICKS] + [int(round(f * W)) if 1 <= round(f * W) < W else -1 for f in P_FRAC]
    return np.array(d, np.int64)


# ------------------------------------------------------------------ corrida
def run():
    out_dir = os.environ.get("R3_OUT", "/kaggle/working")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    ss = load_sessions(int(os.environ.get("R3_MAXSESS", "0")))
    S = len(ss)
    print("sesiones", S, ss[0]["td"], ss[-1]["td"], f"{time.time() - t0:.0f}s", flush=True)
    rng = np.random.default_rng(SEED)
    tods = [((s["ts"] // NS + s["off"]) % 86400) for s in ss]
    agg = np.zeros((S, NCELL, 3), np.float32)       # n, suma pnl, suma aciertos
    zcount = np.zeros((S, NC), np.int64)
    ntrig = np.zeros((S, NC, NNULL), np.int64)
    strides = np.array([int(np.prod(SHAPE[i + 1:])) for i in range(len(SHAPE))], np.int64)
    ii = np.indices((NSL, NDIR, NEX)).reshape(3, -1)   # orden del bloque de simulate
    for si, s in enumerate(ss):
        ts, px, bid, ask = s["ts"], s["px"], s["bid"], s["ask"]
        t, H, L, C, V, bend = bars25(s)
        for ci, (mb, mw) in enumerate(GRID):
            Z = detect(t, H, L, C, V, mb, mw, E0, R_END)
            zcount[si, ci] = len(Z)
            for z in Z:
                d, a, b, j = int(z[0]), int(z[1]), int(z[2]), int(z[5])
                lo, hi = min(a, b), max(a, b)
                k0 = int(bend[j])
                dep = depths(hi - lo)
                # real y un fantasma: otra sesión, misma hora ET +-15 min, geometría relativa al último trade
                cands = [(0, ts, px, bid, ask, k0, lo, hi)]
                for _ in range(8):
                    oi = int(rng.integers(0, S))
                    if oi == si:
                        continue
                    tod = (ts[k0] // NS + s["off"]) % 86400 + int(rng.integers(-TOD_TOL_S, TOD_TOL_S + 1))
                    ko = int(np.argmin(np.abs(tods[oi] - tod)))
                    if abs(int(tods[oi][ko]) - tod) > TOD_TOL_S or ko >= len(ss[oi]["px"]) - 100:
                        continue
                    o = ss[oi]; sh = int(o["px"][ko]) - int(px[k0])
                    cands.append((1, o["ts"], o["px"], o["bid"], o["ask"], ko, lo + sh, hi + sh))
                    break
                for nul, T_, P_, B_, A_, kk, l_, h_ in cands:
                    TR = zone_triggers(T_, P_, kk, l_, h_, d, dep, DS, RS, HZ_S * NS, WAIT_S * NS)
                    ntrig[si, ci, nul] += len(TR)
                    if len(TR) == 0:
                        continue
                    pnl, hit = simulate_many(T_, P_, B_, A_, TR, SLS, TP, HOLD_S * NS, LAT_NS, PASS_T_S * NS, COMM)
                    base = (ci * strides[0] + (1 - TR[:, 3]) * strides[1] + TR[:, 0] * strides[2]
                            + TR[:, 1] * strides[3] + TR[:, 2] * strides[4])
                    cell = (base[:, None] + (ii[1] * strides[5] + ii[0] * strides[6] + ii[2] * strides[7] + nul)[None, :]).ravel()
                    np.add.at(agg[si, :, 0], cell, 1)
                    np.add.at(agg[si, :, 1], cell, pnl.reshape(-1))
                    np.add.at(agg[si, :, 2], cell, hit.reshape(-1))
        print(si, s["td"], "zonas", zcount[si].sum(), "disparos", ntrig[si].sum(), f"{time.time() - t0:.0f}s", flush=True)
    np.savez_compressed(f"{out_dir}/r3_agg.npz", agg=agg, zcount=zcount, ntrig=ntrig,
                        tds=np.array([s["td"] for s in ss]))
    report(agg, zcount, ntrig, [s["td"] for s in ss], out_dir)
    print("listo", f"{time.time() - t0:.0f}s", flush=True)


def bh(p, q):
    p = np.asarray(p); m = len(p)
    if m == 0:
        return np.zeros(0, bool)
    o = np.argsort(p); thr = q * np.arange(1, m + 1) / m
    ok = p[o] <= thr
    k = np.max(np.nonzero(ok)[0]) + 1 if ok.any() else 0
    res = np.zeros(m, bool); res[o[:k]] = True
    return res


def report(agg, zcount, ntrig, tds, out_dir):
    S = agg.shape[0]
    zps = zcount.mean(0)
    keep_cfg = zps >= MIN_ZONES_PER_SESS
    A = agg.reshape((S,) + SHAPE + (3,))
    rng = np.random.default_rng(SEED)
    Wb = np.stack([np.bincount(rng.integers(0, S, S), minlength=S) for _ in range(N_BOOT)]).astype(np.float32)
    months = np.array([td[:6] for td in tds])
    rows = []
    for ci, (mb, mw) in enumerate(GRID):
        if not keep_cfg[ci]:
            continue
        R = A[:, ci]          # S, side, D, P, R, dir, SL, ex, null, 3
        flat = R.reshape(S, -1, NNULL, 3)
        n_r = flat[:, :, 0, 0]; n_f = flat[:, :, 1, 0]
        tot = n_r.sum(0)
        idx = np.nonzero(tot >= MIN_N)[0]
        if len(idx) == 0:
            continue
        def stat(col, nul):
            num = flat[:, idx, nul, col]; den = flat[:, idx, nul, 0]
            pt = num.sum(0) / np.maximum(den.sum(0), 1)
            bt = (Wb @ num) / np.maximum(Wb @ den, 1)
            return pt, bt
        pr, prb = stat(1, 0); hr, hrb = stat(2, 0); pf, pfb = stat(1, 1); hf, hfb = stat(2, 1)
        nf = n_f.sum(0)[idx]
        sub = np.array(np.unravel_index(idx, SHAPE[1:-1]))  # side, D, P, R, dir, SL, ex
        sl = SLS[sub[5]]
        p0 = sl / (sl + TP)
        # meses positivos (P&L real)
        mpos = np.zeros(len(idx))
        um = np.unique(months)
        pm = np.stack([flat[months == m_][:, idx, 0, 1].sum(0) for m_ in um])
        nm = np.stack([flat[months == m_][:, idx, 0, 0].sum(0) for m_ in um])
        valid = nm > 0
        mpos = ((pm > 0) & valid).sum(0) / np.maximum(valid.sum(0), 1)
        for j in range(len(idx)):
            side, iD, ip, ir, dr, isl, ex = (int(x) for x in sub[:, j])
            ptag = f"{P_TICKS[ip]}t" if ip < len(P_TICKS) else f"{P_FRAC[ip - len(P_TICKS)]}W"
            dh = hrb[:, j] - p0[j]
            dhf = hrb[:, j] - hfb[:, j] if nf[j] >= MIN_N else np.full(N_BOOT, np.nan)
            rows.append(dict(
                cfg=f"mb{mb}_mw{mw}", lado="B" if side == 0 else "A", D=int(DS[iD]), p=ptag, r=int(RS[ir]),
                dir="sigue" if dr == 0 else "rebota", SL=int(sl[j]), exec=EXECS[ex], n=int(tot[idx[j]]),
                hit=float(hr[j]), p0=float(p0[j]), hit_lo=float(np.quantile(hrb[:, j], .025)),
                hit_hi=float(np.quantile(hrb[:, j], .975)), exc_N1=float(hr[j] - p0[j]),
                exc_N1_lo=float(np.quantile(dh, .025)), p_N1=float((dh <= 0).mean()),
                pnl=float(pr[j]), pnl_lo=float(np.quantile(prb[:, j], .025)), pnl_hi=float(np.quantile(prb[:, j], .975)),
                p_pnl=float((prb[:, j] <= 0).mean()),
                n_fant=int(nf[j]), hit_fant=float(hf[j]) if nf[j] else np.nan, pnl_fant=float(pf[j]) if nf[j] else np.nan,
                exc_fant=float(hr[j] - hf[j]) if nf[j] else np.nan,
                exc_fant_lo=float(np.nanquantile(dhf, .025)) if nf[j] >= MIN_N else np.nan,
                p_fant=float((dhf <= 0).mean()) if nf[j] >= MIN_N else np.nan,
                meses_pos=float(mpos[j])))
    D = pd.DataFrame(rows)
    D["fdr"] = False; D["sugerencia"] = False
    prim = (D["exec"] == "perfecta") & (D.SL == 3)
    D.loc[prim, "fdr"] = bh(np.maximum(D.loc[prim, "p_N1"], D.loc[prim, "p_fant"].fillna(1)), 0.10)
    sec = D["exec"] == "realista"
    D.loc[sec, "fdr"] = bh(D.loc[sec, "p_pnl"], 0.10)
    D.loc[prim, "sugerencia"] = D.loc[prim, "fdr"] & (D.loc[prim, "exc_N1_lo"] > 0) & (D.loc[prim, "exc_fant_lo"] > 0) \
        & (D.loc[prim, "meses_pos"] >= 0.55)
    D.loc[sec, "sugerencia"] = D.loc[sec, "fdr"] & (D.loc[sec, "pnl_lo"] > 0) & (D.loc[sec, "exc_fant_lo"] > 0) \
        & (D.loc[sec, "meses_pos"] >= 0.55)
    D.to_csv(f"{out_dir}/r3_celdas.csv", index=False)
    summ = dict(
        sesiones=int(S), desde=tds[0], hasta=tds[-1],
        zonas_por_sesion={f"mb{mb}_mw{mw}": float(zps[i]) for i, (mb, mw) in enumerate(GRID)},
        configs_usadas=[f"mb{mb}_mw{mw}" for i, (mb, mw) in enumerate(GRID) if keep_cfg[i]],
        disparos_real=int(ntrig[:, :, 0].sum()), disparos_fantasma=int(ntrig[:, :, 1].sum()),
        celdas=int(len(D)), celdas_primarias=int(prim.sum()), celdas_realistas=int(sec.sum()),
        fdr_primaria=int(D.loc[prim, "fdr"].sum()), fdr_realista=int(D.loc[sec, "fdr"].sum()),
        sugerencias=int(D.sugerencia.sum()),
        top_primaria=D[prim].sort_values("exc_N1", ascending=False).head(15).to_dict("records"),
        top_realista=D[sec].sort_values("pnl", ascending=False).head(15).to_dict("records"),
        sugerencias_lista=D[D.sugerencia].to_dict("records"))
    with open(f"{out_dir}/r3_resumen.json", "w") as fh:
        json.dump(summ, fh, indent=1, default=float)
    print(json.dumps({k: v for k, v in summ.items() if not k.startswith("top") and k != "sugerencias_lista"}, indent=1))


if __name__ == "__main__":
    run()
