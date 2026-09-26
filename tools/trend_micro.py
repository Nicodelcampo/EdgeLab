#!/usr/bin/env python3
r"""TREND-MICRO: rupturas con filtro de microestructura. Manifiesto con iteración 1:
docs/research/MANIFIESTO_TREND_MICRO_20260924.md (OK de Nico: "OK manifiestos TBZ-E2 y TREND-MICRO, adelante con todo").

Bases: B1 ruptura de PDH/PDL (sesión previa) y de ONH/ONL (rango hasta 09:30 ET), B2 primera ruptura de cada número
redondo de la sesión, B3 disparo de una expansión TBZ (W20 k4) en la dirección de la franja previa viva.
Filtros: F0 ninguno, F1 absorción que cedió (sólo NQ, P-93), F2 F1 + cascada (sólo NQ; entrada 10 s después),
F3 alineado con VWAP y EMA50 de 1 min. Targets 2R y 4R, stop nivel - 0,5 sigma5, tiempo máximo 60 min.
Unidad primaria: la señal (estudio de eventos); la versión "una posición a la vez" es descriptiva.

Pasos: declare -> prep -> run -> phantoms -> report. Como máximo 2 procesos (P-92, dos cuelgues de la PC).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import tbz_e2 as TB  # noqa: E402  (sesiones desde los bundles, reglas de sesión)
from edgelab.bridge.bars import build_tick_bars  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.research.l2_manipulation_heuristics import ASK, AbsorptionTracker  # noqa: E402
from edgelab.research.tbz_bands import expansion_bands  # noqa: E402

OUT = REPO / "artifacts" / "trend_micro"
LEDGER = REPO / "artifacts" / "hippocampus" / "trend_micro_20260924.jsonl"
MANIF = "docs/research/MANIFIESTO_TREND_MICRO_20260924.md"
NS = 1_000_000_000
ET = ZoneInfo("America/New_York")
EXP_END = "20260331"
INSTR = {"ES": dict(round_t=100, comm=0.2, aggr_ok=False), "NQ": dict(round_t=400, comm=0.5, aggr_ok=True)}
LAT_NS = 250_000_000
TMAX_S = 3600
MULTS = (2, 4)
BASES = ("B1", "B2", "B3")
FILTERS = ("F0", "F1", "F2", "F3")
SEED, N_BOOT, FDR_Q = 20260924, 2000, 0.10


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def sessions(inst):
    return TB.sessions(inst)


def load_ticks(s):
    tbl = pq.read_table(s["path"], columns=["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "aggressor"],
                        filters=[("contract", "==", s["contract"]), ("ts_utc_ns", ">=", s["start"]), ("ts_utc_ns", "<", s["end"])])
    df = tbl.to_pandas()
    ag = df.aggressor.map({"buy": 1, "sell": -1}).fillna(0).to_numpy().astype(np.int8)
    return (df.ts_utc_ns.to_numpy(np.int64), df.price_ticks.to_numpy(np.int64), df.volume.to_numpy(float),
            df.bid_ticks.to_numpy(np.int64), df.ask_ticks.to_numpy(np.int64), ag)


def et(ns):
    return pd.Timestamp(int(ns), tz="UTC").tz_convert(ET)


# ------------------------------------------------------------------------------------------------ prep (target-free)
def prep_session(args):
    inst, s = args
    out = OUT / "prep" / inst / f"{s['trade_date']}.json"
    ts, px, vol, bid, ask, ag = load_ticks(s)
    if len(ts) < 5000 or bool((np.diff(ts) < 0).any()):
        meta = dict(skip=True)
    else:
        m = ts // (60 * NS); last = np.r_[m[1:] != m[:-1], True]
        b10 = ts // (10 * NS)
        def p90(sign):
            v = pd.Series(np.where(ag == sign, vol, 0.0)).groupby(b10).sum()
            return float(np.percentile(v, 90)) if len(v) else np.nan
        meta = dict(skip=False, contract=s["contract"], high=int(px.max()), low=int(px.min()),
                    minute_end=((m[last] + 1) * 60 * NS).tolist(), minute_close=px[last].astype(float).tolist(),
                    p90_buy10=p90(1), p90_sell10=p90(-1))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(meta), encoding="utf-8")
    return inst, s["trade_date"], meta.get("skip")


# ------------------------------------------------------------------------------------------------ simulación
def simulate(ts, px, bid, ask, t_entry_ns, tdir, stop, target, end_ns, comm):
    i = int(np.searchsorted(ts, t_entry_ns))
    if i >= len(ts):
        return None
    entry = int(ask[i] if tdir == 1 else bid[i]); x0 = int(px[i])
    j1 = max(int(np.searchsorted(ts, min(int(ts[i]) + TMAX_S * NS, end_ns))), i + 1)
    seg = px[i:j1]
    hs, ht = (seg <= stop, seg >= target + 1) if tdir == 1 else (seg >= stop, seg <= target - 1)
    ks = int(np.argmax(hs)) if hs.any() else 10**12
    kt = int(np.argmax(ht)) if ht.any() else 10**12
    if ks == kt == 10**12:
        k = j1 - 1; ex, why, tex = int(bid[k] if tdir == 1 else ask[k]), "tiempo", int(ts[k])
    elif ks <= kt:
        ex, why, tex = int(seg[ks]), "stop", int(ts[i + ks])
    else:
        ex, why, tex = int(target), "target", int(ts[i + kt])
    s_eff = max(tdir * (x0 - stop), 0); r_eff = max(tdir * ((target + tdir) - x0), 0)
    p0 = s_eff / (s_eff + r_eff) if (s_eff + r_eff) > 0 else np.nan
    return dict(entry=entry, exit=ex, pnl=tdir * (ex - entry) - 2 * comm, why=why, t_exit=tex, p0=p0, t_in=int(ts[i]))


# ------------------------------------------------------------------------------------------------ señales
def sigma5(minute_close_hist):
    c = np.asarray(minute_close_hist, float)
    if len(c) < 400:
        return np.nan
    d = np.abs(c[5:] - c[:-5])
    return float(np.median(d[-3000:]))


def signals_session(inst, s, ts, px, vol, ag, prev_meta, hist_close):
    cfg = INSTR[inst]
    sig = []
    t_rth = et(s["end"]).normalize() + pd.Timedelta(hours=9, minutes=30)
    t_rth_ns = int(t_rth.tz_convert("UTC").value)
    # B1: PDH/PDL de la sesión previa; ONH/ONL hasta 09:30 ET, válidos después de 09:30
    levels = []
    if prev_meta and not prev_meta.get("skip") and prev_meta.get("contract") == s["contract"]:   # PDH/PDL sólo del mismo contrato
        levels += [("PDH", prev_meta["high"], 1, int(ts[0])), ("PDL", prev_meta["low"], -1, int(ts[0]))]
    k_rth = int(np.searchsorted(ts, t_rth_ns))
    if 0 < k_rth < len(ts):
        levels += [("ONH", int(px[:k_rth].max()), 1, t_rth_ns), ("ONL", int(px[:k_rth].min()), -1, t_rth_ns)]
    for name, L, d, t_from in levels:
        k0 = int(np.searchsorted(ts, t_from))
        if k0 >= len(ts) or (d == 1 and px[k0] >= L + 1) or (d == -1 and px[k0] <= L - 1):
            continue                                            # ya estaba del otro lado: no hay ruptura
        seg = px[k0:]
        hit = (seg >= L + 1) if d == 1 else (seg <= L - 1)
        if hit.any():
            k = k0 + int(np.argmax(hit))
            sig.append(dict(base="B1", sub=name, t=int(ts[k]), dir=d, level=int(L)))
    # B2: primera ruptura de cada número redondo en la sesión (por 1 tick)
    R = cfg["round_t"]
    lv = np.floor_divide(px, R)
    ch = np.flatnonzero(lv[1:] != lv[:-1]) + 1
    seen = set()
    for k in ch:
        a, b = lv[k - 1], lv[k]
        L = int(max(a, b) * R)
        if L in seen:
            continue
        d = 1 if b > a else -1
        if (d == 1 and px[k] >= L + 1) or (d == -1 and px[k] <= L - 1):
            seen.add(L)
            sig.append(dict(base="B2", sub=str(L), t=int(ts[k]), dir=d, level=L))
    # B3: disparo de expansión W20 k4 en la dirección de la franja previa viva (<= 240 min)
    return sig


def b3_signals(bands, bars):
    """Disparo = cierre EXACTO (ns) de la vela donde se creó el estado; la franja previa es la de t_avail más reciente."""
    out = []
    for b in sorted(bands, key=lambda b: b["t_trigger"]):
        t_trig = int(bars.end_ns[b["i_trigger"]])
        prev = [p for p in bands if int(bars.end_ns[p["i_avail"]]) <= t_trig and t_trig - int(bars.end_ns[p["i_avail"]]) <= 240 * 60 * NS]
        if prev:
            pv = max(prev, key=lambda p: p["i_avail"])
            if pv["dir"] == b["dir"]:
                out.append(dict(base="B3", sub="cont", t=t_trig, dir=int(b["dir"]), level=int(pv["b_tick"]), a_tick=int(b["a_tick"])))
    return out


def run_session(args):
    inst, s, prev_meta, hist_close = args
    cfg = INSTR[inst]
    out = OUT / "signals" / inst / f"{s['trade_date']}.parquet"
    ts, px, vol, bid, ask, ag = load_ticks(s)
    if len(ts) < 5000 or bool((np.diff(ts) < 0).any()):
        return inst, s["trade_date"], dict(skip="POCA_ACTIVIDAD_O_NO_MONOTONO")
    sig5 = sigma5(hist_close)
    if not np.isfinite(sig5) or sig5 <= 0:
        return inst, s["trade_date"], dict(skip="SIN_HISTORIA_SIGMA")
    sigs = signals_session(inst, s, ts, px, vol, ag, prev_meta, hist_close)
    tk = load_canonical_parquet(s["path"], contract=s["contract"], start_utc_ns=s["start"], end_utc_ns=s["end"])
    bars = build_tick_bars(tk, 25, reiniciar_por_sesion=True)
    tsec = (bars.end_ns // NS).astype(np.int64)
    bands = expansion_bands(tsec, bars.open_t * bars.tick_size, bars.high_t * bars.tick_size, bars.low_t * bars.tick_size,
                            bars.close_t * bars.tick_size, bars.tick_size, W=20, k=4.0)
    sigs += b3_signals(bands, bars)
    # contexto causal
    m = ts // (60 * NS); last = np.r_[m[1:] != m[:-1], True]
    m_end = (m[last] + 1) * 60 * NS; m_close = px[last].astype(float)
    ema50 = pd.Series(np.r_[np.asarray(hist_close[-300:], float), m_close]).ewm(span=50, adjust=False).mean().to_numpy()[-len(m_close):]
    cum_pv, cum_v = np.cumsum(px * vol), np.cumsum(vol)
    absn = []
    if cfg["aggr_ok"]:
        tr = AbsorptionTracker()
        for p_, t_, v_, a_ in zip(px, ts // 1000, vol, ag):
            tr.on_trade(int(p_), int(t_), float(v_), int(a_))
        absn = [(c["available_ts_us"] * 1000, c["tick"], c["side"]) for c in tr.candidates()]
    ab_t = np.array([a[0] for a in absn], dtype=np.int64); ab_tick = np.array([a[1] for a in absn]); ab_side = [a[2] for a in absn]
    rows = []
    for g in sigs:
        t, d, L = g["t"], g["dir"], g["level"]
        k = max(int(np.searchsorted(ts, t, "right")) - 1, 0)
        mi = int(np.searchsorted(m_end, t, "right")) - 1
        vw = cum_pv[k] / cum_v[k] if cum_v[k] > 0 else np.nan
        e50 = ema50[mi] if mi >= 0 else np.nan
        f3 = bool(np.isfinite(vw) and np.isfinite(e50) and d * (px[k] - vw) > 0 and d * (px[k] - e50) > 0)
        f1 = None; f2 = None
        if cfg["aggr_ok"]:
            want = ASK if d == 1 else "BID"
            sel = (ab_t >= t - 300 * NS) & (ab_t < t) & (np.abs(ab_tick - L) <= 2) if len(ab_t) else np.array([], bool)
            f1 = bool(any((ab_side[i] == ASK) == (d == 1) for i in np.flatnonzero(sel))) if len(ab_t) else False
            a0, a1 = int(np.searchsorted(ts, t, "right")), int(np.searchsorted(ts, t + 10 * NS, "right"))
            vdir = float(vol[a0:a1][ag[a0:a1] == d].sum())
            thr = (prev_meta or {}).get("p90_buy10" if d == 1 else "p90_sell10", np.nan)
            f2 = bool(f1 and np.isfinite(thr) and vdir >= thr)
            _ = want
        base_stop_level = g.get("a_tick", L) if g["base"] == "B3" else L
        stop = int(base_stop_level - d * int(np.ceil(0.5 * sig5)))
        for lagname, extra in (("t0", 0), ("t10", 10 * NS)):
            t_in = t + extra + LAT_NS
            i_in = int(np.searchsorted(ts, t_in))
            if i_in >= len(ts):
                continue
            entry_ref = int(ask[i_in] if d == 1 else bid[i_in])
            if d * (entry_ref - stop) < 2:
                continue                                    # la señal ya se invalidó antes de poder entrar
            risk = int(d * (entry_ref - stop))
            st = stop
            for mlt in MULTS:
                target = entry_ref + d * mlt * risk
                r = simulate(ts, px, bid, ask, t_in, d, st, target, s["end"], cfg["comm"])
                if r is None:
                    continue
                rows.append(dict(base=g["base"], sub=g["sub"], t_sig=int(t), dir=d, level=int(L), lag=lagname, mult=mlt,
                                 risk=int(risk), f1=f1, f2=f2, f3=f3, sigma5=sig5, R=r["pnl"] / risk, **r))
    D = pd.DataFrame(rows)
    D.insert(0, "session", s["trade_date"])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".partial"); D.to_parquet(tmp, index=False); tmp.replace(out)
    return inst, s["trade_date"], dict(signals=len(sigs), rows=len(D))


def step_declare():
    from edgelab.edge_brain.episode_logger import measurement_episode
    with measurement_episode(LEDGER, "EP-TMIC-DECLARE-20260924", goal="TREND-MICRO: particiones antes de medir",
                             recorded_by="tools/trend_micro.py declare", repo=REPO, prereg_ref=MANIF) as ep:
        for inst in INSTR:
            ds = [s["trade_date"] for s in sessions(inst)]
            ep.store.record_partition(f"P-TMIC-{inst}-EXP", "EXPLORATION", f"TREND-MICRO {inst} hasta {EXP_END}",
                                      [f"{inst}:{d}" for d in ds if d <= EXP_END])
            ep.store.record_partition(f"P-TMIC-{inst}-CONF", "CONFIRMATION_RESERVED", f"TREND-MICRO {inst} desde 20260401 (pre-holdout)",
                                      [f"{inst}:{d}" for d in ds if d > EXP_END])
    print("declaradas")


def step_prep(inst, workers):
    ss = sessions(inst)
    todo = [(inst, s) for s in ss if not (OUT / "prep" / inst / f"{s['trade_date']}.json").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for fu in as_completed([ex.submit(prep_session, t) for t in todo]):
            print(*fu.result(), flush=True)


def step_run(inst, workers):
    ss = [s for s in sessions(inst) if s["trade_date"] <= EXP_END]
    allss = sessions(inst)
    metas = {}
    for s in allss:
        f = OUT / "prep" / inst / f"{s['trade_date']}.json"
        metas[s["trade_date"]] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    order = [s["trade_date"] for s in allss]
    jobs = []
    for s in ss:
        if (OUT / "signals" / inst / f"{s['trade_date']}.parquet").exists():
            continue
        i = order.index(s["trade_date"])
        prev = next((metas[order[j]] for j in range(i - 1, -1, -1) if metas.get(order[j]) and not metas[order[j]].get("skip")), None)
        hist = []
        for j in range(i - 1, -1, -1):
            m = metas.get(order[j])
            if m and not m.get("skip"):
                hist = m["minute_close"] + hist
            if len(hist) >= 3300:
                break
        jobs.append((inst, s, prev, hist))
    with ProcessPoolExecutor(workers) as ex:
        for fu in as_completed([ex.submit(run_session, j) for j in jobs]):
            print(*fu.result(), flush=True)


def cell_filter(D, f):
    if f == "F0":
        return D[D.lag == "t0"]
    if f == "F1":
        return D[(D.lag == "t0") & (D.f1 == True)]  # noqa: E712
    if f == "F2":
        return D[(D.lag == "t10") & (D.f2 == True)]  # noqa: E712
    return D[(D.lag == "t0") & (D.f3 == True)]  # noqa: E712


def step_report(inst_list):
    from math import erfc, sqrt
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus import LessonCandidate
    cells = []
    for inst in inst_list:
        files = sorted((OUT / "signals" / inst).glob("*.parquet"))
        if not files:
            continue
        D = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        D = D[D.session <= EXP_END]
        sess = sorted(D.session.unique()); n_s = len(sess); si = {d: i for i, d in enumerate(sess)}
        rng = np.random.default_rng(SEED)
        W = np.stack([np.bincount(rng.integers(0, n_s, n_s), minlength=n_s) for _ in range(N_BOOT)]).astype(float)
        D["si"] = D.session.map(si); D["month"] = D.session.str.slice(0, 6)
        for base in BASES:
            for f in FILTERS:
                if f in ("F1", "F2") and not INSTR[inst]["aggr_ok"]:
                    continue
                for mlt in MULTS:
                    B0 = D[(D.base == base) & (D.mult == mlt) & (D.lag == ("t10" if f == "F2" else "t0"))]
                    C = cell_filter(B0, f) if f != "F2" else B0[B0.f2 == True]  # noqa: E712
                    if len(C) < 30:
                        cells.append(dict(inst=inst, base=base, filtro=f, mult=mlt, n=int(len(C)), status="SIN_MUESTRA"))
                        continue
                    def bm(df, col):
                        S = np.zeros(n_s); N = np.zeros(n_s)
                        np.add.at(S, df.si.to_numpy(), df[col].to_numpy(float)); np.add.at(N, df.si.to_numpy(), 1)
                        with np.errstate(invalid="ignore", divide="ignore"):
                            b = (W @ S) / (W @ N)
                        return S, N, b
                    S, N, bR = bm(C, "R")
                    Sb, Nb, bRb = bm(B0, "R")
                    pt = S.sum() / N.sum(); sd = np.nanstd(bR)
                    syn = bR - bRb
                    C2 = C.assign(ex=(C.why == "target").astype(int) - C.p0)
                    _, _, bex = bm(C2, "ex")
                    p = erfc(abs(pt / sd) / sqrt(2)) if sd > 0 else 1.0
                    cells.append(dict(inst=inst, base=base, filtro=f, mult=mlt, n=int(len(C)), sesiones=int(C.session.nunique()),
                                      R=[float(pt), float(np.nanpercentile(bR, 2.5)), float(np.nanpercentile(bR, 97.5))], p=p,
                                      hit=float((C.why == "target").mean()), p0_N1=float(C.p0.mean()),
                                      exceso_hit_N1=[float(np.nanmean(bex)), float(np.nanpercentile(bex, 2.5)), float(np.nanpercentile(bex, 97.5))],
                                      sinergia_vs_base=[float(np.nanmean(syn)), float(np.nanpercentile(syn, 2.5)), float(np.nanpercentile(syn, 97.5))],
                                      meses_positivos=float((C.groupby("month").R.mean() > 0).mean()),
                                      salidas=C.why.value_counts(normalize=True).round(3).to_dict(), status="OK"))
    ok_cells = [c for c in cells if c["status"] == "OK"]
    ps = np.array([c["p"] for c in ok_cells]); m = len(ps); o = np.argsort(ps)
    passed = np.zeros(m, bool); kk = np.flatnonzero(ps[o] <= FDR_Q * np.arange(1, m + 1) / m)
    if len(kk):
        passed[o[:kk.max() + 1]] = True
    sug = []
    for c, pz in zip(ok_cells, passed):
        c["fdr"] = bool(pz)
        syn_ok = c["filtro"] == "F0" or c["sinergia_vs_base"][1] > 0
        c["sugerencia"] = bool(pz and c["R"][1] > 0 and c["exceso_hit_N1"][1] > 0 and syn_ok and c["meses_positivos"] >= 0.55)
        if c["sugerencia"]:
            sug.append(c)
    top = sorted(sug, key=lambda c: -c["R"][1])[:3]
    body = dict(schema="EDGELAB_TREND_MICRO_V1", manifest=MANIF, code_commit=_git("rev-parse", "HEAD"),
                tree_dirty=bool(_git("status", "--porcelain", "--", "tools", "edgelab")), celdas=cells, sugerencias_top=top)
    raw = json.dumps(body, indent=1, default=float)
    (OUT / "report.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    with measurement_episode(LEDGER, "EP-TMIC-20260924", goal="TREND-MICRO: rupturas con filtro de microestructura",
                             recorded_by="tools/trend_micro.py report", repo=REPO, prereg_ref=MANIF) as ep:
        for inst in inst_list:
            cc = [c for c in ok_cells if c["inst"] == inst]
            if cc:
                ep.store.record_observation(f"OBS-TMIC-{inst}", f"TREND-MICRO {inst}: R neto por señal", "RESPONSE_PROFILE",
                                            [f"P-TMIC-{inst}-EXP"], {f"{c['base']}|{c['filtro']}|{c['mult']}R": c["R"] for c in cc},
                                            {"cells": len(cc)}, sha, design="NO_CONTROL")
        for i, c in enumerate(top):
            ep.store.record_lesson(LessonCandidate(
                lesson_id=f"SUG-TMIC-{i + 1}", episode_id="EP-TMIC-20260924",
                statement=f"{c['inst']} {c['base']} {c['filtro']} {c['mult']}R: R {c['R'][0]:.3f} (IC {c['R'][1]:.3f}..{c['R'][2]:.3f}). Confirmar SOLO en P-TMIC-*-CONF.",
                confidence="LOW", status="PROPOSED", scope="SUGGESTED_ANALYSIS"))
    print(json.dumps(dict(celdas=len(ok_cells), fdr=int(passed.sum()), sugerencias=len(sug), sha=sha[:12])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["declare", "prep", "run", "report", "one"])
    ap.add_argument("--inst", default="NQ")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--day")
    a = ap.parse_args(argv)
    if a.step == "declare":
        step_declare()
    elif a.step == "prep":
        step_prep(a.inst, a.workers)
    elif a.step == "run":
        step_run(a.inst, a.workers)
    elif a.step == "report":
        step_report(["ES", "NQ"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
