#!/usr/bin/env python3
r"""TBZX-R3: se crea la zona -> se aleja D -> vuelve -> se introduce p -> retrocede r -> entrada; TP y SL en {3, 6, 10, 20}.

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
RS = np.array([0, 2, 4], np.int64)          # iteración 3: los dos patrones vistos (r = 0 y r >= 2)
_K = [(sl, tp) for sl in (3, 6, 10, 20) for tp in (3, 6, 10, 20)]
SLC = np.array([k[0] for k in _K], np.int64)
TPC = np.array([k[1] for k in _K], np.int64)
HZ_S = 7200          # horizonte para alejarse y volver
WAIT_S = 30          # espera del retroceso
HOLD_S = 1800        # salida por tiempo (iteración 3: TP hasta 20)
LAT_NS = 250_000_000
PASS_T_S = 30        # ventana de la límite pasiva
COMM = 0.2           # ticks por lado (ES)
EXECS = ("perfecta", "realista", "agresiva", "perfecta_mid")
MIN_ZONES_PER_SESS = 2.0
MIN_N = 100
N_BOOT = 1000
SEED = 20260925
TOD_TOL_S = 900
N_PH = 3             # fantasmas por zona (iteración 2)

NC, NSIDE, ND, NR, NDIR, NSL, NEX, NNULL = len(GRID), 2, len(DS), len(RS), 2, len(SLC), len(EXECS), 2
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
def exits(ts, px, bid, ask, k0, E, q, SLc, TPc, hold_ns, perfect, comm, pnl, hit, ie, idir, sc):
    """Una pasada: primer tick en que la excursión a favor/en contra llega a cada nivel; resuelve todos los (SL, TP).
    sc = 2 cuando px es el medio en medios ticks. Realista: el TP hay que atravesarlo por 1 tick; el SL sale al
    precio contrario del libro en ese trade."""
    n = len(px); nK = len(SLc)
    extra = 0 if perfect else 1
    mtp = int(TPc.max()) * sc + extra; msl = int(SLc.max()) * sc
    fav = np.full(mtp + 1, -1, np.int64); adv = np.full(msl + 1, -1, np.int64)
    best = 0; worst = 0
    tlim = ts[k0] + hold_ns
    k = k0; last = k0
    while k + 1 < n:
        k += 1
        if ts[k] > tlim:
            break
        last = k
        mv = q * (px[k] - E)
        if mv > best:
            for j in range(best + 1, min(mv, mtp) + 1):
                fav[j] = k
            best = mv
        if -mv > worst:
            for j in range(worst + 1, min(-mv, msl) + 1):
                adv[j] = k
            worst = -mv
        if best >= mtp and worst >= msl:
            break
    for i in range(nK):
        kt = fav[TPc[i] * sc + extra]; ks = adv[SLc[i] * sc]
        if kt >= 0 and (ks < 0 or kt < ks):
            pnl[i, idir, ie] = TPc[i]; hit[i, idir, ie] = 1
        elif ks >= 0:
            if perfect:
                pnl[i, idir, ie] = -SLc[i]
            else:
                xp = bid[ks] if q > 0 else ask[ks]
                pnl[i, idir, ie] = q * (xp - E)
        else:
            if perfect:
                pnl[i, idir, ie] = q * (px[last] - E) / sc
            else:
                xp = bid[last] if q > 0 else ask[last]
                pnl[i, idir, ie] = q * (xp - E)
        if not perfect:
            pnl[i, idir, ie] -= 2 * comm


@njit(cache=True)
def simulate(ts, px, bid, ask, mid2, k_t, lvl, up, SLs, TPs, hold_ns, lat_ns, pass_ns, comm):
    """pnl/hit [nSL, dir(0=sigue,1=rebota), exec(0=perfecta,1=realista,2=agresiva)]."""
    nS = len(SLs)
    pnl = np.zeros((nS, 2, 4)); hit = np.zeros((nS, 2, 4))
    n = len(px)
    ka = k_t
    while ka + 1 < n and ts[ka] < ts[k_t] + lat_ns:
        ka += 1
    for idir in range(2):
        q = (-1 if up else 1) if idir == 0 else (1 if up else -1)
        # perfecta = sin slippage al precio del trade que dispara (no al nivel: si el trade lo saltó, entrar en el
        # nivel regala ticks; detectado en la prueba sintética)
        exits(ts, px, bid, ask, k_t, px[k_t], q, SLs, TPs, hold_ns, True, 0.0, pnl, hit, 0, idir, 1)
        # perfecta sobre el precio medio (en medios ticks): sin rebote bid/ask (iteración 2)
        exits(ts, mid2, bid, ask, k_t, mid2[k_t], q, SLs, TPs, hold_ns, True, 0.0, pnl, hit, 3, idir, 2)
        Ea = ask[ka] if q > 0 else bid[ka]
        exits(ts, px, bid, ask, ka, Ea, q, SLs, TPs, hold_ns, False, comm, pnl, hit, 2, idir, 1)
        L = bid[ka] if q > 0 else ask[ka]
        kf = -1; k = ka
        while k + 1 < n:
            k += 1
            if ts[k] - ts[ka] > pass_ns:
                break
            if (q > 0 and px[k] < L) or (q < 0 and px[k] > L):
                kf = k; break
        if kf >= 0:
            exits(ts, px, bid, ask, kf, L, q, SLs, TPs, hold_ns, False, comm, pnl, hit, 1, idir, 1)
        else:
            kc = min(k, n - 1)
            Ec = ask[kc] if q > 0 else bid[kc]
            exits(ts, px, bid, ask, kc, Ec, q, SLs, TPs, hold_ns, False, comm, pnl, hit, 1, idir, 1)
    return pnl, hit


@njit(cache=True)
def simulate_many(ts, px, bid, ask, TR, SLs, TPs, hold_ns, lat_ns, pass_ns, comm):
    m = len(TR)
    P = np.zeros((m, len(SLs), 2, 4)); Hh = np.zeros((m, len(SLs), 2, 4))
    mid2 = bid + ask
    for i in range(m):
        pnl, hit = simulate(ts, px, bid, ask, mid2, TR[i, 5], TR[i, 6], TR[i, 4] == 1, SLs, TPs, hold_ns, lat_ns, pass_ns, comm)
        P[i] = pnl; Hh[i] = hit
    return P, Hh


def depths(W):
    d = [p if p < W else -1 for p in P_TICKS] + [int(round(f * W)) if 1 <= round(f * W) < W else -1 for f in P_FRAC]
    return np.array(d, np.int64)


# ------------------------------------------------------------------ corrida
_SS = []
_TODS = []


def _session(si):
    """Una sesión: zonas de las 12 configs, un fantasma por zona, disparos y simulación. Semilla por sesión."""
    ss, tods = _SS, _TODS
    S = len(ss); s = ss[si]
    rng = np.random.default_rng(SEED + si)
    strides = np.array([int(np.prod(SHAPE[i + 1:])) for i in range(len(SHAPE))], np.int64)
    ii = np.indices((NSL, NDIR, NEX)).reshape(3, -1)   # orden del bloque de simulate
    row = np.zeros((NCELL, 3), np.float32)             # n, suma pnl, suma aciertos
    zc = np.zeros(NC, np.int64); nt = np.zeros((NC, NNULL), np.int64)
    ctrl = []                                          # (t evento real, t control) para la auditoría del cerebro
    ts, px, bid, ask = s["ts"], s["px"], s["bid"], s["ask"]
    t, H, L, C, V, bend = bars25(s)
    for ci, (mb, mw) in enumerate(GRID):
        Z = detect(t, H, L, C, V, mb, mw, E0, R_END)
        zc[ci] = len(Z)
        for z in Z:
            d, a, b, j = int(z[0]), int(z[1]), int(z[2]), int(z[5])
            lo, hi = min(a, b), max(a, b)
            k0 = int(bend[j])
            dep = depths(hi - lo)
            # real y un fantasma: otra sesión, misma hora ET +-15 min, geometría relativa al último trade
            cands = [(0, ts, px, bid, ask, k0, lo, hi)]
            for _ in range(8 * N_PH):
                if len(cands) > N_PH:
                    break
                oi = int(rng.integers(0, S))
                if oi == si:
                    continue
                tod = (ts[k0] // NS + s["off"]) % 86400 + int(rng.integers(-TOD_TOL_S, TOD_TOL_S + 1))
                ko = int(np.argmin(np.abs(tods[oi] - tod)))
                if abs(int(tods[oi][ko]) - tod) > TOD_TOL_S or ko >= len(ss[oi]["px"]) - 100:
                    continue
                o = ss[oi]; sh = int(o["px"][ko]) - int(px[k0])
                cands.append((1, o["ts"], o["px"], o["bid"], o["ask"], ko, lo + sh, hi + sh))
                ctrl.append((int(ts[k0]), int(o["ts"][ko])))
            for nul, T_, P_, B_, A_, kk, l_, h_ in cands:
                TR = zone_triggers(T_, P_, kk, l_, h_, d, dep, DS, RS, HZ_S * NS, WAIT_S * NS)
                nt[ci, nul] += len(TR)
                if len(TR) == 0:
                    continue
                pnl, hit = simulate_many(T_, P_, B_, A_, TR, SLC, TPC, HOLD_S * NS, LAT_NS, PASS_T_S * NS, COMM)
                base = (ci * strides[0] + (1 - TR[:, 3]) * strides[1] + TR[:, 0] * strides[2]
                        + TR[:, 1] * strides[3] + TR[:, 2] * strides[4])
                cell = (base[:, None] + (ii[1] * strides[5] + ii[0] * strides[6] + ii[2] * strides[7] + nul)[None, :]).ravel()
                np.add.at(row[:, 0], cell, 1)
                np.add.at(row[:, 1], cell, pnl.reshape(-1))
                np.add.at(row[:, 2], cell, hit.reshape(-1))
    return si, row, zc, nt, np.array(ctrl, np.int64).reshape(-1, 2)


def run():
    global _SS, _TODS
    out_dir = os.environ.get("R3_OUT", "/kaggle/working")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    ss = load_sessions(int(os.environ.get("R3_MAXSESS", "0")))
    S = len(ss)
    print("sesiones", S, ss[0]["td"], ss[-1]["td"], f"{time.time() - t0:.0f}s", flush=True)
    _SS = ss
    _TODS = [((s["ts"] // NS + s["off"]) % 86400) for s in ss]
    agg = np.zeros((S, NCELL, 3), np.float32)
    zcount = np.zeros((S, NC), np.int64)
    ntrig = np.zeros((S, NC, NNULL), np.int64)
    workers = int(os.environ.get("R3_WORKERS", str(os.cpu_count() or 1)))
    _session(0)   # compila numba antes de forkear
    import multiprocessing as mp
    with mp.get_context("fork").Pool(workers) as pool:
        ctrls = []
        for si, row, zc, nt, cp in pool.imap_unordered(_session, range(S)):
            agg[si] = row; zcount[si] = zc; ntrig[si] = nt; ctrls.append(cp)
            print(si, ss[si]["td"], "zonas", zc.sum(), "disparos", nt.sum(), f"{time.time() - t0:.0f}s", flush=True)
    np.savez_compressed(f"{out_dir}/r3_ctrl.npz", pairs=np.concatenate(ctrls), tds=np.array([s["td"] for s in ss]),
                        zcount=zcount, ntrig=ntrig)
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


def report(agg, zcount, ntrig, tds, out_dir, chunk=20000):
    S = agg.shape[0]
    zps = zcount.mean(0)
    keep_cfg = zps >= MIN_ZONES_PER_SESS
    A = agg.reshape((S,) + SHAPE + (3,))
    rng = np.random.default_rng(SEED)
    Wb = np.stack([np.bincount(rng.integers(0, S, S), minlength=S) for _ in range(N_BOOT)]).astype(np.float32)
    months = np.array([td[:6] for td in tds]); um = np.unique(months)
    q = lambda x, a_: np.nanquantile(x, a_, axis=0)
    parts = []
    for ci, (mb, mw) in enumerate(GRID):
        if not keep_cfg[ci]:
            continue
        flat = A[:, ci].reshape(S, -1, NNULL, 3)
        tot = flat[:, :, 0, 0].sum(0)
        idx_all = np.nonzero(tot >= MIN_N)[0]
        for c0 in range(0, len(idx_all), chunk):
            idx = idx_all[c0:c0 + chunk]
            X = flat[:, idx]                                 # S, k, null, 3
            def boot(col, nul):
                num = X[:, :, nul, col]; den = X[:, :, nul, 0]
                return num.sum(0) / np.maximum(den.sum(0), 1), (Wb @ num) / np.maximum(Wb @ den, 1)
            pr, prb = boot(1, 0); hr, hrb = boot(2, 0); pf, pfb = boot(1, 1); hf, hfb = boot(2, 1)
            nf = X[:, :, 1, 0].sum(0)
            sub = np.array(np.unravel_index(idx, SHAPE[1:-1]))   # side, D, P, R, dir, K, ex
            sl = SLC[sub[5]]; tp = TPC[sub[5]]; p0 = sl / (sl + tp)
            okf = nf >= MIN_N
            dh = hrb - p0; dhf = np.where(okf, hrb - hfb, np.nan); dpf = np.where(okf, prb - pfb, np.nan)
            pm = np.stack([X[months == m_][:, :, 0, 1].sum(0) for m_ in um])
            nm = np.stack([X[months == m_][:, :, 0, 0].sum(0) for m_ in um])
            mpos = ((pm > 0) & (nm > 0)).sum(0) / np.maximum((nm > 0).sum(0), 1)
            pt = [f"{P_TICKS[i]}t" if i < len(P_TICKS) else f"{P_FRAC[i - len(P_TICKS)]}W" for i in sub[2]]
            parts.append(pd.DataFrame(dict(
                cfg=f"mb{mb}_mw{mw}", lado=np.where(sub[0] == 0, "B", "A"), D=DS[sub[1]], p=pt, r=RS[sub[3]],
                dir=np.where(sub[4] == 0, "sigue", "rebota"), SL=sl, TP=tp, exec=np.array(EXECS)[sub[6]],
                n=tot[idx].astype(int), hit=hr, p0=p0, hit_lo=q(hrb, .025), hit_hi=q(hrb, .975), exc_N1=hr - p0,
                exc_N1_lo=q(dh, .025), p_N1=(dh <= 0).mean(0), pnl=pr, pnl_lo=q(prb, .025), pnl_hi=q(prb, .975),
                p_pnl=(prb <= 0).mean(0), n_fant=nf.astype(int), hit_fant=np.where(nf > 0, hf, np.nan),
                pnl_fant=np.where(nf > 0, pf, np.nan), exc_fant=np.where(okf, hr - hf, np.nan),
                exc_fant_lo=q(dhf, .025), p_fant=np.where(okf, (dhf <= 0).mean(0), np.nan),
                dpnl_fant=np.where(okf, pr - pf, np.nan), dpnl_fant_lo=q(dpf, .025), meses_pos=mpos)))
    D = pd.concat(parts, ignore_index=True)
    D["fdr"] = False; D["sugerencia"] = False
    # iteración 3: primaria = dirección simétrica (SL = TP) sobre el medio; secundaria = P&L realista neto
    prim = (D["exec"] == "perfecta_mid") & (D.SL == D.TP)
    D.loc[prim, "fdr"] = bh(np.maximum(D.loc[prim, "p_N1"], D.loc[prim, "p_fant"].fillna(1)), 0.10)
    sec = D["exec"] == "realista"
    D.loc[sec, "fdr"] = bh(D.loc[sec, "p_pnl"], 0.10)
    D.loc[prim, "sugerencia"] = D.loc[prim, "fdr"] & (D.loc[prim, "exc_N1_lo"] > 0) & (D.loc[prim, "exc_fant_lo"] > 0) \
        & (D.loc[prim, "meses_pos"] >= 0.55)
    D.loc[sec, "sugerencia"] = D.loc[sec, "fdr"] & (D.loc[sec, "pnl_lo"] > 0) & (D.loc[sec, "dpnl_fant_lo"] > 0) \
        & (D.loc[sec, "meses_pos"] >= 0.55)
    D.to_csv(f"{out_dir}/r3_celdas.csv.gz", index=False)
    w = lambda g, c: float((g[c] * g.n).sum() / max(g.n.sum(), 1))
    by_tp = {}
    for (ex, tp_), g in D[D.SL == D.TP].groupby(["exec", "TP"]):
        by_tp[f"{ex}|TP{tp_}"] = dict(hit=w(g, "hit"), hit_fant=w(g.dropna(subset=["hit_fant"]), "hit_fant"),
                                      pnl=w(g, "pnl"), pnl_fant=w(g.dropna(subset=["pnl_fant"]), "pnl_fant"),
                                      mejor_pnl=float(g.pnl.max()), celdas=int(len(g)))
    summ = dict(
        sesiones=int(S), desde=tds[0], hasta=tds[-1],
        zonas_por_sesion={f"mb{mb}_mw{mw}": float(zps[i]) for i, (mb, mw) in enumerate(GRID)},
        configs_usadas=[f"mb{mb}_mw{mw}" for i, (mb, mw) in enumerate(GRID) if keep_cfg[i]],
        disparos_real=int(ntrig[:, :, 0].sum()), disparos_fantasma=int(ntrig[:, :, 1].sum()),
        celdas=int(len(D)), celdas_primarias=int(prim.sum()), celdas_realistas=int(sec.sum()),
        fdr_primaria=int(D.loc[prim, "fdr"].sum()), fdr_realista=int(D.loc[sec, "fdr"].sum()),
        sugerencias_primaria=int(D.loc[prim, "sugerencia"].sum()), sugerencias_realista=int(D.loc[sec, "sugerencia"].sum()),
        realista_pnl_positivo=int((D.loc[sec, "pnl"] > 0).sum()), por_TP_simetrico=by_tp,
        top_realista=D[sec].sort_values("pnl", ascending=False).head(20).to_dict("records"),
        sugerencias_lista=D[D.sugerencia].sort_values("pnl", ascending=False).head(200).to_dict("records"))
    with open(f"{out_dir}/r3_resumen.json", "w") as fh:
        json.dump(summ, fh, indent=1, default=float)
    print(json.dumps({k: v for k, v in summ.items() if k not in ("top_realista", "sugerencias_lista")}, indent=1,
                     default=float))


if __name__ == "__main__":
    run()
