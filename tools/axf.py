#!/usr/bin/env python3
r"""AXF: agotamiento por flujo → barrido del último extremo participante → reversión confirmada. NQ, exploración.

Manifiesto: docs/research/MANIFIESTO_AXF_NQ_20260926.md (escrito antes de medir).

    .venv\Scripts\python tools\axf.py bars --workers 2
    .venv\Scripts\python tools\axf.py stageA
    .venv\Scripts\python tools\axf.py reportA
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
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

INST = "NQ"
OUT = REPO / "artifacts" / "axf"
DOC = "docs/research/MANIFIESTO_AXF_NQ_20260926.md"
LEDGER = REPO / "artifacts" / "hippocampus" / "axf_20260926.jsonl"
NS = 1_000_000_000
LOOKN, EXHW, SWEEPMAX, REVMAX = 200, 30, 60, 60
FAR = (0.0, 4.0)
EXH = ("D05", "D20", "A2", "A3")
LASTDEF = (0, 1)
SWEEP = (2, 6)
REVDIST = (1.0, 3.0)
REVDELTA = (0.05, 0.20)
REVDISP = (0.4, 0.7)
TRENDS = ("ninguno", "a_favor", "en_contra")
HZ = (60, 1000)
N_PH, TOD, TOL, ABS_TOL = 3, 3600, 0.5, 0.15
SEED = 20260928
N_BOOT = 2000


# ------------------------------------------------------------------ velas con agresor
def _bars_session(s):
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from edgelab.bridge.bars import build_tick_bars
    from edgelab.bridge.ticks import load_canonical_parquet
    f = OUT / "bars" / f"{s['trade_date']}.npz"
    if f.exists():
        return s["trade_date"], "EXISTE"
    tk = load_canonical_parquet(s["path"], contract=s["contract"], instrument=INST, start_utc_ns=s["start"], end_utc_ns=s["end"])
    ts0 = tk.ts_ns.astype(np.int64)
    if len(ts0) < 5000:
        return s["trade_date"], "POCA_ACTIVIDAD"
    if int(ts0[-1]) >= TB.HOLDOUT_NS:
        raise ValueError("holdout decodificado")
    tb = pq.read_table(s["path"], columns=["ts_utc_ns", "price_ticks", "aggressor", "contract"],
                       filters=[("ts_utc_ns", ">=", s["start"]), ("ts_utc_ns", "<", s["end"])])
    tb = tb.filter(pc.equal(tb["contract"], s["contract"]))
    if len(tb) != len(tk) or not np.array_equal(tb["ts_utc_ns"].to_numpy(), ts0) or not np.array_equal(tb["price_ticks"].to_numpy(), tk.price_ticks):
        return s["trade_date"], "AGRESOR_DESALINEADO"
    ag = np.array(tb["aggressor"].to_pylist(), dtype=object)
    b = build_tick_bars(tk, 25, reiniciar_por_sesion=True)
    v = tk.volume.astype(float); nb = len(b.end_ns)
    buy = np.bincount(b.tick_bar_idx, weights=v * (ag == "buy"), minlength=nb)
    sell = np.bincount(b.tick_bar_idx, weights=v * (ag == "sell"), minlength=nb)
    f.parent.mkdir(parents=True, exist_ok=True)
    np.savez(f, t=(b.end_ns / NS).astype(np.float64), o=b.open_t.astype(np.int32), h=b.high_t.astype(np.int32), l=b.low_t.astype(np.int32),
             c=b.close_t.astype(np.int32), v=b.volume.astype(np.float32), buy=buy.astype(np.float32), sell=sell.astype(np.float32),
             contract=s["contract"])
    return s["trade_date"], "OK"


def step_bars(workers):
    import tbzx_iter2 as T2
    ss = [s for s in T2.canonical_sessions(INST) if s["trade_date"] <= TB.EXP_END]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for fu in as_completed([ex.submit(_bars_session, s) for s in ss]):
            print(*fu.result(), flush=True)


# ------------------------------------------------------------------ indicadores por sesión
def load():
    S = {}
    for f in sorted((OUT / "bars").glob("*.npz")):
        if f.stem > str(TB.EXP_END):
            continue
        z = np.load(f)
        t = z["t"]
        et = pd.to_datetime(t, unit="s", utc=True).tz_convert(TB.ET)
        clock = ((et.hour * 3600 + et.minute * 60 + et.second).to_numpy() - 18 * 3600) % 86400
        h, l, c, o = (z[k].astype(np.float64) for k in ("h", "l", "c", "o"))
        v = z["v"].astype(np.float64)
        prev = np.r_[c[0], c[:-1]]
        tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
        atr = np.maximum(pd.Series(tr).ewm(alpha=1 / 100, adjust=False).mean().to_numpy(), 1.0)
        vw = np.cumsum((h + l + c) / 3 * np.maximum(v, 1)) / np.cumsum(np.maximum(v, 1))
        e21 = pd.Series(c).ewm(span=21, adjust=False).mean().to_numpy()
        e200 = pd.Series(c).ewm(span=200, adjust=False).mean().to_numpy()
        n = len(c)
        rmax = np.full(n, np.inf); rmin = np.full(n, -np.inf)
        if n > LOOKN:
            from numpy.lib.stride_tricks import sliding_window_view
            rmax[LOOKN:] = sliding_window_view(h, LOOKN)[:-1].max(axis=1)
            rmin[LOOKN:] = sliding_window_view(l, LOOKN)[:-1].min(axis=1)
        vavg = pd.Series(v).rolling(500, min_periods=1).mean().to_numpy()
        rg20 = np.full(n, np.nan); sec20 = np.full(n, np.nan)
        if n > 20:
            from numpy.lib.stride_tricks import sliding_window_view as sw
            rg20[20:] = sw(h, 21).max(axis=1) - sw(l, 21).min(axis=1); sec20[20:] = t[20:] - t[:-20]
        sl21 = np.r_[np.full(5, np.nan), e21[5:] - e21[:-5]] / atr
        S[f.stem] = dict(t=t, o=o, h=h, l=l, c=c, v=v, buy=z["buy"].astype(np.float64), sell=z["sell"].astype(np.float64), atr=atr, vw=vw,
                         e200=e200, rmax=rmax, rmin=rmin, vavg=vavg, rg20=rg20, sec20=sec20, clock=clock.astype(np.int64),
                         st=np.vstack([(c - vw) / atr, sl21]))
    return S


@njit(cache=True)
def detect(h, l, c, o, v, buy, sell, atr, vw, rmax, rmin, vavg, far, exh, lastdef, sweep, revdist, revdelta, revdisp):
    """Eventos confirmados: filas (j, s, conf, entryI, d_extremo, E, zlo, zhi). d = +1 si el agotamiento es arriba."""
    n = len(c)
    out = np.zeros((n // 20 + 10, 8))
    m = 0
    busy = -1
    for j in range(LOOKN, n - 2):
        if j <= busy:
            continue
        up = h[j] > rmax[j]
        dn = l[j] < rmin[j]
        if not (up or dn):
            continue
        d = 1 if up else -1
        ext = h[j] if up else l[j]
        if d * (ext - vw[j]) / atr[j] < far:
            continue
        z0 = j - EXHW + 1
        if z0 < 1:
            continue
        zb = 0.0; zs = 0.0; zv = 0.0
        for q in range(z0, j + 1):
            zb += buy[q]; zs += sell[q]; zv += v[q]
        fav = d * (zb - zs) / max(zb + zs, 1.0)
        prog = d * (c[j] - o[z0]) / atr[j]
        if exh == 0:
            ok = -fav >= 0.05
        elif exh == 1:
            ok = -fav >= 0.20
        elif exh == 2:
            ok = zv >= 2.0 * vavg[j] * EXHW and prog <= 1.5
        else:
            ok = zv >= 3.0 * vavg[j] * EXHW and prog <= 1.0
        if not ok:
            continue
        busy = j + EXHW
        li = z0; best = -1e18
        for q in range(z0, j + 1):
            sc = v[q] if lastdef == 0 else d * (buy[q] - sell[q])
            if sc >= best:
                best = sc; li = q
        L = h[li] if d > 0 else l[li]
        zlo = 1e18; zhi = -1e18
        for q in range(z0, j + 1):
            zlo = min(zlo, l[q]); zhi = max(zhi, h[q])
        s = -1
        for q in range(j + 1, min(n - 1, j + SWEEPMAX) + 1):
            if (d > 0 and h[q] >= L + sweep) or (d < 0 and l[q] <= L - sweep):
                s = q
                break
        if s < 0:
            continue
        E = h[s] if d > 0 else l[s]
        Ei = s
        for q in range(s, min(n - 2, s + REVMAX) + 1):
            if (d > 0 and h[q] > E) or (d < 0 and l[q] < E):
                E = h[q] if d > 0 else l[q]
                Ei = q
            if q == Ei:
                continue
            dist = d * (E - c[q]) / atr[q]
            if dist < revdist:
                continue
            rb = 0.0; rs = 0.0; pth = 0.0
            for r2 in range(Ei + 1, q + 1):
                rb += buy[r2]; rs += sell[r2]; pth += abs(c[r2] - c[r2 - 1])
            rdel = -d * (rb - rs) / max(rb + rs, 1.0)
            disp = abs(c[q] - E) / max(pth + abs(c[Ei] - E), 1.0)
            if rdel >= revdelta and disp >= revdisp:
                out[m, 0] = j; out[m, 1] = s; out[m, 2] = q; out[m, 3] = q + 1; out[m, 4] = d; out[m, 5] = E; out[m, 6] = zlo; out[m, 7] = zhi
                m += 1
                break
    return out[:m]


def fwd(x, e, tdir, h, ref_i):
    n = len(x["c"])
    if e + h >= n:
        return np.nan
    return tdir * (x["c"][e + h] - x["o"][e]) / x["atr"][ref_i]


def step_stageA():
    S = load()
    keys = sorted(S)
    declare(keys)
    rng = np.random.default_rng(SEED)
    combos = list(itertools.product(range(len(FAR)), range(len(EXH)), LASTDEF, SWEEP, REVDIST, REVDELTA, REVDISP))
    rows, ctrl_cache = [], {}
    for k in keys:
        x = S[k]
        for ci, (fi, ei, ld, sw, rd, rde, rdi) in enumerate(combos):
            ev = detect(x["h"], x["l"], x["c"], x["o"], x["v"], x["buy"], x["sell"], x["atr"], x["vw"], x["rmax"], x["rmin"], x["vavg"],
                        FAR[fi], ei, ld, float(sw), rd, rde, rdi)
            for r in ev:
                conf, e, d = int(r[2]), int(r[3]), int(r[4])
                tdir = -d
                tr = np.sign(x["e200"][conf] - x["e200"][max(conf - 100, 0)]) * tdir
                rows.append((ci, k, conf, tdir, tr, *[fwd(x, e, tdir, hh, conf) for hh in HZ]))
                key = (k, conf, tdir)
                if key not in ctrl_cache:
                    ctrl_cache[key] = control(S, keys, k, conf, tdir, rng)
        print(k, "eventos acumulados", len(rows), flush=True)
    D = pd.DataFrame(rows, columns=["combo", "session", "conf", "tdir", "trend", *[f"r{h}" for h in HZ]])
    C = pd.DataFrame([(k, cf, td, *v) for (k, cf, td), v in ctrl_cache.items()],
                     columns=["session", "conf", "tdir", *[f"c{h}" for h in HZ], "n_ctrl", "ph_t", "t_ev", "ph_session"])
    D = D.merge(C, on=["session", "conf", "tdir"], how="left")
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_parquet(OUT / "stageA.parquet", index=False)
    json.dump(dict(combos=[dict(far=FAR[a], exh=EXH[b], lastDef=c, sweep=d, revDist=e, revDelta=f, revDisp=g) for a, b, c, d, e, f, g in combos]),
              open(OUT / "combos.json", "w"), indent=1)
    print("eventos", len(D), "únicos", len(C), "cobertura control", round(float((C.n_ctrl > 0).mean()), 3))


def control(S, keys, k, i, tdir, rng):
    """C-EST: otra sesión, misma hora, mismo estado y actividad. Media de hasta 3 controles."""
    x = S[k]; s0 = x["st"][:, i]; rg0, sec0 = x["rg20"][i], x["sec20"][i]; clock = int(x["clock"][i])
    others = [o for o in keys if o != k]
    vals, pts, ph_s = [], None, None
    for oi in rng.permutation(len(others)):
        if len(vals) >= N_PH:
            break
        o = others[int(oi)]; y = S[o]
        a, b = np.searchsorted(y["clock"], clock - TOD), np.searchsorted(y["clock"], clock + TOD)
        a = max(a, LOOKN)
        if b <= a + 1:
            continue
        st = y["st"][:, a:b]
        tol = np.maximum(TOL * np.abs(s0)[:, None], ABS_TOL)
        ok = np.all(np.abs(st - s0[:, None]) <= tol, axis=0)
        rg, sec = y["rg20"][a:b], y["sec20"][a:b]
        ok &= (np.abs(rg - rg0) <= TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + TOL))
        idx = np.flatnonzero(ok)
        if not len(idx):
            continue
        q = a + int(idx[int(rng.integers(len(idx)))])
        if q + 1 >= len(y["c"]):
            continue
        vals.append([fwd(y, q + 1, tdir, hh, q) for hh in HZ])
        pts, ph_s = float(y["t"][q]), o
    if not vals:
        return (*[np.nan] * len(HZ), 0, np.nan, float(x["t"][i]), None)
    m = np.nanmean(np.array(vals, float), axis=0)
    return (*m.tolist(), len(vals), pts, float(x["t"][i]), ph_s)


def declare(keys):
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    part = "P-AXF-NQ-EXP"
    if LEDGER.exists() and part in DurableHippocampus(LEDGER).partitions:
        return
    with measurement_episode(LEDGER, "EP-AXF-PARTICION-NQ", goal="declarar partición AXF NQ antes de medir",
                             recorded_by="tools/axf.py stageA", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_partition(part, "EXPLORATION", "NQ 25T exploración (<= 2026-03-31), contrato canónico, agresor verificado",
                                  [f"NQ:{k}" for k in keys])


def boot(r, c, ses, rng):
    diff = r - c
    u, inv = np.unique(ses, return_inverse=True)
    sums = np.bincount(inv, weights=diff); cnt = np.bincount(inv)
    bs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        w = np.bincount(rng.integers(len(u), size=len(u)), minlength=len(u))
        bs[b] = (w * sums).sum() / max((w * cnt).sum(), 1)
    p = 2 * min((bs <= 0).mean(), (bs >= 0).mean())
    return float(diff.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), float(2.8 * bs.std()), max(p, 1 / N_BOOT)


def bh(p, q=0.10):
    p = np.asarray(p); o = np.argsort(p); m = len(p); ok = np.zeros(m, bool)
    below = p[o] <= q * np.arange(1, m + 1) / m
    if below.any():
        ok[o[:np.max(np.flatnonzero(below)) + 1]] = True
    return ok


def step_reportA():
    D = pd.read_parquet(OUT / "stageA.parquet")
    combos = json.load(open(OUT / "combos.json"))["combos"]
    rng = np.random.default_rng(SEED)
    cells = []
    for ci, g in D.groupby("combo"):
        for tname, mask in (("ninguno", np.ones(len(g), bool)), ("a_favor", (g.trend > 0).to_numpy()), ("en_contra", (g.trend < 0).to_numpy())):
            gg = g[mask]
            for h in HZ:
                ok = np.isfinite(gg[f"r{h}"]) & np.isfinite(gg[f"c{h}"])
                base = dict(combo=int(ci), **combos[ci], trend=tname, h=h, n=int(ok.sum()))
                if ok.sum() < 50:
                    cells.append(dict(base, status="POCOS")); continue
                r, c, ses = gg[f"r{h}"][ok].to_numpy(), gg[f"c{h}"][ok].to_numpy(), gg.session[ok].to_numpy()
                d, lo, hi, mde, pv = boot(r, c, ses, rng)
                h1 = (pd.to_datetime(pd.Series(ses), format="%Y%m%d") < pd.Timestamp("2025-12-01")).to_numpy()
                halves = [float((r - c)[m_].mean()) if m_.sum() >= 20 else None for m_ in (h1, ~h1)]
                cells.append(dict(base, sessions=int(len(set(ses))), real=float(r.mean()), control=float(c.mean()), diff=d, ci=[lo, hi], mde=mde,
                                  pval=pv, no_dir=float(np.abs(r).mean() - np.abs(c).mean()), halves=halves, status="OK"))
    ok = [c for c in cells if c["status"] == "OK"]
    for c, f in zip(ok, bh([c["pval"] for c in ok])):
        c["fdr"] = bool(f)
    for c in cells:
        if c["status"] != "OK":
            c["estado"] = "SIN_POTENCIA"
        elif c["fdr"]:
            c["estado"] = "INFO+" if c["diff"] > 0 else "INFO-"
        else:
            c["estado"] = "SIN_INFO" if c["mde"] <= 0.25 else "SIN_POTENCIA"
        c["pasa_B"] = bool(c["estado"] == "INFO+" and c.get("halves") and all(v is not None and v > 0 for v in c["halves"]))
    from collections import Counter
    from edgelab.edge_brain.control_guard import audit_event_controls
    C = D.dropna(subset=["ph_t"]).drop_duplicates(["session", "conf", "tdir"])
    audit = audit_event_controls((C.t_ev * 1e6).astype(np.int64).to_numpy(), (C.ph_t * 1e6).astype(np.int64).to_numpy(), 1000 * 60.0,
                                 same_session=(C.session == C.ph_session).to_numpy())
    body = dict(schema="EDGELAB_AXF_A_V1", doc=DOC, code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")), estados=dict(Counter(c["estado"] for c in cells)),
                familia=len(ok), pasan_B=[c for c in cells if c["pasa_B"]], celdas=cells, control_audit=audit,
                cobertura_control=float((D.n_ctrl > 0).mean()))
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "reportA.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.episode_logger import measurement_episode
    with measurement_episode(LEDGER, f"EP-AXF-A-{sha[:8]}", goal="AXF etapa A: información por celda contra C-EST",
                             recorded_by="tools/axf.py reportA", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_observation(f"OBS-AXF-A-{sha[:8]}", "AXF etapa A (alcance por celda)", "RESPONSE_PROFILE", ["P-AXF-NQ-EXP"],
                                    {f"{c['combo']}|{c['trend']}|{c['h']}": (c.get("diff"), c["estado"]) for c in cells},
                                    {"horizons": list(HZ)}, sha, design="EVENT_VS_CONTROL", control_audit=audit)
    print(json.dumps(dict(sha=sha[:12], estados=body["estados"], familia=len(ok), pasan_B=len(body["pasan_B"]), audit=audit["status"],
                          cobertura=round(body["cobertura_control"], 3))))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["bars", "stageA", "reportA"])
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args(argv)
    {"bars": lambda: step_bars(a.workers), "stageA": step_stageA, "reportA": step_reportA}[a.step]()


if __name__ == "__main__":
    main()
