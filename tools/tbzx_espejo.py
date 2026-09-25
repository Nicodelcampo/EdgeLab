#!/usr/bin/env python3
r"""TBZX: impulsos de poco volumen por tick; qué hace el precio AFUERA de la franja y cómo REINGRESA.

Manifiesto: docs/research/MANIFIESTO_TBZX_ESPEJO_20260925.md (escrito antes de medir). Sin entradas ni P&L.

    .venv\Scripts\python tools\tbzx_espejo.py bars --workers 2     # velas 25t por sesión (caché, lectura por sesión)
    .venv\Scripts\python tools\tbzx_espejo.py parity                # detector Python == detector del visor
    .venv\Scripts\python tools\tbzx_espejo.py measure               # franjas reales + 3 fantasmas por franja
    .venv\Scripts\python tools\tbzx_espejo.py report                # paisaje, BH-FDR, cortes descriptivos, Brain
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from numba import njit  # noqa: E402

import tbz_e2 as TB  # noqa: E402

NS = 1_000_000_000
INST = "ES"
OUT = REPO / "artifacts" / "tbzx"
DOC = "docs/research/MANIFIESTO_TBZX_ESPEJO_20260925.md"
LEDGER = REPO / "artifacts" / "hippocampus" / "tbzx_20260925.jsonl"
GRID = [(mb, mw) for mb in (10, 20, 40) for mw in (8, 12, 17, 24)]
NICO = (20, 17)
E0, R_END = 0.6, 0.3
H = 200            # velas de horizonte después de iend
PEN_BARS = 50      # velas para medir la penetración después de reingresar
N_PH = 3           # fantasmas por franja
TOD_TOL_S = 900
SEED = 20260925
# nulo N-VOL (agregado DESPUÉS de ver el primer reporte, más estricto; ver manifiesto §4b)
VOL_TOD_TOL_S = 3600
VOL_TOL = 0.25
VOL_CAP = 20000
PART = "P-TBZX-ES-EXP"
N_BOOT = 2000


# ------------------------------------------------------------------ velas
def _bars_session(s):
    from edgelab.bridge.bars import build_tick_bars
    from edgelab.bridge.ticks import load_canonical_parquet
    f = OUT / "bars" / f"{s['trade_date']}.npz"
    if f.exists():
        return s["trade_date"], "EXISTE"
    tk = load_canonical_parquet(s["path"], contract=s["contract"], start_utc_ns=s["start"], end_utc_ns=s["end"])
    ts = tk.ts_ns.astype(np.int64)
    if len(ts) < 5000 or bool((np.diff(ts) < 0).any()):
        return s["trade_date"], "POCA_ACTIVIDAD_O_NO_MONOTONO"
    if int(ts[-1]) >= TB.HOLDOUT_NS:
        raise ValueError("holdout decodificado")
    b = build_tick_bars(tk, 25, reiniciar_por_sesion=True)
    f.parent.mkdir(parents=True, exist_ok=True)
    np.savez(f, t=(b.end_ns / NS).astype(np.float64), h=b.high_t.astype(np.int32), l=b.low_t.astype(np.int32),
             c=b.close_t.astype(np.int32), v=b.volume.astype(np.float32), contract=s["contract"])
    return s["trade_date"], f"OK {len(b.end_ns)}"


def sessions():
    return [s for s in TB.sessions(INST) if s["trade_date"] <= TB.EXP_END]


def step_bars(workers):
    ss = sessions()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for fu in as_completed([ex.submit(_bars_session, s) for s in ss]):
            td, st = fu.result()
            print(td, st, flush=True)


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
    d = 0; i0 = 0; a = 0; ext = 0; iext = 0; itrig = 0; vol = 0.0
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


# ------------------------------------------------------------------ camino después de la franja
NMET = 22
MET = ["side_B", "bars_to_exit", "exc_ticks", "exc_W", "out_bars", "out_secs", "out_vol", "reentered", "pen_W",
       "reach_opp", "reach_mirror", "re_tpb", "re_tps", "re_eff", "re_vpt", "tot_out_B_bars", "tot_out_A_bars",
       "tot_out_B_vol", "tot_out_A_vol", "tot_exc_B", "tot_exc_A", "exited"]


@njit(cache=True)
def path_metrics(t, H, L, C, V, e, d, A, B, W, hz, pen_bars):
    """Métricas del camino en (e, e+hz]. A, B en ticks (pueden ser fantasma). NaN = no aplica."""
    res = np.full(22, np.nan)
    lo = min(A, B); hi = max(A, B); n = len(C)
    end = min(e + hz, n - 1)
    tobB = 0; tobA = 0; tvB = 0.0; tvA = 0.0; teB = 0.0; teA = 0.0
    for k in range(e + 1, end + 1):
        if d == 1:
            if C[k] > hi: tobB += 1; tvB += V[k]
            if C[k] < lo: tobA += 1; tvA += V[k]
            teB = max(teB, H[k] - hi); teA = max(teA, lo - L[k])
        else:
            if C[k] < lo: tobB += 1; tvB += V[k]
            if C[k] > hi: tobA += 1; tvA += V[k]
            teB = max(teB, lo - L[k]); teA = max(teA, H[k] - hi)
    res[15] = tobB; res[16] = tobA; res[17] = tvB; res[18] = tvA; res[19] = teB; res[20] = teA
    kx0 = -1; up = False
    for k in range(e + 1, end + 1):
        if C[k] > hi:
            kx0 = k; up = True; break
        if C[k] < lo:
            kx0 = k; up = False; break
    if kx0 < 0:
        res[21] = 0.0
        return res
    res[21] = 1.0
    res[0] = 1.0 if (up == (d == 1)) else 0.0
    res[1] = kx0 - e
    edge = hi if up else lo
    exc = 0.0; kx = kx0; vol = 0.0; kb = -1
    for k in range(kx0, end + 1):
        if (C[k] <= hi) and (C[k] >= lo):
            kb = k; break
        x = (H[k] - edge) if up else (edge - L[k])
        if x > exc:
            exc = x; kx = k
        vol += V[k]
    res[2] = exc; res[3] = exc / W; res[6] = vol
    if kb < 0:
        res[4] = end - kx0 + 1; res[5] = t[end] - t[kx0]; res[7] = 0.0
        return res
    res[4] = kb - kx0; res[5] = t[kb] - t[kx0]; res[7] = 1.0
    pen = -1e9; kd = kb
    for k in range(kb, min(kb + pen_bars, n - 1) + 1):
        p = (edge - L[k]) if up else (H[k] - edge)
        if p > pen:
            pen = p; kd = k
    res[8] = pen / W
    res[9] = 1.0 if pen >= W + 1 else 0.0
    res[10] = 1.0 if pen >= 2 * W + 1 else 0.0
    xp = (edge + exc) if up else (edge - exc)
    dp = (edge - pen) if up else (edge + pen)
    ticks = abs(xp - dp); bars = max(kd - kx, 1); secs = max(t[kd] - t[kx], 1e-3)
    pth = 0.0; vv = 0.0
    for k in range(kx + 1, kd + 1):
        pth += abs(C[k] - C[k - 1]); vv += V[k]
    res[11] = ticks / bars; res[12] = ticks / secs
    res[13] = abs(C[kd] - C[kx]) / pth if pth > 0 else np.nan
    res[14] = vv / ticks if ticks > 0 else np.nan
    return res


def _load_all():
    S = {}
    for f in sorted((OUT / "bars").glob("*.npz")):
        z = np.load(f)
        t = z["t"]
        et = pd.to_datetime(t, unit="s", utc=True).tz_convert(TB.ET)
        clock = ((et.hour * 3600 + et.minute * 60 + et.second).to_numpy() - 18 * 3600) % 86400   # desde las 18:00 ET
        S[f.stem] = dict(t=t, h=z["h"].astype(np.int64), l=z["l"].astype(np.int64), c=z["c"].astype(np.int64),
                         v=z["v"].astype(np.float64), clock=clock.astype(np.int64), contract=str(z["contract"]))
    return S


def step_parity():
    """Detector Python sobre las velas del bundle del visor (enero) contra el conteo del visor con los mismos parámetros."""
    d = json.loads((TB.BUNDLES / "ES_03-26_202601_25T_HFT.json").read_text(encoding="utf-8"))
    key = next(iter(d["bar_series"]))
    cd = d["bar_series"][key]["candles"]
    tick = d["meta"]["tick_size"]
    t = np.array([c["time"] for c in cd], float)
    Hh = np.round(np.array([c["high"] for c in cd]) / tick).astype(np.int64)
    Ll = np.round(np.array([c["low"] for c in cd]) / tick).astype(np.int64)
    Cc = np.round(np.array([c["close"] for c in cd]) / tick).astype(np.int64)
    V = np.array([c.get("volume", 0) for c in cd], float)
    del d, cd
    res = {}
    for mb, mw in [NICO, (20, 8)]:
        b = detect(t, Hh, Ll, Cc, V, mb, mw, E0, R_END)
        res[f"{mb}_{mw}"] = dict(n=int(len(b)), first=[[float(t[int(x[3])]), int(x[1]), int(x[2]), float(t[int(x[4])])] for x in b[:5]])
    out = OUT / "parity_python.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


def declare_partition(keys):
    """Partición de exploración de esta familia, declarada en su propio ledger ANTES de medir."""
    from edgelab.edge_brain.episode_logger import measurement_episode
    with measurement_episode(LEDGER, "EP-TBZX-PARTICION-20260925", goal="declarar partición TBZX antes de medir",
                             recorded_by="tools/tbzx_espejo.py measure", repo=REPO, prereg_ref=DOC) as ep:
        if PART not in ep.store.partitions:
            ep.store.record_partition(PART, "EXPLORATION", "ES 25T jul-2025 a mar-2026 (las mismas sesiones que P-TBZ-EXP)",
                                      [f"ES:{k}" for k in keys])


def trailing(x, W):
    """Rango (máx. H − mín. L) y segundos de las W velas que terminan en cada vela: actividad previa, causal."""
    n = len(x["c"])
    from numpy.lib.stride_tricks import sliding_window_view
    rg = np.full(n, np.nan); sec = np.full(n, np.nan)
    if n > W:
        rg[W:] = sliding_window_view(x["h"], W + 1).max(axis=1) - sliding_window_view(x["l"], W + 1).min(axis=1)
        sec[W:] = x["t"][W:] - x["t"][:-W]
    return rg, sec


def vol_phantom(S, keys, s, mb, clock, rg0, sec0, rng):
    """Otra sesión, misma hora (± 1 h), con rango y duración de las últimas `mb` velas a ± 25 % de los reales."""
    others = [k for k in keys if k != s]
    for _ in range(40):
        o = others[int(rng.integers(len(others)))]
        y = S[o]
        a, b = np.searchsorted(y["clock"], clock - VOL_TOD_TOL_S), np.searchsorted(y["clock"], clock + VOL_TOD_TOL_S)
        if b <= a:
            continue
        rg, sec = y[f"rg{mb}"][a:b], y[f"sec{mb}"][a:b]
        ok = (np.abs(rg - rg0) <= VOL_TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + VOL_TOL))
        ok &= (np.arange(a, b) + H < len(y["c"]) - 1)
        idx = np.flatnonzero(ok)
        if len(idx):
            return o, a + int(idx[int(rng.integers(len(idx)))])
    return None, None


def step_measure():
    S = _load_all()
    keys = sorted(S)
    assert max(keys) <= TB.EXP_END
    declare_partition(keys)
    for k in keys:
        for mb in sorted({g[0] for g in GRID}):
            S[k][f"rg{mb}"], S[k][f"sec{mb}"] = trailing(S[k], mb)
    rng = np.random.default_rng(SEED)
    vol_rng = np.random.default_rng(SEED + 1)
    rows = []
    # fracción de franjas con N-VOL: todas si son <= VOL_CAP, si no una muestra aleatoria fija
    counts = {f"B{mb}_W{mw}": sum(len(detect(S[k]["t"], S[k]["h"], S[k]["l"], S[k]["c"], S[k]["v"], mb, mw, E0, R_END)) for k in keys)
              for mb, mw in GRID}
    vol_frac = {c: min(1.0, VOL_CAP / max(n, 1)) for c, n in counts.items()}
    for mb, mw in GRID:
        cfg = f"B{mb}_W{mw}"
        for s in keys:
            x = S[s]
            bands = detect(x["t"], x["h"], x["l"], x["c"], x["v"], mb, mw, E0, R_END)
            for bi, b in enumerate(bands):
                d, A, B, i0, iext, iend, itrig, vimp, why = b
                d, A, B, i0, iext, iend = int(d), int(A), int(B), int(i0), int(iext), int(iend)
                if iend + H > len(x["c"]) - 1:
                    continue                                          # horizonte incompleto: fuera (se cuenta)
                W = abs(B - A)
                base = dict(cfg=cfg, maxBars=mb, minW=mw, session=s, band=bi, dir=d, W=W, imp_bars=max(iext - i0, 1),
                            imp_secs=float(x["t"][iext] - x["t"][i0]), imp_vol=float(vimp), imp_vpt=float(vimp) / W,
                            imp_eff=float(abs(x["c"][iext] - x["c"][i0]) / max(np.abs(np.diff(x["c"][i0:iext + 1])).sum(), 1)),
                            end_why=int(why), t_end=float(x["t"][iend]), clock=int(x["clock"][iend]),
                            phase=TB.phase_et(int(x["t"][iend] * NS)))
                real = path_metrics(x["t"], x["h"], x["l"], x["c"], x["v"], iend, d, A, B, W, H, PEN_BARS)
                rows.append(dict(base, kind="real", ph_session=s, **dict(zip(MET, real))))
                # fantasmas: otra sesión, misma hora del día, misma geometría relativa al cierre de iend
                c_e = int(x["c"][iend]); got = 0; tries = 0
                others = [k for k in keys if k != s]
                while got < N_PH and tries < 12:
                    tries += 1
                    o = others[int(rng.integers(len(others)))]
                    y = S[o]
                    k = int(np.searchsorted(y["clock"], base["clock"]))
                    cand = [q for q in (k - 1, k) if 0 <= q < len(y["c"])]
                    if not cand:
                        continue
                    q = min(cand, key=lambda z: abs(int(y["clock"][z]) - base["clock"]))
                    if abs(int(y["clock"][q]) - base["clock"]) > TOD_TOL_S or q + H > len(y["c"]) - 1 or q < 1:
                        continue
                    sh = int(y["c"][q]) - c_e
                    m = path_metrics(y["t"], y["h"], y["l"], y["c"], y["v"], q, d, A + sh, B + sh, W, H, PEN_BARS)
                    rows.append(dict(base, kind="fantasma", ph_session=o, ph_t=float(y["t"][q]), **dict(zip(MET, m))))
                    got += 1
                # N-VOL: misma actividad previa (sólo una muestra de hasta VOL_CAP franjas por configuración)
                if vol_rng.random() < vol_frac[cfg]:
                    rg0, sec0 = x[f"rg{mb}"][iend], x[f"sec{mb}"][iend]
                    for _ in range(N_PH):
                        o, q = vol_phantom(S, keys, s, mb, base["clock"], rg0, sec0, rng)
                        if o is None:
                            break
                        y = S[o]; sh = int(y["c"][q]) - c_e
                        m = path_metrics(y["t"], y["h"], y["l"], y["c"], y["v"], q, d, A + sh, B + sh, W, H, PEN_BARS)
                        pdir = float(np.sign(y["c"][q] - y["c"][max(q - mb, 0)]))
                        rows.append(dict(base, kind="fantasma_vol", ph_session=o, ph_t=float(y["t"][q]), ph_prev_dir=pdir, **dict(zip(MET, m))))
        print(cfg, sum(1 for r in rows if r["cfg"] == cfg and r["kind"] == "real"), flush=True)
    D = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_parquet(OUT / "measure_ES.parquet", index=False)
    print("filas", len(D))


# ------------------------------------------------------------------ reporte
PRIMARY = [("side_B", "sale por el lado B (continuación)"), ("exc_W", "excursión afuera / W"), ("out_bars", "velas afuera"),
           ("out_vol_rel", "volumen afuera / volumen del impulso"), ("reentered", "reingresa en 200 velas"),
           ("pen_W", "penetración al reingresar / W"), ("reach_opp", "llega al borde opuesto"), ("re_tpb", "velocidad de reingreso (t/vela)")]


def _pair(D, col, null="fantasma"):
    """Por franja: valor real y media de sus fantasmas (del nulo pedido)."""
    R = D[D.kind == "real"].set_index(["cfg", "session", "band"])[col]
    P = D[D.kind == null].groupby(["cfg", "session", "band"])[col].mean()
    J = pd.concat([R.rename("r"), P.rename("p")], axis=1).dropna()
    return J


def _boot(J, rng):
    s = J.index.get_level_values("session").to_numpy()
    u, inv = np.unique(s, return_inverse=True)
    diff = (J.r - J.p).to_numpy()
    sums = np.bincount(inv, weights=diff); cnt = np.bincount(inv)
    obs = diff.mean()
    bs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        w = np.bincount(rng.integers(len(u), size=len(u)), minlength=len(u))
        bs[b] = (w * sums).sum() / max((w * cnt).sum(), 1)
    se = bs.std()
    p = 2 * min((bs <= 0).mean(), (bs >= 0).mean())
    return obs, np.percentile(bs, 2.5), np.percentile(bs, 97.5), se, max(p, 1 / N_BOOT)


def _bh(p, q=0.10):
    p = np.asarray(p); o = np.argsort(p); m = len(p)
    ok = np.zeros(m, bool)
    thr = q * (np.arange(1, m + 1)) / m
    below = p[o] <= thr
    if below.any():
        ok[o[:np.max(np.flatnonzero(below)) + 1]] = True
    return ok


def step_report():
    D = pd.read_parquet(OUT / "measure_ES.parquet")
    D["out_vol_rel"] = D.out_vol / D.imp_vol.clip(lower=1)
    rng = np.random.default_rng(SEED)
    cells = []
    for cfg, g in D.groupby("cfg", sort=False):
      for null in ("fantasma", "fantasma_vol"):
        for col, lab in PRIMARY:
            J = _pair(g, col, null)
            if len(J) < 30:
                cells.append(dict(cfg=cfg, null=null, metric=col, label=lab, n=len(J), status="POCOS"))
                continue
            obs, lo, hi, se, p = _boot(J, rng)
            cells.append(dict(cfg=cfg, null=null, metric=col, label=lab, n=int(len(J)), sessions=int(J.index.get_level_values("session").nunique()),
                              real=float(J.r.mean()), fantasma=float(J.p.mean()), diff=float(obs), ci=[float(lo), float(hi)],
                              mde=float(2.8 * se), p=float(p), status="OK"))
    ok = [c for c in cells if c["status"] == "OK"]
    for null in ("fantasma", "fantasma_vol"):                     # BH por nulo: cada uno es su propia familia de 96
        oo = [c for c in ok if c["null"] == null]
        for c, f in zip(oo, _bh([c["p"] for c in oo])):
            c["fdr"] = bool(f)
    # combinaciones: cortes descriptivos sobre la configuración de Nico
    g = D[D.cfg == f"B{NICO[0]}_W{NICO[1]}"].copy()
    r = g[g.kind == "real"]
    for col in ("imp_vpt", "imp_bars", "imp_eff", "W"):
        try:
            g[f"{col}_q"] = g.groupby(["session", "band"])[col].transform("first")
            g[f"{col}_q"] = pd.qcut(g[f"{col}_q"], 3, labels=["bajo", "medio", "alto"], duplicates="drop").astype(str)
        except ValueError:
            g[f"{col}_q"] = "único"
    cuts = {}
    for cut in ("phase", "imp_vpt_q", "imp_bars_q", "imp_eff_q", "W_q", "dir"):
        for lvl, gg in g.groupby(cut):
            row = {}
            for col, lab in PRIMARY + [("exc_ticks", "excursión (t)"), ("out_secs", "segundos afuera"), ("reach_mirror", "espejo completo")]:
                J = _pair(gg, col); Jv = _pair(gg, col, "fantasma_vol")
                if len(J) >= 30:
                    row[col] = [round(float(J.r.mean()), 3), round(float(J.p.mean()), 3), int(len(J)),
                                [round(float(Jv.r.mean()), 3), round(float(Jv.p.mean()), 3), int(len(Jv))] if len(Jv) >= 30 else None]
            cuts[f"{cut}={lvl}"] = row
    # distribución completa (real y fantasma) sobre Nico
    dist = {}
    for col in ("exc_ticks", "exc_W", "out_bars", "out_secs", "out_vol", "pen_W", "re_tpb", "re_eff", "re_vpt"):
        for k in ("real", "fantasma", "fantasma_vol"):
            v = g[g.kind == k][col].dropna()
            dist[f"{col}|{k}"] = [round(float(x), 3) for x in np.percentile(v, [10, 25, 50, 75, 90])] if len(v) else None
    ph = D[D.kind.isin(["fantasma", "fantasma_vol"])]
    from edgelab.edge_brain.control_guard import audit_event_controls
    audit = audit_event_controls((ph.t_end * 1e6).astype(np.int64).to_numpy(), (ph.ph_t * 1e6).astype(np.int64).to_numpy(),
                                 H * 60.0, same_session=(ph.session == ph.ph_session).to_numpy())
    body = dict(schema="EDGELAB_TBZX_ESPEJO_V1", doc=DOC, inst=INST, code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")), partition=PART,
                franjas_reales={c: int(((D.cfg == c) & (D.kind == "real")).sum()) for c in D.cfg.unique()},
                celdas=cells, cortes_nico=cuts, distribucion_nico=dist, control_audit=audit)
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "report_ES.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.episode_logger import measurement_episode
    with measurement_episode(LEDGER, "EP-TBZX-ESPEJO-ES-20260925B", goal="TBZX: afuera y reingreso vs fantasma misma hora y fantasma misma actividad (N-VOL)",
                             recorded_by="tools/tbzx_espejo.py report", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_observation("OBS-TBZX-ESPEJO-ES-V2", "franja TBZX: afuera y reingreso, 2 nulos", "RESPONSE_PROFILE", [PART],
                                    {f"{c['cfg']}|{c['null']}|{c['metric']}": (c.get("diff"), c.get("fdr")) for c in cells},
                                    {"horizon_bars": H, "phantoms": N_PH}, sha, design="EVENT_VS_CONTROL", control_audit=audit)
    print(json.dumps(dict(celdas=len(ok), fdr={n: int(sum(c["fdr"] for c in ok if c["null"] == n)) for n in ("fantasma", "fantasma_vol")},
                          sha=sha[:12], audit=audit["status"])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["bars", "parity", "measure", "report"])
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args(argv)
    {"bars": lambda: step_bars(a.workers), "parity": step_parity, "measure": step_measure, "report": step_report}[a.step]()


if __name__ == "__main__":
    main()
