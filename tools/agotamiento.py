#!/usr/bin/env python3
r"""AGOT-EXT: agotamiento en extremo (divergencia de RSI y de delta). Manifiesto aprobado por Nico el 25/09
("OK manifiesto AGOT-EXT, levanto F9, adelante con todo"): docs/research/MANIFIESTO_AGOTAMIENTO_EN_EXTREMO_20260925.md

Evento: pivote nuevo de zigzag (retroceso >= max(2 t, 0,3*tramo), tramo >= 1,5*ATR20 causal) que supera al pivote previo
del mismo lado (<= 60 barras). Dos momentos: V-RUP (primer trade que supera el pivote previo) y V-CONF (confirmación
del pivote nuevo). Divergencias: RSI de Wilder (14; 7 y 21 sólo como sensibilidad) y, sólo NQ (P-93), delta del tramo.
Operación contra el extremo: entrada agresiva a +250 ms, stop del otro lado del extremo nuevo + max(2 t, 0,25*tramo),
targets 1R y 2R (atravesar por 1 tick), tiempo máximo 30 barras. Decide la sinergia (con contra sin divergencia).

Pasos: declare -> run -> report. Como máximo 1 proceso mientras corre la cola nocturna (P-92, dos cuelgues de la PC).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import tbz_e2 as TB  # noqa: E402  (sesiones desde los bundles)
import trend_micro as TM  # noqa: E402  (lectura de ticks con agresor)

OUT = REPO / "artifacts" / "agot_ext"
LEDGER = REPO / "artifacts" / "hippocampus" / "agot_ext_20260925.jsonl"
MANIF = "docs/research/MANIFIESTO_AGOTAMIENTO_EN_EXTREMO_20260925.md"
NS = 1_000_000_000
EXP_END = "20260331"
RES = {"1m": 60, "5m": 300}
INSTR = {"ES": dict(comm=0.2, delta_ok=False), "NQ": dict(comm=0.5, delta_ok=True)}   # P-93: agresor ES inválido
R_RETR, K_ATR, MIN_TICKS, PREV_MAX_BARS, HOLD_BARS = 0.3, 1.5, 4, 60, 30
LAT_NS = 250_000_000
MULTS = (1, 2)
SEED, N_BOOT, FDR_Q = 20260925, 2000, 0.10


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


# ------------------------------------------------------------------------------------------------ construcción
def time_bars(ts, px, vol, ag, sec):
    """Barras de tiempo sólo donde hubo trades: fin de barra (ns), OHLC en ticks, volumen agresivo comprador y vendedor."""
    b = ts // (sec * NS)
    edge = np.r_[True, b[1:] != b[:-1]]
    idx = np.flatnonzero(edge)
    o = px[idx]
    c = px[np.r_[idx[1:] - 1, len(px) - 1]]
    h = np.maximum.reduceat(px, idx)
    lo = np.minimum.reduceat(px, idx)
    buy = np.add.reduceat(np.where(ag == 1, vol, 0.0), idx)
    sell = np.add.reduceat(np.where(ag == -1, vol, 0.0), idx)
    end = (b[idx] + 1) * sec * NS
    return dict(end=end.astype(np.int64), o=o, h=h, l=lo, c=c.astype(float), buy=buy, sell=sell)


def rsi_wilder(c, n):
    """RSI de Wilder causal; devuelve también los promedios para poder actualizar con un cierre provisorio."""
    d = np.diff(c, prepend=c[0])
    g, l = np.maximum(d, 0.0), np.maximum(-d, 0.0)
    ag, al = np.full(len(c), np.nan), np.full(len(c), np.nan)
    if len(c) > n:
        ag[n], al[n] = g[1:n + 1].mean(), l[1:n + 1].mean()
        for i in range(n + 1, len(c)):
            ag[i] = (ag[i - 1] * (n - 1) + g[i]) / n
            al[i] = (al[i - 1] * (n - 1) + l[i]) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        rsi = 100 - 100 / (1 + ag / al)
    rsi = np.where(al == 0, 100.0, rsi)
    rsi[:3 * n] = np.nan                                     # calentamiento (Wilder converge en ~3n barras)
    return rsi, ag, al


def rsi_provisional(ag_prev, al_prev, close_prev, price, n):
    ch = price - close_prev
    ag = (ag_prev * (n - 1) + max(ch, 0.0)) / n
    al = (al_prev * (n - 1) + max(-ch, 0.0)) / n
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)


def atr_wilder(h, lo, c, n=20):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc))).astype(float)
    out = np.full(len(c), np.nan)
    if len(c) > n:
        out[n] = tr[1:n + 1].mean()
        for i in range(n + 1, len(c)):
            out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def zigzag_adaptive(B, atr):
    """Pivotes con retroceso >= max(2 t, 0,3*tramo) y tramo >= max(4 t, 1,5*ATR20 causal en la vela que confirma).
    Si el precio cruza el pivote de arranque antes de formar el tramo, el pivote de arranque se mueve (no queda trabado)."""
    H, L = B["h"].astype(np.int64), B["l"].astype(np.int64)
    out, d = [], 0
    hi_i, hi_p, lo_i, lo_p = 0, int(H[0]), 0, int(L[0])
    piv_i = piv_p = ext_i = ext_p = 0
    for j in range(1, len(H)):
        mn = max(MIN_TICKS, K_ATR * atr[j]) if np.isfinite(atr[j]) else np.inf
        if d == 0:
            if H[j] > hi_p:
                hi_i, hi_p = j, int(H[j])
            if L[j] < lo_p:
                lo_i, lo_p = j, int(L[j])
            if hi_p - lo_p >= mn:
                if hi_i > lo_i:
                    d, piv_i, piv_p, ext_i, ext_p = 1, lo_i, lo_p, hi_i, hi_p
                else:
                    d, piv_i, piv_p, ext_i, ext_p = -1, hi_i, hi_p, lo_i, lo_p
            if d == 0:
                continue                                     # si se fijó la dirección, se chequea en la MISMA vela
        if d == 1:
            if H[j] > ext_p:
                ext_i, ext_p = j, int(H[j])
            retr = ext_p - int(L[j])
        else:
            if L[j] < ext_p:
                ext_i, ext_p = j, int(L[j])
            retr = int(H[j]) - ext_p
        tot = abs(ext_p - piv_p)
        if tot >= mn and retr >= max(2, R_RETR * tot):
            out.append(dict(dir=d, a=piv_p, b=ext_p, i_a=piv_i, i_ext=ext_i, i_conf=j, tot=tot))
            piv_i, piv_p, d = ext_i, ext_p, -d
            ext_i, ext_p = j, (int(L[j]) if d == -1 else int(H[j]))
        elif (d == 1 and L[j] < piv_p) or (d == -1 and H[j] > piv_p):
            # el tramo nunca llegó al tamaño mínimo y el precio cruzó su arranque: el arranque se mueve (no se traba).
            # Va DESPUÉS del chequeo de confirmación: un tramo ya formado se confirma, no se descarta (bug hallado
            # por test_cada_pivote_se_confirma_en_la_primera_vela_que_cumple_la_regla, 25/09).
            if d == 1:
                piv_i, piv_p, ext_i, ext_p = j, int(L[j]), j, int(H[j])
            else:
                piv_i, piv_p, ext_i, ext_p = j, int(H[j]), j, int(L[j])
    return out


def leg_share(B, i0, i1, d):
    """Fracción de volumen agresivo a favor del tramo (compra para tramos al alza) en las velas (i0, i1]."""
    b, s = B["buy"][i0 + 1:i1 + 1].sum(), B["sell"][i0 + 1:i1 + 1].sum()
    tot = b + s
    return np.nan if tot <= 0 else float(d * (b - s) / tot)


def simulate(ts, px, bid, ask, t_ns, tdir, stop, target, end_ns, comm, hold_s):
    i = int(np.searchsorted(ts, t_ns))
    if i >= len(ts):
        return None
    entry = int(ask[i] if tdir == 1 else bid[i]); x0 = int(px[i])
    j1 = max(int(np.searchsorted(ts, min(int(ts[i]) + hold_s * NS, end_ns))), i + 1)
    seg = px[i:j1]
    hs, ht = (seg <= stop, seg >= target + 1) if tdir == 1 else (seg >= stop, seg <= target - 1)
    ks = int(np.argmax(hs)) if hs.any() else 10**12
    kt = int(np.argmax(ht)) if ht.any() else 10**12
    if ks == kt == 10**12:
        k = j1 - 1; ex, why = int(bid[k] if tdir == 1 else ask[k]), "tiempo"
    elif ks <= kt:
        ex, why = int(seg[ks]), "stop"
    else:
        ex, why = int(target), "target"
    s_eff = max(tdir * (x0 - stop), 0); r_eff = max(tdir * ((target + tdir) - x0), 0)
    p0 = s_eff / (s_eff + r_eff) if (s_eff + r_eff) > 0 else np.nan
    fav = tdir * (seg - x0)
    return dict(entry=entry, exit=ex, pnl=tdir * (ex - entry) - 2 * comm, why=why, p0=p0,
                mfe=float(fav.max()), mae=float(-fav.min()), absmove=float(abs(int(seg[-1]) - x0)))


# ------------------------------------------------------------------------------------------------ eventos
def session_events(inst, s):
    ts, px, vol, bid, ask, ag = TM.load_ticks(s)
    if len(ts) < 5000 or bool((np.diff(ts) < 0).any()):
        return None, "POCA_ACTIVIDAD_O_NO_MONOTONO"
    return compute_events(ts, px, vol, bid, ask, ag, int(s["end"]), INSTR[inst]), None


def compute_events(ts, px, vol, bid, ask, ag, end_ns, cfg):
    """Eventos y resultados de una sesión. Separado de la carga para poder testear la causalidad con datos sintéticos."""
    s = {"end": end_ns}
    rows = []
    for res, sec in RES.items():
        B = time_bars(ts, px, vol, ag, sec)
        if len(B["c"]) < 80:
            continue
        rsi = {n: rsi_wilder(B["c"], n) for n in (7, 14, 21)}
        atr = atr_wilder(B["h"], B["l"], B["c"])
        piv = zigzag_adaptive(B, atr)
        hold_s = HOLD_BARS * sec
        # Los pivotes del zigzag alternan: piv[i] y piv[i + 2] son del mismo lado; piv[i + 1] es el opuesto que los separa.
        for i1 in range(len(piv)):
            p1 = piv[i1]
            side = p1["dir"]                                 # 1 = máximo (fin de tramo al alza), -1 = mínimo
            l0 = piv[i1 + 1] if i1 + 1 < len(piv) else None  # pivote opuesto confirmado que arranca el tramo siguiente
            p2 = piv[i1 + 2] if i1 + 2 < len(piv) else None  # próximo pivote del mismo lado (sólo para V-CONF)
            r1 = {n: rsi[n][0][p1["i_ext"]] for n in rsi}
            sh1 = leg_share(B, p1["i_a"], p1["i_ext"], side)
            ev = []
            # ---- V-CONF: al confirmarse p2 (todo lo usado se conoce en ese instante)
            if p2 is not None and p2["i_ext"] - p1["i_ext"] <= PREV_MAX_BARS and side * (p2["b"] - p1["b"]) >= 1:
                r2 = {n: rsi[n][0][p2["i_ext"]] for n in rsi}
                sh2 = leg_share(B, p2["i_a"], p2["i_ext"], side)
                ev.append(dict(moment="CONF", t=int(B["end"][p2["i_conf"]]), ext=int(p2["b"]), tramo=int(p2["tot"]),
                               div={n: (side * (r2[n] - r1[n]) < 0) if np.isfinite(r1[n]) and np.isfinite(r2[n]) else None for n in rsi},
                               div_delta=(sh2 < sh1) if cfg["delta_ok"] and np.isfinite(sh1) and np.isfinite(sh2) else None))
            # ---- V-RUP: primer trade que supera p1 DESPUÉS de confirmado el pivote opuesto l0, y antes de que se confirme
            #      un pivote nuevo del mismo lado (si se confirmó antes, en ese instante ya se conoce y p1 deja de ser el previo).
            if l0 is not None:
                t_from = int(B["end"][l0["i_conf"]])
                t_to = int(B["end"][p2["i_conf"]]) if p2 is not None else int(s["end"])
                a0, a1 = int(np.searchsorted(ts, t_from)), int(np.searchsorted(ts, t_to))
                seg = px[a0:a1]
                hit = (seg >= p1["b"] + 1) if side == 1 else (seg <= p1["b"] - 1)
                if hit.any():
                    kx = a0 + int(np.argmax(hit))
                    t_r, p_r = int(ts[kx]), int(px[kx])
                    bar_of_trade = int(np.searchsorted(B["end"], t_r, "right"))          # vela en curso del trade
                    if bar_of_trade - p1["i_ext"] <= PREV_MAX_BARS:
                        c_last = bar_of_trade - 1                                          # última vela cerrada
                        tramo_now = abs(p_r - int(l0["b"]))
                        div = {}
                        for n in rsi:
                            _, agv, alv = rsi[n]
                            ok_c = c_last >= 3 * n and np.isfinite(agv[c_last]) and np.isfinite(alv[c_last])
                            rn = rsi_provisional(agv[c_last], alv[c_last], B["c"][c_last], p_r, n) if ok_c else np.nan
                            div[n] = (side * (rn - r1[n]) < 0) if np.isfinite(rn) and np.isfinite(r1[n]) else None
                        dd = None
                        if cfg["delta_ok"]:
                            l_start = int(np.searchsorted(ts, int(B["end"][l0["i_ext"]])))
                            w = ag[l_start:kx + 1]; v = vol[l_start:kx + 1]
                            bv, sv = v[w == side].sum(), v[w == -side].sum()
                            shn = (bv - sv) / (bv + sv) if bv + sv > 0 else np.nan
                            dd = (shn < sh1) if np.isfinite(shn) and np.isfinite(sh1) else None
                        ev.append(dict(moment="RUP", t=t_r, ext=p_r, tramo=int(tramo_now), div=div, div_delta=dd))
            for e in ev:
                tdir = -side
                stop = int(e["ext"] + side * max(2, int(np.ceil(0.25 * e["tramo"]))))
                i_in = int(np.searchsorted(ts, e["t"] + LAT_NS))
                if i_in >= len(ts):
                    continue
                entry_ref = int(ask[i_in] if tdir == 1 else bid[i_in])
                risk = tdir * (entry_ref - stop)
                if risk < 2:
                    continue                                  # ya se invalidó antes de poder entrar
                for m in MULTS:
                    target = entry_ref + tdir * m * risk
                    r = simulate(ts, px, bid, ask, e["t"] + LAT_NS, tdir, stop, target, s["end"], cfg["comm"], hold_s)
                    if r is None:
                        continue
                    rows.append(dict(res=res, moment=e["moment"], side=side, mult=m, t_event=e["t"], tramo=e["tramo"],
                                     risk=int(risk), div14=e["div"][14], div7=e["div"][7], div21=e["div"][21],
                                     div_delta=e["div_delta"], R=r["pnl"] / risk, hit=int(r["why"] == "target"), **r))
    return rows


def run_one(args):
    inst, s = args
    out = OUT / "events" / inst / f"{s['trade_date']}.parquet"
    rows, skip = session_events(inst, s)
    if skip:
        return inst, s["trade_date"], dict(skip=skip)
    D = pd.DataFrame(rows)
    D.insert(0, "session", s["trade_date"])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".partial"); D.to_parquet(tmp, index=False); tmp.replace(out)
    return inst, s["trade_date"], dict(rows=len(D))


def step_declare():
    from edgelab.edge_brain.episode_logger import measurement_episode
    with measurement_episode(LEDGER, "EP-AGOT-DECLARE-20260925", goal="AGOT-EXT: particiones antes de medir",
                             recorded_by="tools/agotamiento.py declare", repo=REPO, prereg_ref=MANIF) as ep:
        for inst in INSTR:
            ds = [s["trade_date"] for s in TB.sessions(inst)]
            ep.store.record_partition(f"P-AGOT-{inst}-EXP", "EXPLORATION", f"AGOT-EXT {inst} hasta {EXP_END}",
                                      [f"{inst}:{d}" for d in ds if d <= EXP_END])
            ep.store.record_partition(f"P-AGOT-{inst}-CONF", "CONFIRMATION_RESERVED", f"AGOT-EXT {inst} abr-jun 2026 (pre-holdout)",
                                      [f"{inst}:{d}" for d in ds if d > EXP_END])
    print("declaradas")


def step_run(inst, workers):
    ss = [s for s in TB.sessions(inst) if s["trade_date"] <= EXP_END]
    todo = [(inst, s) for s in ss if not (OUT / "events" / inst / f"{s['trade_date']}.parquet").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for fu in as_completed([ex.submit(run_one, t) for t in todo]):
            print(*fu.result(), flush=True)


# ------------------------------------------------------------------------------------------------ reporte
def step_report():
    from math import erfc, sqrt
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus import LessonCandidate
    cells, sens = [], []
    for inst in INSTR:
        files = sorted((OUT / "events" / inst).glob("*.parquet"))
        if not files:
            continue
        D = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        D = D[D.session <= EXP_END]
        sess = sorted(D.session.unique()); n_s = len(sess); si = {d: i for i, d in enumerate(sess)}
        rng = np.random.default_rng(SEED)
        W = np.stack([np.bincount(rng.integers(0, n_s, n_s), minlength=n_s) for _ in range(N_BOOT)]).astype(float)
        D["si"] = D.session.map(si); D["month"] = D.session.str.slice(0, 6)

        def sums(df, col):
            S = np.zeros(n_s); N = np.zeros(n_s)
            np.add.at(S, df.si.to_numpy(), df[col].to_numpy(float)); np.add.at(N, df.si.to_numpy(), 1)
            return S, N

        def boot(S, N):
            with np.errstate(invalid="ignore", divide="ignore"):
                return (W @ S) / (W @ N)
        divs = ["div14"] + (["div_delta"] if INSTR[inst]["delta_ok"] else [])
        for res in RES:
            for mom in ("RUP", "CONF"):
                for m in MULTS:
                    base = D[(D.res == res) & (D.moment == mom) & (D.mult == m)]
                    for dv in divs + ["div7", "div21"]:
                        yes = base[base[dv] == True]  # noqa: E712
                        no = base[base[dv] == False]  # noqa: E712
                        row = dict(inst=inst, res=res, momento=mom, div=dv, mult=m, n_div=int(len(yes)), n_sin=int(len(no)))
                        if len(yes) < 30 or len(no) < 30:
                            row["status"] = "SIN_MUESTRA"
                        else:
                            Sy, Ny = sums(yes, "R"); Sn, Nn = sums(no, "R")
                            by, bn = boot(Sy, Ny), boot(Sn, Nn)
                            syn = by - bn
                            pt = Sy.sum() / Ny.sum(); sd = np.nanstd(by)
                            Ex, Nx = sums(yes.assign(ex=yes.hit - yes.p0), "ex")
                            bex = boot(Ex, Nx)
                            Ay, Ayn = sums(yes, "absmove"); An, Ann = sums(no, "absmove")
                            dabs = boot(Ay, Ayn) - boot(An, Ann)
                            q = np.nanpercentile
                            row.update(status="OK", sesiones=int(yes.session.nunique()),
                                       R_div=[float(pt), float(q(by, 2.5)), float(q(by, 97.5))], R_sin=float(Sn.sum() / Nn.sum()),
                                       sinergia=[float(np.nanmean(syn)), float(q(syn, 2.5)), float(q(syn, 97.5))],
                                       hit=float(yes.hit.mean()), p0_N1=float(yes.p0.mean()),
                                       exceso_hit_N1=[float(np.nanmean(bex)), float(q(bex, 2.5)), float(q(bex, 97.5))],
                                       dif_absmove=[float(np.nanmean(dabs)), float(q(dabs, 2.5)), float(q(dabs, 97.5))],
                                       R_cuantiles_div=yes.R.quantile([.05, .25, .5, .75, .95]).round(3).tolist(),
                                       meses_positivos=float((yes.groupby("month").R.mean() > 0).mean()),
                                       p=erfc(abs(pt / sd) / sqrt(2)) if sd > 0 else 1.0)
                        (cells if dv in divs else sens).append(row)
    ok = [c for c in cells if c["status"] == "OK"]
    ps = np.array([c["p"] for c in ok]); mm = len(ps); o = np.argsort(ps)
    passed = np.zeros(mm, bool); kk = np.flatnonzero(ps[o] <= FDR_Q * np.arange(1, mm + 1) / mm) if mm else []
    if len(kk):
        passed[o[:kk.max() + 1]] = True
    sug = []
    for c, pz in zip(ok, passed):
        c["fdr"] = bool(pz)
        c["sugerencia"] = bool(pz and c["R_div"][1] > 0 and c["exceso_hit_N1"][1] > 0 and c["sinergia"][1] > 0 and c["meses_positivos"] >= 0.55)
        if c["sugerencia"]:
            sug.append(c)
    top = sorted(sug, key=lambda c: -c["R_div"][1])[:3]
    body = dict(schema="EDGELAB_AGOT_EXT_V1", manifest=MANIF, code_commit=_git("rev-parse", "HEAD"),
                tree_dirty=bool(_git("status", "--porcelain", "--", "tools", "edgelab")), celdas=cells, sensibilidad_rsi=sens,
                sugerencias_top=top)
    raw = json.dumps(body, indent=1, default=float)
    (OUT / "report.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    with measurement_episode(LEDGER, "EP-AGOT-20260925", goal="AGOT-EXT: divergencia en extremo, 24 celdas",
                             recorded_by="tools/agotamiento.py report", repo=REPO, prereg_ref=MANIF) as ep:
        for inst in INSTR:
            cc = [c for c in ok if c["inst"] == inst]
            if cc:
                ep.store.record_observation(f"OBS-AGOT-{inst}", f"AGOT-EXT {inst}: R con divergencia y sinergia", "RESPONSE_PROFILE",
                                            [f"P-AGOT-{inst}-EXP"],
                                            {f"{c['res']}|{c['momento']}|{c['div']}|{c['mult']}R": dict(R=c["R_div"], S=c["sinergia"]) for c in cc},
                                            {"cells": len(cc)}, sha, design="OTHER")
        for i, c in enumerate(top):
            ep.store.record_lesson(LessonCandidate(
                lesson_id=f"SUG-AGOT-{i + 1}", episode_id="EP-AGOT-20260925",
                statement=f"{c['inst']} {c['res']} {c['momento']} {c['div']} {c['mult']}R: R {c['R_div'][0]:.3f} (IC {c['R_div'][1]:.3f}..{c['R_div'][2]:.3f}), sinergia {c['sinergia'][0]:.3f}. Confirmar SOLO en P-AGOT-*-CONF.",
                confidence="LOW", status="PROPOSED", scope="SUGGESTED_ANALYSIS"))
    print(json.dumps(dict(celdas=len(ok), fdr=int(passed.sum()) if mm else 0, sugerencias=len(sug), sha=sha[:12])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["declare", "run", "report"])
    ap.add_argument("--inst", default="NQ")
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args(argv)
    if a.step == "declare":
        step_declare()
    elif a.step == "run":
        step_run(a.inst, a.workers)
    else:
        step_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
