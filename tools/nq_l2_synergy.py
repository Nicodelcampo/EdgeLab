#!/usr/bin/env python3
r"""Absorción como amplificador de contexto, NQ L2 (manifiesto docs/research/MANIFIESTO_NQ_L2_SINERGIA_ABSORCION_20260924.md,
OK de Nico 2026-09-24: "OK manifiesto sinergia, adelante con todo").

Pasos:
  run      por sesión de P-NQL2-EXP: eventos de absorción + controles emparejados (misma distancia, mismo tercil de
           actividad 60 s), contextos causales C1–C12 en el instante y resultados en la dirección implícita.
           Filas en artifacts/nq_l2_synergy/rows/<día>.parquet
  report   etapa 1 (interacción por contexto/nivel/canal/horizonte, bootstrap por sesión, BH-FDR q=0,10, MDE)
           + etapa 2 (árbol honesto) + reglas de sugerencia (fijas en este archivo) + ledger.

La reserva P-NQL2-CONF no se lee. Unidades: ticks de NQ (0,25).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import nq_l2_explore as X  # noqa: E402
from edgelab.bridge.indicators import hftzones_universal as hu  # noqa: E402
from edgelab.research.l2_manipulation_heuristics import ASK  # noqa: E402
from edgelab.research.tbz_bands import dwell_bands, expansion_bands  # noqa: E402

OUT = REPO / "artifacts" / "nq_l2_synergy_C"   # corrida C: controles corregidos (la B vive en artifacts/nq_l2_synergy)
LEDGER = X.LEDGER  # mismo ledger: particiones P-NQL2-* declaradas antes de medir
MANIF = "docs/research/MANIFIESTO_NQ_L2_SINERGIA_ABSORCION_20260924.md"
US = X.US
HZ = (30, 60, 300, 900)
RACE = (8, 16)
CHANNELS = ["sig", "asym", "race8", "race16", "abs"]
DIRECTIONAL = {"sig", "asym", "race8", "race16"}
SEED, N_BOOT, FDR_Q = 20260924, 2000, 0.10
MIN_EV, MIN_SESS, TOP_K = 30, 15, 5
ROUND_TICKS, NEAR_EXT, NEAR_ZONE, NEAR_EDGE = 400, 8, 4, 2
# "-B": la primera corrida del reporte usó hojas del árbol con >= 8 sesiones (MIN_SESS // 2 + 1) contra las >= 15 del
# manifiesto. Se invalidó en el ledger y se rehízo con el valor del manifiesto (endurece, no relaja).
TAG = "-C"
# "-C": auditoría EP-NQL2-SYN-AUDIT-C. Los controles en [t0-30 min, t0) heredan el camino con el que el precio llegó al
# nivel del evento (-6,6 ticks a 300 s; -20,7 si se solapan). Desde C, los controles se toman sólo DESPUÉS del horizonte
# máximo: t_c en (t0 + 900 s + 60 s, t0 + 900 s + 1.800 s].
CTRL_LO_S, CTRL_HI_S = max(HZ) + 60, max(HZ) + 1800


# ---------------------------------------------------------------- construcción causal por sesión
def bars25(T):
    n = len(T) // 25
    px, ts, sz = T.px.to_numpy()[: n * 25], T.ts.to_numpy()[: n * 25], T.sz.to_numpy()[: n * 25].astype(float)
    idx = np.arange(n) * 25
    return dict(o=px[idx], c=px[idx + 24], h=np.maximum.reduceat(px, idx), l=np.minimum.reduceat(px, idx),
                v=np.add.reduceat(sz, idx), t_open=ts[idx], t_close=ts[idx + 24])


def hft_zones(T):
    cands = hu.detect_candidates(T.ts.to_numpy().astype(np.int64) * 1000, T.px.to_numpy().astype(np.int64),
                                 T.sz.to_numpy().astype(float), params=None, prev_session_close_ticks=None)
    zones, _ = hu.accept_all(cands, hu.profile(hu.LITERAL, "NQ"), 0.25)
    if not zones:
        return np.zeros((0, 4))
    return np.array([[round(z["lower"] / 0.25), round(z["upper"] / 0.25), np.sign(z["direction"]), z["ts_avail"] // 1000]
                     for z in zones], dtype=float)                         # lo, hi, dir, avail_us


def zone_ctx(Z, B, t0, L, dirn):
    """C1 (nivel respecto de la zona más cercana disponible) y C2 (toques de esa zona antes de t0)."""
    if len(Z) == 0:
        return np.nan, "afuera", -1
    av = Z[Z[:, 3] <= t0]
    if len(av) == 0:
        return np.nan, "afuera", -1
    d = np.where((av[:, 0] <= L) & (L <= av[:, 1]), 0, np.minimum(np.abs(av[:, 0] - L), np.abs(av[:, 1] - L)))
    k = np.flatnonzero(d == d.min())[-1]                                   # empate: la más reciente
    z = av[k]
    pos = "dentro" if d[k] == 0 else ("borde" if d[k] <= NEAR_ZONE else "afuera")
    if pos == "afuera":
        return float(d[k]), "afuera", -1
    al = "alineada" if z[2] * dirn > 0 else "opuesta"
    closed = B["t_close"] < t0
    i0 = np.searchsorted(B["t_open"], z[3], "right")
    ins = (B["l"][i0:] <= z[1]) & (B["h"][i0:] >= z[0]) & closed[i0:]
    prev = np.concatenate([[True], ins[:-1]])
    touches = int((ins & ~prev).sum())
    return float(d[k]) * (1 if al == "alineada" else -1), f"{pos}_{al}", touches


class SessionCtx:
    def __init__(self, Q, T, prev_hl):
        self.Q, self.T = Q, T
        self.qts = Q.ts.to_numpy()
        self.mid = (Q.bid.to_numpy() + Q.ask.to_numpy()) / 2.0
        self.spr = (Q.ask.to_numpy() - Q.bid.to_numpy()).astype(float)
        self.dep = (Q.bsz.to_numpy() + Q.asz.to_numpy()).astype(float)
        self.tts, self.tpx, self.tsz = T.ts.to_numpy(), T.px.to_numpy(), T.sz.to_numpy().astype(float)
        self.cum_pv, self.cum_v = np.cumsum(self.tpx * self.tsz), np.cumsum(self.tsz)
        self.run_hi, self.run_lo = np.maximum.accumulate(self.tpx), np.minimum.accumulate(self.tpx)
        self.prev_hl = prev_hl
        self.B = bars25(T)
        self.Z = hft_zones(T)
        B = self.B
        tc_s = B["t_close"] // US
        self.exp = expansion_bands(tc_s, B["o"] * 0.25, B["h"] * 0.25, B["l"] * 0.25, B["c"] * 0.25, 0.25, W=20, k=4.0)
        self.dw = dwell_bands(tc_s, B["h"] * 0.25, B["l"] * 0.25, B["v"], 0.25, L_s=3600)
        self.dw_t = np.array([d["t"] for d in self.dw]) if self.dw else np.array([])
        rng_ = (B["h"] - B["l"]).astype(float)
        self.bar_rng = rng_
        # p95 causal del rango de vela (3.000 previas, mínimo 200)
        p95 = np.full(len(rng_), np.nan)
        for i in range(200, len(rng_)):
            p95[i] = np.percentile(rng_[max(0, i - 3000):i], 95)
        self.p95 = p95

    def j(self, t):
        return max(np.searchsorted(self.qts, t, "right") - 1, 0)

    def contexts(self, t0, L, dirn):
        c = {}
        zd, c1, touches = zone_ctx(self.Z, self.B, t0, L, dirn)
        c["C1_zona"], c["C1_dist"] = c1, zd
        c["C2_toques"] = touches
        # C3 bordes TBZ
        av = [b for b in self.exp if b["t_avail"] * US <= t0 and (t0 - b["t_avail"] * US) <= 240 * 60 * US]
        de = min([min(abs(L - b["lo_tick"]), abs(L - b["hi_tick"])) for b in av], default=np.nan)
        c["C3_exp_dist"] = float(de)
        dd = np.nan
        if len(self.dw_t):
            k = np.searchsorted(self.dw_t, t0 // US, "right") - 1
            if k >= 0 and self.dw[k]["bands"]:
                dd = float(min(min(abs(L - a), abs(L - b)) for a, b in self.dw[k]["bands"]))
        c["C3_dwell_dist"] = dd
        # C4 vela extrema en las 5 velas cerradas previas
        nb = np.searchsorted(self.B["t_close"], t0, "left")                # velas con cierre < t0
        ext = 0
        for i in range(max(nb - 5, 0), nb):
            if np.isfinite(self.p95[i]) and self.bar_rng[i] >= self.p95[i] and self.bar_rng[i] > 0:
                ext = int(np.sign(self.B["c"][i] - self.B["o"][i]) * dirn) or 2   # 2 = extrema sin cuerpo
        c["C4_extrema"] = ext
        # C5 tendencia (movimiento del medio en la dirección implícita)
        m0 = self.mid[self.j(t0)]
        c["C5_r5"] = float(dirn * (m0 - self.mid[self.j(t0 - 300 * US)]))
        c["C5_r30"] = float(dirn * (m0 - self.mid[self.j(t0 - 1800 * US)]))
        # C6 VWAP de sesión hasta t0
        kt = np.searchsorted(self.tts, t0, "left") - 1
        vw = self.cum_pv[kt] / self.cum_v[kt] if kt >= 0 else np.nan
        c["C6_vwap"] = float(dirn * (m0 - vw))
        # C7 extremos: sesión hasta t0 y sesión previa
        ext_lv = []
        if kt >= 0:
            ext_lv += [(self.run_hi[kt], -1), (self.run_lo[kt], +1)]
        if self.prev_hl:
            ext_lv += [(self.prev_hl[0], -1), (self.prev_hl[1], +1)]
        best = min(ext_lv, key=lambda e: abs(L - e[0]), default=None)
        c["C7_ext_dist"] = float(abs(L - best[0])) if best else np.nan
        c["C7_ext_dir"] = int(best[1] * dirn) if best else 0
        # C8 número redondo
        r = L % ROUND_TICKS
        c["C8_round_dist"] = float(min(r, ROUND_TICKS - r))
        # C9 liquidez (mediana 60 s previos)
        a, b = np.searchsorted(self.qts, t0 - 60 * US), self.j(t0) + 1
        c["C9_spread"] = float(np.median(self.spr[a:b])) if b > a else float(self.spr[self.j(t0)])
        c["C9_depth"] = float(np.median(self.dep[a:b])) if b > a else float(self.dep[self.j(t0)])
        # C10 bloque (reloj crudo = ART; ART = ET + 1)
        c["C10_sod"] = int((t0 // US) % 86400)
        # C11 QI en t0
        jj = self.j(t0)
        bs, as_ = self.Q.bsz.to_numpy()[jj], self.Q.asz.to_numpy()[jj]
        c["C11_qi"] = float(dirn * (bs - as_) / max(bs + as_, 1))
        # C12 ruptura previa del nivel en los 5 min anteriores
        lo, hi = np.searchsorted(self.tts, t0 - 300 * US), np.searchsorted(self.tts, t0, "left")
        pxw = self.tpx[lo:hi]
        c["C12_rota"] = int(len(pxw) > 0 and ((pxw.max() > L) if dirn == -1 else (pxw.min() < L)))
        c["spread0"] = float(self.spr[jj])
        return c

    def outcomes(self, t0, dirn):
        a, b = self.j(t0), np.searchsorted(self.qts, t0 + max(HZ) * US, "right")
        m0 = self.mid[a]
        path = dirn * (self.mid[a:b] - m0)
        pts = self.qts[a:b]
        o = {}
        for h in HZ:
            k = np.searchsorted(pts, t0 + h * US, "right")
            p = path[:k]
            o[f"sig{h}"] = float(p[-1])
            o[f"abs{h}"] = float(abs(p[-1]))
            o[f"asym{h}"] = float(max(p.max(), 0) - max(-p.min(), 0))
            for x in RACE:
                up, dn = np.flatnonzero(p >= x), np.flatnonzero(p <= -x)
                fu, fd = (up[0] if len(up) else 10**12), (dn[0] if len(dn) else 10**12)
                o[f"race{x}_{h}"] = float(1 if fu < fd else (-1 if fd < fu else 0))
        return o


def session_rows(day, prev_hl):
    Q, T = X.load_l1(day)
    if len(T) < 5000 or len(Q) < 5000:
        return day, "POCA_ACTIVIDAD", None, None
    if X.usable(day) is False:
        return day, "DEFECT_PHASE0", None, None
    if not X.clock_ok(T.ts.to_numpy(), day):
        return day, "CLOCK_UNCERTIFIED_P84", None, None
    rng = np.random.default_rng([SEED, int(day)])
    S = SessionCtx(Q, T, prev_hl)
    ev = X.absorption_events(T)
    last = int(Q.ts.iloc[-1])
    evt = np.array([e["available_ts_us"] for e in ev]) if ev else np.array([])
    grid = np.arange(int(Q.ts.iloc[0]) + 60 * US, last, 30 * US)
    vg = np.array([X.vol60(T, g) for g in grid]) if len(grid) else np.array([0.0])
    q1, q2 = np.percentile(vg, [33.3, 66.7])
    terc = lambda v: 0 if v <= q1 else (1 if v <= q2 else 2)
    ok_t = lambda t: t + max(HZ) * US <= last and not X.in_halt(t - 1800 * US, t + max(HZ) * US)
    rows = []
    for mid_, e in enumerate(ev):
        dirn = -1 if e["side"] == ASK else 1
        t0 = e["available_ts_us"] + X.LAT
        tch = X.touch_at(Q, t0, dirn)
        if tch is None or not ok_t(t0):
            continue
        dist = (e["tick"] - tch) if dirn == -1 else (tch - e["tick"])
        te = terc(X.vol60(T, t0))
        rows.append(dict(kind=1, match=mid_, dirn=dirn, t0=int(t0), level=int(e["tick"]),
                         **S.contexts(t0, e["tick"], dirn), **S.outcomes(t0, dirn)))
        got = 0
        for _ in range(80 * X.N_CTRL):
            if got >= X.N_CTRL:
                break
            tc = int(t0 + rng.integers(CTRL_LO_S, CTRL_HI_S) * US)
            if (len(evt) and np.min(np.abs(evt - tc)) < X.EXCL_S * US) or not ok_t(tc) or terc(X.vol60(T, tc)) != te:
                continue
            tt = X.touch_at(Q, tc, dirn)
            if tt is None:
                continue
            lv = int(tt + dist if dirn == -1 else tt - dist)
            rows.append(dict(kind=0, match=mid_, dirn=dirn, t0=tc, level=lv, **S.contexts(tc, lv, dirn), **S.outcomes(tc, dirn)))
            got += 1
    df = pd.DataFrame(rows)
    df.insert(0, "session", day)
    return day, None, df, dict(n_zones=int(len(S.Z)), n_exp=len(S.exp), n_events=int((df.kind == 1).sum()) if len(df) else 0)


def _hl(day):
    t = pq.read_table(X.BASE / "l1_quotes" / f"{day}.parquet", columns=["side", "price_tick"]).to_pandas()
    p = t.price_tick[t.side == 2]
    return day, ((float(p.max()), float(p.min())) if len(p) > 1000 else None)


def _job(args):
    day, prev = args
    d, skip, df, info = session_rows(day, prev)
    if df is not None:
        (OUT / "rows").mkdir(parents=True, exist_ok=True)
        df.to_parquet(OUT / "rows" / f"{d}.parquet", index=False)
    return d, skip, info


def step_run(workers):
    OUT.mkdir(parents=True, exist_ok=True)
    days = X.sessions_in(X.EXP_RANGE)
    allday = sorted(p.stem for p in (X.BASE / "l1_quotes").glob("*.parquet") if p.stem < days[-1])
    with ProcessPoolExecutor(workers) as ex:
        hl = dict(ex.map(_hl, allday))
    prev = {}
    last = None
    for d in allday:                                                       # sesión previa con actividad
        prev[d] = hl.get(last) if last else None
        if hl.get(d):
            last = d
    log = OUT / "run_log.jsonl"
    done = {json.loads(x)["session"] for x in log.read_text(encoding="utf-8").splitlines()} if log.exists() else set()
    todo = [(d, prev.get(d)) for d in days if d not in done]
    with ProcessPoolExecutor(workers) as ex:
        for d, skip, info in ex.map(_job, todo):
            rec = dict(session=d, skip=skip, **(info or {}))
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            print(json.dumps(rec), flush=True)


# ---------------------------------------------------------------- etapa 1: discretización declarada
def block(sod):
    h = sod / 3600.0                                                       # ART
    if 10.5 <= h < 11.5:
        return "apertura_RTH"
    if 11.5 <= h < 16.0:
        return "RTH"
    if 16.0 <= h < 18.0:
        return "cierre"
    if 4.0 <= h < 10.5:
        return "Europa"
    return "Asia"


def discretize(D, cuts):
    C = pd.DataFrame(index=D.index)
    C["C1_zona"] = D.C1_zona
    C["C2_toques"] = np.where(D.C1_zona == "afuera", "sin_zona",
                              np.where(D.C2_toques == 0, "0", np.where(D.C2_toques <= 2, "1-2", ">=3")))
    C["C3_exp"] = np.where(D.C3_exp_dist <= NEAR_EDGE, "borde", "no")
    C["C3_dwell"] = np.where(D.C3_dwell_dist <= NEAR_EDGE, "borde", "no")
    C["C4_extrema"] = D.C4_extrema.map({1: "alineada", -1: "opuesta", 2: "sin_cuerpo", 0: "no"})
    for w in ("r5", "r30"):
        s = cuts[f"sigma_{w}"]
        C[f"C5_{w}"] = np.where(D[f"C5_{w}"] > 0.5 * s, "a_favor", np.where(D[f"C5_{w}"] < -0.5 * s, "contra", "lateral"))
    C["C6_vwap"] = np.where(D.C6_vwap > 0, "a_favor", "contra")
    C["C7_ext"] = np.where(D.C7_ext_dist <= NEAR_EXT, np.where(D.C7_ext_dir > 0, "alineado", "opuesto"), "no")
    C["C8_round"] = np.where(D.C8_round_dist <= NEAR_EXT, "si", "no")
    for v in ("spread", "depth"):
        a, b = cuts[f"{v}_t"]
        C[f"C9_{v}"] = np.where(D[f"C9_{v}"] <= a, "bajo", np.where(D[f"C9_{v}"] <= b, "medio", "alto"))
    C["C10_bloque"] = D.C10_sod.map(block)
    C["C11_qi"] = np.where(D.C11_qi >= 0.33, "a_favor", np.where(D.C11_qi <= -0.33, "contra", "neutral"))
    C["C12_rota"] = np.where(D.C12_rota == 1, "si", "no")
    return C


def ycol(ch, h):
    return f"race{ch[4:]}_{h}" if ch.startswith("race") else f"{ch}{h}"


def boot_weights(n_s):
    r = np.random.default_rng(SEED)
    return np.stack([np.bincount(r.integers(0, n_s, n_s), minlength=n_s) for _ in range(N_BOOT)]).astype(float)


def cell_stats(sess_idx, y, kind, inC, W, n_s):
    """Suma y conteo por sesión de las 4 celdas; estimación agrupada y bootstrap por sesión."""
    S, N = np.zeros((n_s, 4)), np.zeros((n_s, 4))
    cell = kind * 2 + inC                                                  # 0 c¬C, 1 cC, 2 e¬C, 3 eC
    np.add.at(S, (sess_idx, cell), y)
    np.add.at(N, (sess_idx, cell), 1)

    def est(Sm, Nm):
        with np.errstate(invalid="ignore", divide="ignore"):
            m = Sm / Nm
        return (m[..., 3] - m[..., 1]) - (m[..., 2] - m[..., 0]), m[..., 1] - m[..., 0], m[..., 2] - m[..., 0]
    I, Ca, Aa = est(S.sum(0), N.sum(0))
    bI, bC, bA = est(W @ S, W @ N)
    return dict(I=I, C_alone=Ca, A_alone=Aa, bI=bI, bC=bC, bA=bA, n_ev_in=int(N[:, 3].sum()),
                sess_ev_in=int((N[:, 3] > 0).sum()), S=S, N=N)


def ci(b):
    b = b[np.isfinite(b)]
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)), float(b.std())] if len(b) > 50 else [None, None, None]


def loo_min(S, N):
    out = []
    for s in range(len(S)):
        Sm, Nm = S.sum(0) - S[s], N.sum(0) - N[s]
        with np.errstate(invalid="ignore", divide="ignore"):
            m = Sm / Nm
        out.append((m[3] - m[1]) - (m[2] - m[0]))
    return float(np.nanmin(out))


def bh(p, q):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    thr = q * (np.arange(1, m + 1) / m)
    passed = np.zeros(m, bool)
    k = np.flatnonzero(p[o] <= thr)
    if len(k):
        passed[o[: k.max() + 1]] = True
    return passed


# ---------------------------------------------------------------- etapa 2: árbol honesto
TREE_FEATS = ["C1_dist", "C2_toques", "C3_exp_dist", "C3_dwell_dist", "C4_extrema", "C5_r5", "C5_r30", "C6_vwap",
              "C7_ext_dist", "C8_round_dist", "C9_spread", "C9_depth", "C10_sod", "C11_qi", "C12_rota"]


def tau_frame(D, y):
    ctrl = D[D.kind == 0].groupby(["session", "match"])[y].mean().rename("yc")
    E = D[D.kind == 1].join(ctrl, on=["session", "match"]).dropna(subset=["yc"])
    E["tau"] = E[y] - E["yc"]
    return E


def grow(E, depth, min_sess, path=()):
    node = dict(path=list(path), n=len(E), sess=int(E.session.nunique()), mean=float(E.tau.mean()) if len(E) else None)
    if depth == 0:
        return [node]
    best = None
    tot = E.tau.sum()
    for f in TREE_FEATS:
        x = E[f].astype(float)
        if x.isna().all():
            continue
        for cpt in np.unique(np.nanpercentile(x, np.arange(10, 100, 10))):
            L = x <= cpt
            if E.session[L].nunique() < min_sess or E.session[~L & x.notna()].nunique() < min_sess:
                continue
            nl, nr = L.sum(), (~L).sum()
            sl = E.tau[L].sum()
            gain = sl ** 2 / nl + (tot - sl) ** 2 / nr - tot ** 2 / len(E)
            if best is None or gain > best[0]:
                best = (gain, f, float(cpt))
    if best is None:
        return [node]
    _, f, cpt = best
    L = E[f].astype(float) <= cpt
    return (grow(E[L], depth - 1, min_sess, path + ((f, "<=", cpt),)) +
            grow(E[~L], depth - 1, min_sess, path + ((f, ">", cpt),)))


def apply_path(E, path):
    m = pd.Series(True, index=E.index)
    for f, op, c in path:
        x = E[f].astype(float)
        m &= (x <= c) if op == "<=" else (x > c)
    return E[m]


def sess_boot_mean(E):
    g = E.groupby("session").tau.agg(["sum", "count"])
    if len(g) < 5:
        return [None, None]
    r = np.random.default_rng(SEED)
    idx = r.integers(0, len(g), (N_BOOT, len(g)))
    b = g["sum"].to_numpy()[idx].sum(1) / g["count"].to_numpy()[idx].sum(1)
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


def step_report():
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus import LessonCandidate
    log = [json.loads(x) for x in (OUT / "run_log.jsonl").read_text(encoding="utf-8").splitlines()]
    used = sorted(r["session"] for r in log if not r.get("skip") and (OUT / "rows" / f"{r['session']}.parquet").exists())
    used = [d for d in used if X.EXP_RANGE[0] <= d <= X.EXP_RANGE[1]]     # guarda: sólo exploración
    D = pd.concat([pd.read_parquet(OUT / "rows" / f"{d}.parquet") for d in used], ignore_index=True)
    ctl = D[D.kind == 0]                                                   # cortes target-free, desde los controles
    cuts = dict(sigma_r5=float(ctl.C5_r5.abs().median()), sigma_r30=float(ctl.C5_r30.abs().median()),
                spread_t=np.percentile(ctl.C9_spread, [33.3, 66.7]).tolist(), depth_t=np.percentile(ctl.C9_depth, [33.3, 66.7]).tolist())
    C = discretize(D, cuts)
    sess_idx = D.session.map({d: i for i, d in enumerate(used)}).to_numpy()
    n_s = len(used)
    W = boot_weights(n_s)
    kind = D.kind.to_numpy().astype(int)
    cells = []
    for cn in C.columns:
        for lv in sorted(C[cn].dropna().unique()):
            inC = (C[cn] == lv).to_numpy().astype(int)
            if inC.sum() == 0 or inC.sum() == len(inC):
                continue
            spr_floor = float(D.spread0[(kind == 1) & (inC == 1)].median()) if ((kind == 1) & (inC == 1)).any() else np.nan
            for ch in CHANNELS:
                for h in HZ:
                    y = D[ycol(ch, h)].to_numpy(float)
                    st = cell_stats(sess_idx, y, kind, inC, W, n_s)
                    lo, hi, sd = ci(st["bI"])
                    z = (st["I"] / sd) if sd else np.nan
                    from math import erfc, sqrt
                    p = erfc(abs(z) / sqrt(2)) if np.isfinite(z) else 1.0
                    scale = int(ch[4:]) if ch.startswith("race") else 1   # carrera: I (prob. neta) × X = ticks esperados
                    cells.append(dict(context=cn, level=lv, channel=ch, h=h, I=float(st["I"]), ci=[lo, hi], p=p,
                                      mde=(2.8 * sd if sd else None), I_ticks=float(st["I"]) * scale,
                                      ci_lo_ticks=(lo * scale if lo is not None else None),
                                      C_alone=float(st["C_alone"]), C_alone_ci=ci(st["bC"])[:2],
                                      A_alone=float(st["A_alone"]), A_alone_ci=ci(st["bA"])[:2],
                                      n_ev_in=st["n_ev_in"], sess_ev_in=st["sess_ev_in"], spread_floor=spr_floor,
                                      _S=st["S"], _N=st["N"]))
    passed = bh([c["p"] for c in cells], FDR_Q)
    sug = []
    for c, ps in zip(cells, passed):
        c["fdr_pass"] = bool(ps)
        pure = (c["C_alone_ci"][0] is not None and c["C_alone_ci"][0] <= 0 <= c["C_alone_ci"][1] and
                c["A_alone_ci"][0] is not None and c["A_alone_ci"][0] <= 0 <= c["A_alone_ci"][1])
        c["sinergia_pura"] = bool(pure)
        ok = (ps and c["I"] > 0 and c["channel"] in DIRECTIONAL and np.isfinite(c["spread_floor"]) and
              c["I_ticks"] >= c["spread_floor"] and c["n_ev_in"] >= MIN_EV and c["sess_ev_in"] >= MIN_SESS)
        if ok:
            c["loo_min"] = loo_min(c["_S"], c["_N"])
            ok = c["loo_min"] > 0
        c["candidate"] = bool(ok)
        if ok:
            sug.append(c)
    for c in cells:
        c.pop("_S"); c.pop("_N")
    # etapa 2: árbol honesto (mitades de sesiones al azar, fijas por semilla)
    r = np.random.default_rng(SEED)
    perm = list(r.permutation(used))
    grow_s, est_s = set(perm[: n_s // 2]), set(perm[n_s // 2:])
    trees = []
    for ch, h in (("asym", 60), ("asym", 300), ("sig", 60), ("sig", 300)):
        E = tau_frame(D, ycol(ch, h))
        leaves = grow(E[E.session.isin(grow_s)], 3, MIN_SESS)
        Eest = E[E.session.isin(est_s)]
        for lf in leaves:
            sub = apply_path(Eest, lf["path"])
            lo, hi = sess_boot_mean(sub)
            spr = float(Eest.loc[sub.index, "spread0"].median()) if len(sub) else np.nan
            leaf = dict(channel=ch, h=h, path=lf["path"], grow_mean=lf["mean"], grow_n=lf["n"], est_mean=float(sub.tau.mean()) if len(sub) else None,
                        est_ci=[lo, hi], est_n=len(sub), est_sess=int(sub.session.nunique()), spread_floor=spr)
            leaf["candidate"] = bool(lo is not None and lo > 0 and leaf["est_mean"] >= spr and len(sub) >= MIN_EV and leaf["est_sess"] >= MIN_SESS)
            trees.append(leaf)
    ranked = sorted([("S1", c, c["ci_lo_ticks"]) for c in sug] +
                    [("T", t, t["est_ci"][0]) for t in trees if t["candidate"]], key=lambda x: -x[2])[:TOP_K]
    body = dict(schema="EDGELAB_NQ_L2_SYNERGY_V1", manifest=MANIF, code_commit=X._git("rev-parse", "HEAD"),
                tree_dirty=bool(X._git("status", "--porcelain", "--", "tools", "edgelab")), sessions_used=used,
                skipped=[(r_["session"], r_["skip"]) for r_ in log if r_.get("skip")], cuts=cuts,
                n_rows=int(len(D)), n_events=int((D.kind == 1).sum()), n_cells=len(cells), n_fdr_pass=int(passed.sum()),
                stage1=cells, stage2=trees, grow_sessions=sorted(grow_s), est_sessions=sorted(est_s),
                top_suggestions=[dict(src=s, **{k: v for k, v in c.items()}) for s, c, _ in ranked])
    raw = json.dumps(body, indent=1, default=lambda o: (float(o) if isinstance(o, (np.floating, np.integer)) else str(o)))
    (OUT / "report.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    with measurement_episode(LEDGER, f"EP-NQL2-SYN-20260924{TAG}", goal="NQ L2: absorción × contexto (interacción)",
                             recorded_by="tools/nq_l2_synergy.py report", repo=REPO, prereg_ref=MANIF) as ep:
        ep.store.record_observation(f"OBS-NQL2-SYN-S1{TAG}", "interacción absorción × C1–C12", "RESPONSE_PROFILE", ["P-NQL2-EXP"],
                                    dict(n_cells=len(cells), n_fdr_pass=int(passed.sum()), n_candidates=len(sug)),
                                    {"sessions": n_s}, sha, depends_on=["CODE:AbsorptionTracker@causal", "CODE:HFTZonesUniversal@NQ_LITERAL",
                                                                        "DATA:l2_parquet/NQ_09-26"])
        ep.store.record_observation(f"OBS-NQL2-SYN-S2{TAG}", "árbol honesto sobre τ", "RESPONSE_PROFILE", ["P-NQL2-EXP"],
                                    dict(leaves=len(trees), candidates=sum(t["candidate"] for t in trees)), {"sessions": n_s}, sha)
        for i, (s, c, _) in enumerate(ranked):
            txt = (f"{c['context']}={c['level']} {c['channel']}{c['h']}s: I={c['I_ticks']:.2f} ticks (lo {c['ci_lo_ticks']:.2f})"
                   if s == "S1" else f"hoja {c['path']} {c['channel']}{c['h']}s: τ={c['est_mean']:.2f} (lo {c['est_ci'][0]:.2f})")
            ep.store.record_lesson(LessonCandidate(lesson_id=f"SUG-NQ-SYN{TAG}-{i + 1}", episode_id=f"EP-NQL2-SYN-20260924{TAG}",
                                                   statement=txt + ". Confirmar SOLO en P-NQL2-CONF con protocolo firmado.",
                                                   confidence="LOW", status="PROPOSED", scope="SUGGESTED_ANALYSIS"))
    print(json.dumps(dict(sessions=n_s, events=body["n_events"], cells=len(cells), fdr_pass=int(passed.sum()),
                          candidates=len(sug), tree_candidates=sum(t["candidate"] for t in trees), top=len(ranked), sha=sha[:12])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["run", "report", "one"])
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--day")
    a = ap.parse_args(argv)
    if a.step == "run":
        step_run(a.workers)
    elif a.step == "report":
        step_report()
    else:
        d, skip, df, info = session_rows(a.day, None)
        print(skip, info, None if df is None else df.describe().T.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
